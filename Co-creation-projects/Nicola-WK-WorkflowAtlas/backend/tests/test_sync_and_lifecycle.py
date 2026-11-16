from dataclasses import replace
import json
import sqlite3
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.connectors.feishu import FeishuHistoryClient, HttpResponse, SyncCheckpoint
from app.extraction.local import extract_local
from app.main import create_app
from app.retrieval.memory import build_working_memory
from app.schemas import StandardMessage
from app.storage import ConflictError

from test_api import sample


def test_evidence_query_supports_slash_and_unicode_identity(client):
    record = sample(source="文档/北辰", id="章节/1")
    assert client.post("/api/import", json={"source_id": record["source_id"], "messages": [record]}).status_code == 200
    response = client.get("/api/evidence", params={"source_id": record["source_id"], "message_id": record["id"]})
    assert response.status_code == 200 and response.json()["text"] == record["text"]


def test_working_memory_is_bounded_and_project_scoped(client, demo):
    projects = client.get("/api/projects").json()
    north = next(p for p in projects if p["name"] == "北辰门户")
    memory = client.get(f"/api/projects/{north['id']}/memory").json()
    assert memory["fact_count"] == 17
    assert len(memory["recent_facts"]) <= 12
    assert memory["text_used"] <= memory["text_budget"]
    assert "数据清洗" not in json.dumps(memory, ensure_ascii=False)
    facts = [*extract_local(StandardMessage.model_validate(sample()))]
    tiny = build_working_memory(facts, text_budget=1)
    assert tiny["text_used"] <= 1 and tiny["recent_facts"] == []


def test_project_completion_requires_marker_and_new_work_reopens(client):
    terminal = sample(text="【验收项目】[实体:结项] 项目验收通过")
    assert client.post("/api/import", json={"source_id": "unit-source", "messages": [terminal]}).status_code == 200
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    project = client.get("/api/projects").json()[0]
    assert project["status"] == "completed"
    later = {**sample(id="m2", text="【验收项目】[任务:新需求] 开始接口开发"), "timestamp": "2026-11-03T09:00:00+08:00"}
    client.post("/api/import", json={"source_id": "unit-source", "messages": [later]})
    client.post("/api/process", json={})
    assert client.get(f"/api/projects/{project['id']}").json()["status"] == "active"


def test_rejected_completion_marker_cannot_complete_project(client):
    terminal = sample(text="【验收项目】[实体:结项] 项目验收通过")
    client.post("/api/import", json={"source_id": "unit-source", "messages": [terminal]})
    client.post("/api/process", json={})
    fact = client.get("/api/facts").json()[0]
    client.post(f"/api/facts/{fact['id']}/review", json={"status": "rejected", "reviewer": "qa"})
    assert client.get("/api/projects").json()[0]["status"] == "active"


def test_sync_message_conflict_never_acknowledges_page(client):
    repository = client.app.state.repository
    first = StandardMessage.model_validate(sample())
    initial = SyncCheckpoint(source_id=first.source_id, chat_id="oc_1", page_token="p1")
    repository.commit_sync_page([first], initial)
    new = first.model_copy(update={"id": "new"})
    changed = first.model_copy(update={"text": "改变了原文"})
    with pytest.raises(ConflictError):
        repository.commit_sync_page([new, changed], replace(initial, page_token="p2"))
    assert repository.checkpoint(first.source_id)["page_token"] == "p1"
    assert [m.id for m in repository.messages()] == [first.id]


def test_checkpoint_storage_failure_rolls_back_raw_messages(client):
    repository = client.app.state.repository
    record = StandardMessage.model_validate(sample())
    checkpoint = SyncCheckpoint(source_id=record.source_id, chat_id="oc_1", complete=True)
    with repository.connection:
        repository.connection.execute("CREATE TRIGGER reject_checkpoint BEFORE INSERT ON state WHEN NEW.key LIKE 'checkpoint:%' BEGIN SELECT RAISE(ABORT, 'injected checkpoint failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        repository.commit_sync_page([record], checkpoint)
    assert repository.messages() == [] and repository.checkpoint(record.source_id) is None


def raw_message(id="om_1", time="1793606400000"):
    return {"message_id": id, "create_time": time, "chat_id": "oc_fake", "msg_type": "text", "sender": {"id": "ou_fake"}, "body": {"content": json.dumps({"text": "【同步项目】开始开发接口"}, ensure_ascii=False)}}


def test_feishu_api_resume_incremental_dedup_and_chat_identity(tmp_path, monkeypatch):
    import app.connectors.feishu as connector
    responses = [
        {"code": 0, "data": {"items": [raw_message()], "has_more": True, "page_token": "next"}},
        {"code": 0, "data": {"items": [raw_message("om_2", "1793610000000")], "has_more": False}},
        {"code": 0, "data": {"items": [raw_message("om_2", "1793610000000"), raw_message("om_3", "1793613600000")], "has_more": False}},
    ]
    requests = []
    def transport(url, headers):
        requests.append(parse_qs(urlparse(url).query))
        assert headers["Authorization"] == "Bearer fixture-token"
        return HttpResponse(200, responses.pop(0))
    monkeypatch.setattr(connector, "FeishuHistoryClient", lambda token: FeishuHistoryClient(token, transport=transport, sleeper=lambda _: None))
    app = create_app(Settings(database_path=str(tmp_path / "sync.db"), feishu_sync_enabled=True, feishu_access_token="fixture-token", _env_file=None))
    with TestClient(app) as syncing:
        body = {"source_id": "live-source", "chat_id": "oc_fake", "max_pages": 1, "end_time": 1793700000}
        first = syncing.post("/api/feishu/sync", json=body)
        assert first.status_code == 200 and first.json()["imported"] == 1
        assert not first.json()["checkpoint"]["complete"]
        second = syncing.post("/api/feishu/sync", json=body)
        assert second.status_code == 200 and second.json()["checkpoint"]["complete"]
        assert requests[1]["page_token"] == ["next"]
        third = syncing.post("/api/feishu/sync", json={**body, "incremental": True, "end_time": 1793800000})
        assert third.status_code == 200 and third.json()["imported"] == 1 and third.json()["duplicates"] == 1
        assert "start_time" in requests[2]
        assert len(syncing.get("/api/messages").json()) == 3
        assert syncing.post("/api/feishu/sync", json={**body, "chat_id": "oc_other"}).status_code == 409
        status = syncing.get("/api/feishu/status")
        assert "fixture-token" not in status.text and status.json()["mode"] == "read-only"


def test_feishu_failure_keeps_previous_checkpoint(tmp_path, monkeypatch):
    import app.connectors.feishu as connector
    monkeypatch.setattr(connector, "FeishuHistoryClient", lambda token: FeishuHistoryClient(token, transport=lambda url, headers: HttpResponse(503, {}), sleeper=lambda _: None))
    app = create_app(Settings(database_path=str(tmp_path / "sync-error.db"), feishu_sync_enabled=True, feishu_access_token="fixture-token", _env_file=None))
    with TestClient(app) as syncing:
        response = syncing.post("/api/feishu/sync", json={"source_id": "s", "chat_id": "oc_fake"})
        assert response.status_code == 502
        assert syncing.app.state.repository.checkpoint("s") is None
        assert syncing.get("/api/messages").json() == []


def test_feishu_sync_disabled_by_default(client):
    status = client.get("/api/feishu/status").json()
    assert not status["enabled"] and not status["credential_configured"]
    assert client.post("/api/feishu/sync", json={"source_id": "s", "chat_id": "oc_fake"}).status_code == 403
