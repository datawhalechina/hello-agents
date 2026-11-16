"""Source deletion is exercised only against synthetic temporary databases."""
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.connectors.feishu import SyncCheckpoint
from app.main import create_app
from app.schemas import DeleteSourceRequest, EvidenceReference, Job, ReviewRequest, StandardMessage, WorkFact
from app.workflow.builder import build_workflow


TARGET = "删除/虚构甲"
KEEP = "保留/虚构乙"


def message(source, identifier, text, day=1):
    return {"id": identifier, "source_id": source, "sender": "虚构作者", "text": text,
            "timestamp": f"2026-01-{day:02d}T09:00:00+08:00"}


def import_records(client, source, records):
    response = client.post("/api/import", json={"source_id": source, "messages": records})
    assert response.status_code == 200, response.text


def seed(client):
    records = {
        TARGET: [message(TARGET, "a1", "【共享虚构项目】[任务:甲接口] 开始接口开发"),
                 message(TARGET, "a2", "【独有虚构项目】[任务:甲样例] 准备验收样例")],
        KEEP: [message(KEEP, "b1", "【共享虚构项目】[任务:乙接口] 开始接口测试", day=2),
               message(KEEP, "b2", "【共享虚构项目】[任务:乙报告] 已交付验收报告", day=3)],
    }
    for source, rows in records.items():
        import_records(client, source, rows)
    processed = client.post("/api/process", json={}).json()
    assert processed["status"] == "completed", processed
    repository = client.app.state.repository
    facts = repository.facts()
    target_fact = next(f for f in facts if f.evidence[0].source_id == TARGET)
    keep_fact = next(f for f in facts if f.evidence[0].source_id == KEEP)
    repository.review(target_fact.id, ReviewRequest(status="accepted", reviewer="synthetic-reviewer-a"))
    repository.review(keep_fact.id, ReviewRequest(status="accepted", reviewer="synthetic-reviewer-b"))
    repository.commit_sync_page([], SyncCheckpoint(source_id=TARGET, chat_id="oc_synthetic", complete=True))
    return records, target_fact.id, keep_fact.id


def preview(client, source=TARGET):
    response = client.get("/api/sources/delete-preview", params={"source_id": source})
    assert response.status_code == 200, response.text
    return response.json()


def body(impact):
    return {"confirmation": impact["source_id"], "expected_messages": impact["messages"], "expected_version": impact["version"]}


def remove(client, impact, **overrides):
    return client.request("DELETE", "/api/sources", params={"source_id": impact["source_id"]}, json={**body(impact), **overrides})


def logical_state(repository):
    tables = ("messages", "facts", "projects", "versions", "reviews", "jobs", "state")
    return {table: [tuple(row) for row in repository.connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()] for table in tables}


def assert_history_has_no_source(repository, source):
    for entry in repository.versions():
        _, graph = repository.latest(entry["version"])
        node_ids = {node.id for node in graph.nodes}
        fact_ids = {fact.id for fact in graph.facts}
        assert all(key in fact_ids for node in graph.nodes for key in node.fact_ids)
        assert all(edge.source in node_ids and edge.target in node_ids for edge in graph.edges)
        references = [ref for fact in graph.facts for ref in fact.evidence]
        references += [ref for node in graph.nodes for ref in node.evidence]
        references += [ref for edge in graph.edges for ref in edge.evidence]
        assert not any(ref.source_id == source for ref in references)


def test_preview_is_read_only_and_reports_shared_project_impact(client):
    seed(client)
    repository = client.app.state.repository
    before = logical_state(repository)
    impact = preview(client)
    assert impact["source_id"] == TARGET
    assert impact["messages"] == impact["facts"] == 2
    assert impact["projects_removed"] == impact["reviews"] == 1
    assert impact["versions"] >= 1 and impact["checkpoint"] is True
    assert impact["jobs_reset"] >= 1
    assert logical_state(repository) == before


def test_missing_or_wrong_confirmation_never_writes(client):
    seed(client)
    impact = preview(client)
    repository = client.app.state.repository
    before = logical_state(repository)
    missing = client.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={})
    assert missing.status_code == 422
    wrong = remove(client, impact, confirmation=KEEP)
    assert wrong.status_code in {409, 422}
    assert logical_state(repository) == before


def test_unknown_source_cannot_be_deleted(client):
    assert client.get("/api/sources/delete-preview", params={"source_id": "missing"}).status_code == 404
    response = client.request("DELETE", "/api/sources", params={"source_id": "missing"}, json={"confirmation": "missing", "expected_messages": 0, "expected_version": 0})
    assert response.status_code == 404


def test_unprocessed_source_can_be_removed_without_running_analysis(client):
    import_records(client, TARGET, [message(TARGET, "unprocessed", "独立虚构材料")])
    impact = preview(client)
    assert impact["messages"] == 1 and impact["facts"] == impact["versions"] == 0
    response = remove(client, impact)
    assert response.status_code == 200
    assert client.get("/api/sources").json() == []
    assert client.get("/api/facts").json() == []


@pytest.mark.parametrize("mutation", ["import", "review", "analysis"])
def test_changed_preview_requires_another_confirmation(client, mutation):
    _, _, keep_id = seed(client)
    impact = preview(client)
    if mutation == "import":
        import_records(client, TARGET, [message(TARGET, "new", "【共享虚构项目】开始新一轮测试", day=4)])
    elif mutation == "review":
        client.app.state.repository.review(keep_id, ReviewRequest(status="pending", reviewer="synthetic-recheck"))
    else:
        import_records(client, KEEP, [message(KEEP, "new", "【共享虚构项目】开始新一轮测试", day=4)])
        assert client.post("/api/process", json={}).json()["status"] == "completed"
    before = logical_state(client.app.state.repository)
    assert remove(client, impact).status_code == 409
    assert logical_state(client.app.state.repository) == before


