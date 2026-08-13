"""SQLite snapshot repositories for local ResumeAgent projects."""

import sqlite3
from pathlib import Path
from typing import List
from uuid import UUID

from resume_agent.application.ports import RevisionConflict
from resume_agent.domain.models import (
    CareerFactBase,
    InterviewSession,
    ResumeVersion,
)


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS fact_bases (
                    id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interview_sessions (
                    id TEXT PRIMARY KEY,
                    fact_base_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_fact_base
                    ON interview_sessions (fact_base_id);

                CREATE TABLE IF NOT EXISTS resume_versions (
                    id TEXT PRIMARY KEY,
                    fact_base_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_versions_fact_base
                    ON resume_versions (fact_base_id);
                """
            )


class SQLiteFactBaseRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def create(self, base: CareerFactBase) -> None:
        with self.store.connect() as connection:
            connection.execute(
                "INSERT INTO fact_bases (id, revision, payload) VALUES (?, ?, ?)",
                (str(base.id), base.revision, base.model_dump_json()),
            )

    def get(self, fact_base_id: UUID) -> CareerFactBase:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM fact_bases WHERE id = ?",
                (str(fact_base_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"fact base not found: {fact_base_id}")
        return CareerFactBase.model_validate_json(row["payload"])

    def list(self) -> List[CareerFactBase]:
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM fact_bases ORDER BY rowid"
            ).fetchall()
        return [CareerFactBase.model_validate_json(row["payload"]) for row in rows]

    def save(self, base: CareerFactBase, expected_revision: int) -> None:
        with self.store.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE fact_bases
                   SET revision = ?, payload = ?
                 WHERE id = ? AND revision = ?
                """,
                (
                    base.revision,
                    base.model_dump_json(),
                    str(base.id),
                    expected_revision,
                ),
            )
        if cursor.rowcount != 1:
            raise RevisionConflict(
                f"fact base revision conflict: {base.id} expected {expected_revision}"
            )


class SQLiteSessionRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def create(self, session: InterviewSession) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO interview_sessions (id, fact_base_id, payload)
                VALUES (?, ?, ?)
                """,
                (
                    str(session.id),
                    str(session.fact_base_id),
                    session.model_dump_json(),
                ),
            )

    def get(self, session_id: UUID) -> InterviewSession:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM interview_sessions WHERE id = ?",
                (str(session_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"interview session not found: {session_id}")
        return InterviewSession.model_validate_json(row["payload"])

    def list(self, fact_base_id: UUID) -> List[InterviewSession]:
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM interview_sessions WHERE fact_base_id = ? ORDER BY rowid",
                (str(fact_base_id),),
            ).fetchall()
        return [
            InterviewSession.model_validate_json(row["payload"]) for row in rows
        ]

    def save(self, session: InterviewSession) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO interview_sessions (id, fact_base_id, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    fact_base_id = excluded.fact_base_id,
                    payload = excluded.payload
                """,
                (
                    str(session.id),
                    str(session.fact_base_id),
                    session.model_dump_json(),
                ),
            )


class SQLiteVersionRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def get(self, version_id: UUID) -> ResumeVersion:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM resume_versions WHERE id = ?",
                (str(version_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"resume version not found: {version_id}")
        return ResumeVersion.model_validate_json(row["payload"])

    def list(self, fact_base_id: UUID) -> List[ResumeVersion]:
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM resume_versions WHERE fact_base_id = ?",
                (str(fact_base_id),),
            ).fetchall()
        versions = [ResumeVersion.model_validate_json(row["payload"]) for row in rows]
        return sorted(versions, key=lambda version: version.created_at)

    def save(self, version: ResumeVersion) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO resume_versions (id, fact_base_id, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    fact_base_id = excluded.fact_base_id,
                    payload = excluded.payload
                """,
                (
                    str(version.id),
                    str(version.fact_base_id),
                    version.model_dump_json(),
                ),
            )

    def delete(self, version_id: UUID) -> None:
        with self.store.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM resume_versions WHERE id = ?",
                (str(version_id),),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"resume version not found: {version_id}")
