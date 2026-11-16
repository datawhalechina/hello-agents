"""Browser model configuration tests use invented credentials and no provider."""
from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.schemas import Job

KEY = "synthetic-VERY-SECRET-model-key-DO-NOT-RETURN"
MODEL = "synthetic-model"
BASE = "https://provider.example/v1"


@pytest.fixture
def fake_connection(monkeypatch):
    from app.extraction import remote
    calls = []

    def connection(model, api_key, base_url):
        calls.append((model, api_key, base_url))
        return {"ok": True, "detail": "连接成功", "latency_ms": 1.0}

    monkeypatch.setattr(remote, "test_model_connection", connection, raising=False)
    return calls


def payload(**overrides):
    return {"provider": "helloagents-llm", "model": MODEL, "base_url": BASE,
            "api_key": KEY, "external_data_authorized": True, "batch_size": 5, **overrides}


def check_connection(client, **overrides):
    response = client.post("/api/model/test", json={"model": MODEL, "base_url": BASE, "api_key": KEY, **overrides})
    assert response.status_code == 200 and response.json()["ok"], response.text
    assert KEY not in response.text
    return response


def enable_remote(client):
    check_connection(client)
    response = client.put("/api/model/settings", json=payload())
    assert response.status_code == 200, response.text
    return response.json()


def test_default_get_and_connection_test_do_not_enable_or_analyze(client, fake_connection):
    initial = client.get("/api/model/settings")
    assert initial.status_code == 200
    assert initial.json()["provider"] == "local-demo" and not initial.json()["external_data_authorized"]
    assert initial.json()["api_key_configured"] is False
    before = client.get("/api/stats").json()
    check_connection(client)
    assert fake_connection == [(MODEL, KEY, BASE)]
    after = client.get("/api/model/settings").json()
    assert after["provider"] == "local-demo" and not after["api_key_configured"]
    assert client.get("/api/stats").json() == before


def test_remote_enable_requires_test_for_exact_credentials_and_data_consent(client, fake_connection):
    untested = client.put("/api/model/settings", json=payload())
    assert untested.status_code in {400, 409, 422}
    check_connection(client)
    unconsented = client.put("/api/model/settings", json=payload(external_data_authorized=False))
    assert unconsented.status_code in {400, 409, 422}
    for changed_credentials in ({"model": "different-model"}, {"base_url": "https://other.example/v1"}, {"api_key": "synthetic-different-key"}):
        changed = client.put("/api/model/settings", json=payload(**changed_credentials))
        assert changed.status_code in {400, 409, 422}
        assert KEY not in changed.text and "synthetic-different-key" not in changed.text
    assert KEY not in untested.text + unconsented.text
    enabled = client.put("/api/model/settings", json=payload())
    assert enabled.status_code == 200
    result = enabled.json()
    assert result["provider"] == "helloagents-llm" and result["api_key_configured"]
    assert result["test_status"] == "passed" and result["external_data_authorized"]
    assert KEY not in enabled.text and "encrypted_api_key" not in enabled.text
    assert client.get("/api/health").json()["provider"] == "helloagents-llm"