@pytest.mark.parametrize("status", ["queued", "running"])
def test_active_job_blocks_source_deletion(client, status):
    seed(client)
    repository = client.app.state.repository
    repository.save_job(Job(id="synthetic-active", status=status))
    impact = preview(client)
    before = logical_state(repository)
    assert remove(client, impact).status_code == 409
    assert logical_state(repository) == before


def test_confirmed_unicode_source_deletion_preserves_other_source_review_and_training(client, monkeypatch):
    records, target_id, keep_id = seed(client)
    repository = client.app.state.repository
    surviving_messages = [m.model_dump(mode="json") for m in repository.messages() if m.source_id == KEEP]
    surviving_fact = next(f for f in repository.facts() if f.id == keep_id).model_dump(mode="json")
    before_jobs = {job.id: (job.status, job.created_at) for job in repository.jobs()}
    impact = preview(client)
    from app.agents.orchestrator import WorkflowOrchestrator
    monkeypatch.setattr(WorkflowOrchestrator, "analyze", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Deletion must not re-run agents")))
    response = remove(client, impact)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["messages_deleted"] == result["facts_deleted"] == 2
    assert result["projects_removed"] == result["reviews_deleted"] == result["remaining_sources"] == 1
    assert result["versions_updated"] >= 1
    assert repository.checkpoint(TARGET) is None
    assert client.get("/api/messages", params={"source_id": TARGET}).json() == []
    assert client.get("/api/facts", params={"source_id": TARGET}).json() == []
    assert client.get("/api/evidence", params={"source_id": TARGET, "message_id": records[TARGET][0]["id"]}).status_code == 404
    assert [m.model_dump(mode="json") for m in repository.messages()] == surviving_messages
    assert next(f for f in repository.facts() if f.id == keep_id).model_dump(mode="json") == surviving_fact
    assert {p.name for p in repository.projects()} == {"共享虚构项目"}
    assert {review["fact_id"] for review in repository.reviews()} == {keep_id}
    assert not any(f.id == target_id for f in repository.facts())
    assert_history_has_no_source(repository, TARGET)
    training = client.get("/api/export", params={"source_id": KEEP, "format": "training"}).text.splitlines()
    assert len(training) == 1 and json.loads(json.loads(training[0])["messages"][-1]["content"])["id"] == keep_id
    assert repository.runtime() == {}
    for job in repository.jobs():
        assert (job.status, job.created_at) == before_jobs[job.id]
        assert job.result is None


def test_cross_source_supported_fact_is_removed_as_a_whole(client):
    seed(client)
    repository = client.app.state.repository
    originals = repository.messages()
    primary = next(m for m in originals if m.source_id == KEEP)
    context = next(m for m in originals if m.source_id == TARGET)
    dependent = WorkFact(id="synthetic-dependent", kind="task", summary=primary.text, project_hint="共享虚构项目", occurred_at=primary.timestamp,
                         evidence=[EvidenceReference(message_id=primary.id, source_id=primary.source_id, quote=primary.text),
                                   EvidenceReference(message_id=context.id, source_id=context.source_id, quote=context.text)])
    proposal = build_workflow([*repository.facts(), dependent], originals, repository.projects())
    assert next(f for f in proposal.facts if f.id == dependent.id).verified
    repository.apply(proposal, {})
    impact = preview(client)
    assert impact["facts"] == 3
    assert remove(client, impact).status_code == 200
    assert not any(f.id == dependent.id for f in repository.facts())
    assert len([m for m in repository.messages() if m.source_id == KEEP]) == 2
    assert_history_has_no_source(repository, TARGET)


def test_delete_last_source_clears_history_and_allows_later_reimport(client):
    records, _, _ = seed(client)
    assert remove(client, preview(client)).status_code == 200
    assert remove(client, preview(client, KEEP)).status_code == 200
    assert client.get("/api/sources").json() == []
    stats = client.get("/api/stats").json()
    assert all(stats[field] == 0 for field in ("messages", "facts", "projects", "nodes", "edges", "pending_review", "versions"))
    assert client.get("/api/reviews").json() == []
    assert client.get("/api/export?format=training").text == ""
    import_records(client, TARGET, records[TARGET])
    assert client.get("/api/stats").json()["messages"] == 2


def test_delete_transaction_rolls_back_on_injected_sql_failure(client):
    _, target_id, _ = seed(client)
    repository = client.app.state.repository
    impact = preview(client)
    with repository.connection:
        repository.connection.execute(f"CREATE TRIGGER reject_source_delete BEFORE DELETE ON facts WHEN OLD.id='{target_id}' BEGIN SELECT RAISE(ABORT, 'synthetic rollback'); END")
    before = logical_state(repository)
    with pytest.raises(sqlite3.IntegrityError):
        repository.delete_source(TARGET, DeleteSourceRequest(**body(impact)))
    assert logical_state(repository) == before


def test_deletion_endpoints_require_configured_bearer_token(tmp_path):
    app = create_app(Settings(database_path=str(tmp_path / "secured-delete.db"), provider="local-demo", api_token="synthetic-secret", _env_file=None))
    with TestClient(app) as secured:
        assert secured.get("/api/sources/delete-preview", params={"source_id": TARGET}).status_code == 401
        response = secured.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={"confirmation": TARGET, "expected_messages": 0, "expected_version": 0})
        assert response.status_code == 401
        assert secured.get("/api/sources/delete-preview", params={"source_id": TARGET}, headers={"Authorization": "Bearer synthetic-secret"}).status_code == 404
