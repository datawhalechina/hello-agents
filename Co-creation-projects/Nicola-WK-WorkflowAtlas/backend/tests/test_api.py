from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.schemas import Job, ReviewRequest, StandardMessage, WorkflowUpdateProposal
from app.storage import ConflictError, Repository


def sample(source="unit-source", id="m1", text="【验收项目】[任务:接口] 开始接口开发"):
    return {"id": id, "source_id": source, "sender": "工程师", "text": text, "timestamp": "2026-11-02T09:00:00+08:00"}


def test_demo_to_graph_evidence_review_and_training_export(client, demo):
    assert demo["import"]["imported"] == 29
    assert demo["job"]["result"]["facts"] == 25
    assert demo["job"]["result"]["projects"] == 2
    assert demo["job"]["result"]["nodes"] == 24
    assert len(demo["job"]["result"]["agent_results"]) == 6
    projects = client.get("/api/projects").json()
    graph = client.get(f"/api/projects/{projects[0]['id']}/workflow").json()
    assert graph["nodes"] and graph["edges"]
    node_ids = {node["id"] for node in graph["nodes"]}
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"])
    assert all(node["verified"] for node in graph["nodes"])
    assert client.get("/api/export?format=training").text == ""
    fact = graph["facts"][0]
    for evidence in fact["evidence"]:
        source = client.get(f"/api/evidence/{evidence['source_id']}/{evidence['message_id']}")
        assert source.status_code == 200
        assert evidence["quote"] in source.json()["text"]
    review = client.post(f"/api/facts/{fact['id']}/review", json={"status": "accepted", "reviewer": "qa-reviewer", "note": "原文一致"})
    assert review.status_code == 200 and review.json()["review_status"] == "accepted"
    rows = [json.loads(line) for line in client.get("/api/export?format=training").text.splitlines()]
    assert len(rows) == 1 and rows[0]["verified"] and rows[0]["review_status"] == "accepted"
    label = json.loads(rows[0]["messages"][-1]["content"])
    assert label["id"] == fact["id"] and rows[0]["provenance"] == fact["evidence"]
    assert client.get("/api/reviews").json()[0]["reviewer"] == "qa-reviewer"
    exported = client.get("/api/export?format=json")
    assert exported.status_code == 200 and "attachment" in exported.headers["content-disposition"]
    assert len(exported.json()["facts"]) == 25
    assert len(client.get("/api/export?format=jsonl").text.splitlines()) == 25


def test_repeat_demo_is_idempotent_and_does_not_create_new_versions(client, demo):
    first = client.get("/api/stats").json()
    second = client.post("/api/demo").json()
    assert second["import"]["imported"] == 0 and second["import"]["duplicates"] == 29
    assert second["job"]["status"] == "completed"
    assert client.get("/api/stats").json() == first


def test_conflicting_import_rolls_back_entire_batch(client):
    existing = sample()
    assert client.post("/api/import", json={"source_id": "unit-source", "messages": [existing]}).json()["imported"] == 1
    new = sample(id="m2")
    changed = {**existing, "text": "改写原文"}
    response = client.post("/api/import", json={"source_id": "unit-source", "messages": [new, changed]})
    assert response.status_code == 409
    messages = client.get("/api/messages").json()
    assert len(messages) == 1 and messages[0]["text"] == existing["text"]


def test_mixed_source_import_rejected_without_write(client):
    response = client.post("/api/import", json={"source_id": "unit-source", "messages": [sample(), sample(source="other")]})
    assert response.status_code == 400
    assert client.get("/api/messages").json() == []


def test_incremental_processing_preserves_old_project_review_and_snapshot(client, demo):
    projects = client.get("/api/projects").json()
    north = next(p for p in projects if p["name"] == "北辰门户")
    original = client.get(f"/api/projects/{north['id']}/workflow").json()
    fact = original["facts"][0]
    client.post(f"/api/facts/{fact['id']}/review", json={"status": "accepted", "reviewer": "qa"})
    new = sample(source="document-source", id="doc1", text="【新项目】[任务:验证] 开始测试")
    assert client.post("/api/import", json={"source_id": "document-source", "messages": [new]}).status_code == 200
    process = client.post("/api/process", json={"source_id": "document-source"}).json()
    assert process["status"] == "completed" and process["result"]["projects"] == 3
    current = client.get(f"/api/projects/{north['id']}/workflow").json()
    assert len(current["facts"]) == len(original["facts"])
    assert next(f for f in current["facts"] if f["id"] == fact["id"])["review_status"] == "accepted"
    old = client.get(f"/api/projects/{north['id']}/workflow?version={original['version']}").json()
    assert old == original
    assert client.get(f"/api/projects/{north['id']}/versions").json()[0]["version"] > original["version"]