def test_saved_key_survives_restart_encrypted_and_never_reads_back(tmp_path, fake_connection):
    path = tmp_path / "persistent.db"
    settings = Settings(database_path=str(path), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        enable_remote(first)
        state_rows = first.app.state.repository.connection.execute("SELECT payload FROM state").fetchall()
        assert KEY not in " ".join(str(row[0]) for row in state_rows)
        assert KEY not in first.get("/api/model/settings").text
    assert KEY.encode() not in path.read_bytes()
    with TestClient(create_app(settings)) as reopened:
        result = reopened.get("/api/model/settings").json()
        assert result["saved"] and result["api_key_configured"] and result["provider"] == "helloagents-llm"
        tested = reopened.post("/api/model/test", json={"model": MODEL, "base_url": BASE})
        assert tested.status_code == 200 and tested.json()["ok"]
        assert fake_connection[-1] == (MODEL, KEY, BASE)
        assert KEY not in tested.text


@pytest.mark.parametrize("blank", [None, ""])
def test_blank_key_retains_existing_and_explicit_clear_removes_it(client, fake_connection, blank):
    enable_remote(client)
    retained = client.put("/api/model/settings", json=payload(api_key=blank))
    assert retained.status_code == 200 and retained.json()["api_key_configured"]
    cleared = client.put("/api/model/settings", json=payload(provider="local-demo", api_key=None, clear_api_key=True, external_data_authorized=False))
    assert cleared.status_code == 200
    assert not cleared.json()["api_key_configured"] and cleared.json()["provider"] == "local-demo"
    assert not client.get("/api/health").json()["external_llm_enabled"]


@pytest.mark.parametrize("url", [
    "file:///tmp/model", "https://user:password@provider.example/v1",
    "https://provider.example/v1?api_key=DO_NOT_FORWARD", "https://provider.example/v1#secret",
    "https://provider.example/v1\r\nX-Injected: true",
])
def test_invalid_endpoint_is_rejected_before_any_test_request(client, fake_connection, url):
    response = client.post("/api/model/test", json={"model": MODEL, "base_url": url, "api_key": KEY})
    assert response.status_code in {400, 422}
    assert fake_connection == []
    assert KEY not in response.text


def test_active_processing_blocks_configuration_change(client, fake_connection):
    check_connection(client)
    client.app.state.repository.save_job(Job(id="synthetic-active", status="running"))
    response = client.put("/api/model/settings", json=payload())
    assert response.status_code == 409
    assert client.get("/api/model/settings").json()["provider"] == "local-demo"


def test_configuration_endpoints_require_bearer_when_enabled(tmp_path, fake_connection):
    with TestClient(create_app(Settings(database_path=str(tmp_path / "auth.db"), api_token="synthetic-access-token", _env_file=None))) as secured:
        for method, path, body in [("GET", "/api/model/settings", None), ("POST", "/api/model/test", {"model": MODEL, "base_url": BASE, "api_key": KEY}), ("PUT", "/api/model/settings", payload())]:
            response = secured.request(method, path, json=body)
            assert response.status_code == 401
            assert KEY not in response.text
        assert fake_connection == []


def test_failed_connection_result_does_not_allow_enable(client, monkeypatch):
    from app.extraction import remote
    monkeypatch.setattr(remote, "test_model_connection", lambda *args: {"ok": False, "detail": "认证失败", "latency_ms": 1.0}, raising=False)
    response = client.post("/api/model/test", json={"model": MODEL, "base_url": BASE, "api_key": KEY})
    assert response.status_code == 200 and response.json()["ok"] is False
    assert client.put("/api/model/settings", json=payload()).status_code in {400, 409, 422}


@pytest.mark.parametrize("size", [0, 11])
def test_batch_size_bounds_reject_without_persisting_credentials(client, fake_connection, size):
    response = client.put("/api/model/settings", json=payload(batch_size=size))
    assert response.status_code == 422 and KEY not in response.text
    assert not client.get("/api/model/settings").json()["api_key_configured"]
    assert fake_connection == []


def test_in_memory_configuration_does_not_write_a_secret_file(tmp_path, monkeypatch, fake_connection):
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app(Settings(database_path=":memory:", provider="local-demo", _env_file=None))) as memory:
        enable_remote(memory)
        rows = memory.app.state.repository.connection.execute("SELECT payload FROM state").fetchall()
        assert KEY not in " ".join(str(row[0]) for row in rows)
        assert memory.get("/api/model/settings").json()["api_key_configured"]
        assert list(tmp_path.iterdir()) == []
    with TestClient(create_app(Settings(database_path=":memory:", provider="local-demo", _env_file=None))) as fresh:
        assert not fresh.get("/api/model/settings").json()["api_key_configured"]
        assert list(tmp_path.iterdir()) == []
