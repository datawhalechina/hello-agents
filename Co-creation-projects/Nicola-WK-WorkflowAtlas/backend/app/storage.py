"""Transactional local persistence; immutable raw data and versioned proposals."""
from __future__ import annotations

import json
import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .schemas import DeleteSourceRequest, ImportReport, Job, Project, ReviewRequest, SourceDeletionPreview, SourceDeletionResult, StandardMessage, WorkFact, WorkflowUpdateProposal, utcnow
from .ordering import fact_order_key


class ConflictError(ValueError):
    pass


def dump(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def message_fingerprint(message: StandardMessage) -> str:
    """Keep exporter snapshot changes separate from immutable message evidence."""
    value = message.model_dump(mode='json')
    imported = value.get('metadata', {}).get('import')
    if (isinstance(imported, dict)
            and imported.get('platform') == message.source_type
            and imported.get('identity_kind') in {'native', 'derived'}):
        imported.pop('source_context_hash', None)
    return dump(value)


class Repository:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
                INSERT OR IGNORE INTO schema_versions VALUES(1, CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS messages(source_id TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(source_id,id));
                CREATE TABLE IF NOT EXISTS facts(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS versions(version INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, fact_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)
        self._recover_jobs()

    def _recover_jobs(self) -> None:
        for job in self.jobs():
            if job.status in {"queued", "running"}:
                job.status = "failed"
                job.error = "Service restarted before this job finished; submit a new processing job."
                job.completed_at = utcnow()
                self.save_job(job)

    def close(self) -> None:
        with self.lock:
            self.connection.close()

    def import_messages(self, messages: list[StandardMessage], source_id: str,
                        import_contexts: dict[str, dict[str, Any]] | None = None) -> ImportReport:
        if not messages:
            raise ValueError("Import contains no messages")
        with self.lock, self.connection:
            report = self._import_messages(messages, source_id)
            for context_hash, context in (import_contexts or {}).items():
                actual_hash = hashlib.sha256(dump(context).encode('utf-8')).hexdigest()
                if context_hash != actual_hash:
                    raise ValueError('导出上下文校验失败，请重新检查原始文件。')
                key = f'import_context:{source_id}:{context_hash}'
                value = {'source_id': source_id, 'context_hash': context_hash, 'context': context}
                self.connection.execute('INSERT OR IGNORE INTO state(key,payload) VALUES(?,?)', (key, dump(value)))
            return report

    def _import_messages(self, messages: list[StandardMessage], source_id: str) -> ImportReport:
        """Caller owns the transaction, including any connector acknowledgement."""
        if any(message.source_id != source_id for message in messages):
            raise ValueError("All message source_id values must match the import source_id")
        report = ImportReport(source_id=source_id)
        for message in messages:
            old = self.connection.execute("SELECT payload FROM messages WHERE source_id=? AND id=?", (source_id, message.id)).fetchone()
            payload = dump(message)
            if old:
                if old['payload'] != payload and message_fingerprint(StandardMessage.model_validate_json(old['payload'])) != message_fingerprint(message):
                    raise ConflictError(f"Immutable message conflict: {source_id}/{message.id}")
                report.duplicates += 1
            else:
                self.connection.execute("INSERT INTO messages VALUES(?,?,?)", (source_id, message.id, payload))
                report.imported += 1
        return report

    def checkpoint(self, source_id: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute("SELECT payload FROM state WHERE key=?", ("checkpoint:" + source_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def commit_sync_page(self, messages: list[StandardMessage], checkpoint) -> ImportReport:
        """Raw messages and pagination acknowledgement commit or roll back together."""
        with self.lock, self.connection:
            report = self._import_messages(messages, checkpoint.source_id)
            self.connection.execute("INSERT OR REPLACE INTO state VALUES(?,?)", ("checkpoint:" + checkpoint.source_id, dump(checkpoint.to_dict())))
            return report

    def messages(self) -> list[StandardMessage]:
        with self.lock:
            rows = self.connection.execute("SELECT payload FROM messages").fetchall()
        return sorted((StandardMessage.model_validate_json(row[0]) for row in rows), key=lambda m: (m.timestamp, m.source_id, m.id))

    def evidence(self, source_id: str, message_id: str) -> StandardMessage | None:
        with self.lock:
            row = self.connection.execute("SELECT payload FROM messages WHERE source_id=? AND id=?", (source_id, message_id)).fetchone()
        return StandardMessage.model_validate_json(row[0]) if row else None

    def facts(self) -> list[WorkFact]:
        with self.lock:
            rows = self.connection.execute("SELECT payload FROM facts ORDER BY id").fetchall()
        return sorted((WorkFact.model_validate_json(row[0]) for row in rows), key=fact_order_key)

    def projects(self) -> list[Project]:
        with self.lock:
            rows = self.connection.execute("SELECT payload FROM projects ORDER BY id").fetchall()
        return [Project.model_validate_json(row[0]) for row in rows]

    def latest(self, version: int | None = None) -> tuple[int, WorkflowUpdateProposal]:
        with self.lock:
            if version is None:
                row = self.connection.execute("SELECT version,payload FROM versions ORDER BY version DESC LIMIT 1").fetchone()
            else:
                row = self.connection.execute("SELECT version,payload FROM versions WHERE version=?", (version,)).fetchone()
        if row is None:
            if version is not None:
                raise KeyError("Workflow version not found")
            return 0, WorkflowUpdateProposal()
        return row[0], WorkflowUpdateProposal.model_validate_json(row[1])

    def _snapshot(self, proposal: WorkflowUpdateProposal) -> int:
        version, old = self.latest()
        if dump(old) == dump(proposal):
            return version
        cursor = self.connection.execute("INSERT INTO versions(created_at,payload) VALUES(?,?)", (utcnow().isoformat(), dump(proposal)))
        return int(cursor.lastrowid)

    def apply(self, proposal: WorkflowUpdateProposal, runtime: dict[str, Any], *, preserve_model_semantics: bool = False, extra_state: tuple[str, dict] | None = None, terminal_job: Job | None = None) -> int:
        from .services.completion import update_project_status
        with self.lock, self.connection:
            previous = {fact.id: fact for fact in self.facts()}
            for fact in proposal.facts:
                old = previous.get(fact.id)
                excluded = {"review_status", "verified", "confidence"}
                if old and old.model_dump(exclude=excluded) == fact.model_dump(exclude=excluded):
                    fact.review_status = old.review_status
                else:
                    fact.review_status = "pending"
            # Re-analysis can remove a former false discovery. Keep historical
            # snapshots, but do not present empty stale candidates as projects.
            referenced_projects = {fact.project_id for fact in proposal.facts if fact.project_id and fact.verified}
            if not preserve_model_semantics:
                proposal.projects = [project for project in proposal.projects if project.id in referenced_projects or project.analysis_mode == 'model']
                update_project_status(proposal)
            self.connection.execute("DELETE FROM facts")
            self.connection.executemany("INSERT INTO facts VALUES(?,?)", [(fact.id, dump(fact)) for fact in proposal.facts])
            self.connection.execute("DELETE FROM projects")
            self.connection.executemany("INSERT INTO projects VALUES(?,?)", [(project.id, dump(project)) for project in proposal.projects])
            version = self._snapshot(proposal)
            self.connection.execute("INSERT OR REPLACE INTO state VALUES('runtime',?)", (dump(runtime),))
            if extra_state is not None:
                key, value = extra_state
                self.connection.execute('INSERT OR REPLACE INTO state VALUES(?,?)', (key, dump({**value, 'version': version})))
            if terminal_job is not None:
                terminal_job.result['version'] = version
                self.connection.execute('UPDATE jobs SET payload=? WHERE id=?', (dump(terminal_job), terminal_job.id))
            return version

    def review(self, fact_id: str, request: ReviewRequest) -> WorkFact:
        from .services.completion import update_project_status
        with self.lock, self.connection:
            row = self.connection.execute("SELECT payload FROM facts WHERE id=?", (fact_id,)).fetchone()
            if row is None:
                raise KeyError("Fact not found")
            fact = WorkFact.model_validate_json(row[0])
            if request.status == "accepted" and not fact.verified:
                raise ConflictError("A fact without verified source evidence cannot be accepted")
            fact.review_status = request.status
            self.connection.execute("UPDATE facts SET payload=? WHERE id=?", (dump(fact), fact_id))
            audit = {**request.model_dump(), "fact_id": fact_id, "created_at": utcnow().isoformat()}
            self.connection.execute("INSERT INTO reviews(fact_id,created_at,payload) VALUES(?,?,?)", (fact_id, audit["created_at"], dump(audit)))
            _, proposal = self.latest()
            proposal.facts = [fact if item.id == fact_id else item for item in proposal.facts]
            update_project_status(proposal)
            self.connection.executemany("UPDATE projects SET payload=? WHERE id=?", [(dump(item), item.id) for item in proposal.projects])
            self._snapshot(proposal)
            return fact

    def versions(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute("SELECT version,created_at,payload FROM versions ORDER BY version DESC").fetchall()
        return [{"version": row[0], "created_at": row[1]} for row in rows if project_id is None or any(p["id"] == project_id for p in json.loads(row[2])["projects"])]

    def reviews(self) -> list[dict[str, Any]]:
        with self.lock:
            return [json.loads(row[0]) for row in self.connection.execute("SELECT payload FROM reviews ORDER BY id DESC").fetchall()]

    def save_job(self, job: Job) -> None:
        with self.lock, self.connection:
            self.connection.execute("INSERT OR REPLACE INTO jobs VALUES(?,?)", (job.id, dump(job)))

    def jobs(self) -> list[Job]:
        with self.lock:
            return [Job.model_validate_json(row[0]) for row in self.connection.execute("SELECT payload FROM jobs").fetchall()]

    def job(self, job_id: str) -> Job | None:
        with self.lock:
            row = self.connection.execute("SELECT payload FROM jobs WHERE id=?", (job_id,)).fetchone()
        return Job.model_validate_json(row[0]) if row else None

    def runtime(self) -> dict[str, Any]:
        with self.lock:
            row = self.connection.execute("SELECT payload FROM state WHERE key='runtime'").fetchone()
        return json.loads(row[0]) if row else {}

    def read_state(self, key: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute("SELECT payload FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def write_state(self, key: str, value: dict[str, Any]) -> None:
        with self.lock, self.connection:
            self.connection.execute("INSERT OR REPLACE INTO state VALUES(?,?)", (key, dump(value)))

    def _source_deletion_state(self, source_id: str):
        from .services.deletion import redact_source
        count = self.connection.execute("SELECT COUNT(*) FROM messages WHERE source_id=?", (source_id,)).fetchone()[0]
        checkpoint = self.checkpoint(source_id) is not None
        if not count and not checkpoint:
            raise KeyError("Source not found")
        version, graph = self.latest()
        # The current fact table includes current review status.
        graph.facts = self.facts()
        retained, removed_ids, _ = redact_source(graph, source_id)
        current_removed = len(removed_ids)
        affected_versions = []
        for row in self.connection.execute("SELECT version,payload FROM versions ORDER BY version").fetchall():
            historical = WorkflowUpdateProposal.model_validate_json(row[1])
            redacted, removed, changed = redact_source(historical, source_id)
            removed_ids.update(removed)
            if changed:
                affected_versions.append((row[0], redacted))
        reviews = sum(review["fact_id"] in removed_ids for review in self.reviews())
        jobs_reset = sum(job.result is not None for job in self.jobs())
        preview = SourceDeletionPreview(source_id=source_id, messages=count, facts=current_removed,
                                       projects_removed=len(graph.projects) - len(retained.projects), reviews=reviews,
                                       versions=len(affected_versions), checkpoint=checkpoint, jobs_reset=jobs_reset, version=version)
        return preview, retained, removed_ids, affected_versions

    def source_delete_preview(self, source_id: str) -> SourceDeletionPreview:
        with self.lock:
            return self._source_deletion_state(source_id)[0]

    def delete_source(self, source_id: str, request: DeleteSourceRequest) -> SourceDeletionResult:
        """Explicit local dataset removal. All graph/history writes are atomic."""
        from .services.completion import update_project_status
        from .workflow.builder import build_chronological_edges

        with self.lock, self.connection:
            preview, retained, removed_ids, affected_versions = self._source_deletion_state(source_id)
            if request.confirmation != source_id:
                raise ConflictError("Type the exact source ID to confirm deletion")
            if request.expected_messages != preview.messages or request.expected_version != preview.version:
                raise ConflictError("Source or analysis changed; refresh the deletion preview before confirming")
            if any(job.status in {"queued", "running"} for job in self.jobs()):
                raise ConflictError("Processing is active; wait for jobs to finish before deleting a source")

            # Only chronology is recalculated. Other sources' facts, assignments
            # and review labels are retained verbatim, with no model invocation.
            model_projects = {p.id for p in retained.projects if p.analysis_mode == 'model'}
            retained.edges = [edge for edge in retained.edges if edge.relation != "precedes" or edge.project_id in model_projects] + build_chronological_edges([f for f in retained.facts if f.project_id not in model_projects], [n for n in retained.nodes if n.project_id not in model_projects])
            retained.edges.sort(key=lambda edge: (edge.project_id, edge.source, edge.target, edge.relation))
            update_project_status(retained)
            self.connection.execute("DELETE FROM messages WHERE source_id=?", (source_id,))
            self.connection.execute("DELETE FROM state WHERE key=?", ("checkpoint:" + source_id,))
            self.connection.executemany("DELETE FROM reviews WHERE fact_id=?", [(key,) for key in removed_ids])
            for version, historical in affected_versions:
                update_project_status(historical)
                if historical.facts or historical.nodes or historical.projects:
                    self.connection.execute("UPDATE versions SET payload=? WHERE version=?", (dump(historical), version))
                else:
                    self.connection.execute("DELETE FROM versions WHERE version=?", (version,))
            self.connection.execute("DELETE FROM facts")
            self.connection.executemany("INSERT INTO facts VALUES(?,?)", [(fact.id, dump(fact)) for fact in retained.facts])
            self.connection.execute("DELETE FROM projects")
            self.connection.executemany("INSERT INTO projects VALUES(?,?)", [(project.id, dump(project)) for project in retained.projects])
            for job in self.jobs():
                if job.result is not None:
                    job.result = None
                    # Do not call save_job here: its connection context would
                    # commit before the source-removal transaction finishes.
                    self.connection.execute("UPDATE jobs SET payload=? WHERE id=?", (dump(job), job.id))
            self.connection.execute("DELETE FROM state WHERE key='runtime'")
            # Analysis checkpoints contain source-derived evidence too.
            for row in self.connection.execute("SELECT key,payload FROM state WHERE key LIKE 'analysis_cache:%' OR key LIKE 'holistic_cache:%' OR key LIKE 'direct_cache:%' OR key LIKE 'holistic_report:%' OR key LIKE 'diagram_cache:%' OR key LIKE 'model_diagram:%' OR key LIKE 'fact_graph:%' OR key LIKE 'fact_graph_cache:%' OR key LIKE 'import_context:%'").fetchall():
                if json.loads(row['payload']).get('source_id') == source_id:
                    self.connection.execute("DELETE FROM state WHERE key=?", (row['key'],))
            version = self._snapshot(retained)
            remaining_sources = self.connection.execute("SELECT COUNT(DISTINCT source_id) FROM messages").fetchone()[0]
            return SourceDeletionResult(source_id=source_id, messages_deleted=preview.messages, facts_deleted=preview.facts,
                                        projects_removed=preview.projects_removed, reviews_deleted=preview.reviews,
                                        versions_updated=preview.versions, jobs_reset=preview.jobs_reset,
                                        remaining_sources=remaining_sources, version=version)