def test_raw_jsonl_import_search_and_pagination(client):
    rows = [sample(id="m1"), sample(id="m2", text="【验收项目】交付数据报告")]
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    response = client.post("/api/import/file?source_id=unit-source&format=jsonl", content=text.encode("utf-8"), headers={"Content-Type": "text/plain"})
    assert response.status_code == 200 and response.json()["imported"] == 2
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    found = client.get("/api/facts", params={"q": "数据报告"}).json()
    assert len(found) == 1 and "数据报告" in found[0]["summary"]
    assert len(client.get("/api/messages?limit=1&offset=1").json()) == 1
    assert client.get("/api/messages?limit=0").status_code == 422


def test_invalid_file_import_does_not_echo_arbitrary_raw_data(client):
    response = client.post("/api/import/file?source_id=x", content=b'[{"api_key":"DO_NOT_ECHO"}]')
    assert response.status_code == 400
    assert "DO_NOT_ECHO" not in response.text
    assert client.get("/api/messages").json() == []


def test_failed_job_persists_status_and_keeps_existing_graph(client, demo):
    stats = client.get("/api/stats").json()
    job = client.post("/api/process", json={"source_id": "missing-source"}).json()
    assert job["status"] == "failed" and job["error"]
    assert client.get(f"/api/jobs/{job['id']}").json()["status"] == "failed"
    assert client.get("/api/stats").json() == stats


def test_background_job_is_observable(client):
    client.post("/api/import", json={"source_id": "unit-source", "messages": [sample()]})
    response = client.post("/api/jobs", json={})
    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['id']}").json()
    assert job["status"] == "completed" and job["result"]["facts"] == 1


def test_restart_marks_unfinished_jobs_failed(tmp_path):
    path = str(tmp_path / "restart.db")
    repository = Repository(path)
    repository.save_job(Job(id="orphan", status="running"))
    repository.close()
    reopened = Repository(path)
    try:
        job = reopened.job("orphan")
        assert job.status == "failed" and "restarted" in job.error
    finally:
        reopened.close()


def test_token_protects_read_write_export_and_evidence(tmp_path):
    app = create_app(Settings(database_path=str(tmp_path / "auth.db"), api_token="test-secret", _env_file=None))
    with TestClient(app) as secured:
        assert secured.get("/api/health").status_code == 200
        for method, url in [("get", "/api/messages"), ("get", "/api/export?format=training"), ("get", "/api/evidence/s/m"), ("post", "/api/demo"), ("get", "/api/runtime")]:
            response = getattr(secured, method)(url)
            assert response.status_code == 401, url
            assert "test-secret" not in response.text
        assert secured.get("/api/stats", headers={"Authorization": "Bearer incorrect"}).status_code == 401
        assert secured.get("/api/stats", headers={"Authorization": "Bearer test-secret"}).status_code == 200


def test_request_size_is_bounded(tmp_path):
    app = create_app(Settings(database_path=str(tmp_path / "size.db"), max_body_bytes=100, _env_file=None))
    with TestClient(app) as limited:
        assert limited.post("/api/import/file?source_id=s", content=b"x" * 101).status_code == 413


def test_bad_ids_and_review_status_are_rejected(client, demo):
    assert client.get("/api/projects/missing").status_code == 404
    assert client.get("/api/evidence/missing/missing").status_code == 404
    assert client.post("/api/facts/missing/review", json={"status": "accepted", "reviewer": "qa"}).status_code == 404
    fact = client.get("/api/facts").json()[0]
    assert client.post(f"/api/facts/{fact['id']}/review", json={"status": "trusted", "reviewer": "qa"}).status_code == 422
    assert client.get("/api/export?format=unsafe").status_code == 422


def test_explicit_app_settings_override_ambient_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKFLOW_PROVIDER", "helloagents-llm")
    app = create_app(Settings(database_path=str(tmp_path / "env.db"), provider="local-demo", _env_file=None))
    with TestClient(app) as local:
        response = local.post("/api/demo").json()
        assert response["job"]["status"] == "completed"
        assert response["job"]["result"]["provider"] == "local-demo"


def test_unverified_fact_cannot_be_accepted_or_exported(client):
    repository = client.app.state.repository
    from app.extraction.local import extract_local
    record = StandardMessage.model_validate(sample())
    repository.import_messages([record], record.source_id)
    fact = extract_local(record)[0]
    fact.verified = False
    repository.apply(WorkflowUpdateProposal(facts=[fact]), {})
    response = client.post(f"/api/facts/{fact.id}/review", json={"status": "accepted", "reviewer": "qa"})
    assert response.status_code == 409
    assert client.get("/api/export?format=training").text == ""


def test_changed_fact_content_resets_prior_approval(client, demo):
    from app.schemas import WorkFact
    repository = client.app.state.repository
    first = repository.facts()[0]
    repository.review(first.id, ReviewRequest(status="accepted", reviewer="qa"))
    _, proposal = repository.latest()
    next(f for f in proposal.facts if f.id == first.id).summary += "（内容变更）"
    repository.apply(proposal, {})
    current = next(f for f in repository.facts() if f.id == first.id)
    assert current.review_status == "pending"
    assert client.get("/api/export?format=training").text == ""
