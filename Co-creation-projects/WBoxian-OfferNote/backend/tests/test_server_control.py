import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from types import SimpleNamespace

from scripts import server_control


def test_local_control_requires_instance_token_and_rejects_browser_origins(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(server_control, "RUNTIME", tmp_path / "server.json")
    app = FastAPI()
    app.mount("/", StaticFiles(directory=tmp_path, html=True), name="web")
    server = SimpleNamespace(should_exit=False)
    state = server_control.attach(app, server, 8765)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.post("/api/_local/stop").status_code == 403
        headers = {"X-OfferNote-Control": state["token"]}
        assert (
            client.post(
                "/api/_local/stop",
                headers={**headers, "Origin": "http://127.0.0.1:8765"},
            ).status_code
            == 403
        )
        assert client.get("/api/_local/status", headers=headers).status_code == 200
        assert client.post("/api/_local/stop", headers=headers).status_code == 200
        assert server.should_exit
    server_control.release(state)
    assert not server_control.RUNTIME.exists()


def test_start_rejects_live_instance_without_replacing_its_token(tmp_path, monkeypatch):
    monkeypatch.setattr(server_control, "RUNTIME", tmp_path / "server.json")
    state = server_control.attach(FastAPI(), SimpleNamespace(should_exit=False), 8765)
    monkeypatch.setattr(server_control, "control", lambda *_: {"status": "running"})
    with pytest.raises(RuntimeError, match="already running"):
        server_control.attach(FastAPI(), SimpleNamespace(should_exit=False), 8766)
    assert server_control.read_runtime() == state
    server_control.release({"token": "other-instance", "port": 8765})
    assert server_control.read_runtime() == state
