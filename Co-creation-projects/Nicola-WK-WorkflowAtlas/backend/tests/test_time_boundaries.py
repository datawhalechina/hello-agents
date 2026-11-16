"""Explicit time boundaries must never expand to a broader enterprise read."""
from fastapi.testclient import TestClient

from app.config import Settings
from app.connectors.feishu import FeishuHistoryClient, HttpResponse
from app.main import create_app


def test_epoch_zero_end_time_is_preserved_and_invalid_window_never_reads(tmp_path, monkeypatch):
    import app.connectors.feishu as connector
    calls = []

    def transport(url, headers):
        calls.append(url)
        return HttpResponse(200, {"code": 0, "data": {"items": [], "has_more": False}})

    monkeypatch.setattr(connector, "FeishuHistoryClient", lambda token: FeishuHistoryClient(token, transport=transport))
    app = create_app(Settings(database_path=str(tmp_path / "bounds.db"), feishu_sync_enabled=True, feishu_access_token="synthetic", _env_file=None))
    with TestClient(app) as client:
        invalid = client.post("/api/feishu/sync", json={"source_id": "invalid", "chat_id": "oc_fake", "start_time": 1, "end_time": 0})
        assert invalid.status_code == 400 and calls == []
        valid = client.post("/api/feishu/sync", json={"source_id": "epoch", "chat_id": "oc_fake", "start_time": 0, "end_time": 0})
        assert valid.status_code == 200 and valid.json()["checkpoint"]["end_time"] == 0
        assert len(calls) == 1 and "end_time=0" in calls[0]
