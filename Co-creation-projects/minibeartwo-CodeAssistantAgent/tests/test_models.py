"""Model discovery uses draft credentials without mutating the saved connection."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend import models


@pytest.fixture
def discovery(tmp_path, monkeypatch):
    app = create_app(tmp_path / "data", token="discovery-token", persist_secrets=False)
    requests, options = [], []
    state = {"reply": lambda request: httpx.Response(200, json={"data": [{"id": "test-model"}]})}
    original_client = httpx.AsyncClient

    def handler(request):
        requests.append(request)
        return state["reply"](request)

    def client(**values):
        options.append(values)
        return original_client(transport=httpx.MockTransport(handler), **values)

    monkeypatch.setattr(models.httpx, "AsyncClient", client)
    with TestClient(app, headers={"Authorization": "Bearer discovery-token"}) as api:
        yield api, app, state, requests, options


def test_draft_connection_models_are_normalized_without_saving(discovery):
    api, app, state, requests, options = discovery
    before = api.get("/api/settings").json()
    state["reply"] = lambda request: httpx.Response(200, json={"data": [
        {"id": "z-model"}, {"id": " a-model "}, {"id": "z-model"},
        {"id": ""}, {"id": None}, {"id": "x" * 201}, "invalid",
    ]})
    result = api.post("/api/models", json={"base_url": " http://127.0.0.1:12345/proxy/v1/ ", "api_key": "draft-secret"})
    assert result.status_code == 200
    assert result.json() == {"models": ["a-model", "z-model"]}
    assert str(requests[-1].url) == "http://127.0.0.1:12345/proxy/v1/models"
    assert requests[-1].headers["authorization"] == "Bearer draft-secret"
    assert options[-1]["trust_env"] is False
    assert options[-1]["follow_redirects"] is False
    assert api.get("/api/settings").json() == before
    assert "draft-secret" not in json.dumps(app.state.store.settings())
    assert "draft-secret" not in result.text


def test_saved_key_is_reused_only_for_saved_endpoint(discovery):
    api, app, state, requests, options = discovery
    api.put("/api/settings", json={"base_url": "https://saved.example/v1", "model": "saved-model", "api_key": "saved-secret"})
    assert api.post("/api/models", json={"base_url": "https://saved.example/v1/"}).status_code == 200
    assert requests[-1].headers["authorization"] == "Bearer saved-secret"
    assert options[-1]["trust_env"] is True
    api.post("/api/models", json={"base_url": "https://other.example/v1"})
    assert "authorization" not in requests[-1].headers
    api.post("/api/models", json={"base_url": "https://other.example/v1", "api_key": "new-secret"})
    assert requests[-1].headers["authorization"] == "Bearer new-secret"
    assert app.state.settings.memory_key == "saved-secret"
    assert api.get("/api/settings").json()["model"] == "saved-model"


@pytest.mark.parametrize("status, message", [(401, "API Key"), (403, "访问权限"), (404, "不支持"),
    (405, "不支持"), (501, "不支持"), (429, "频繁"), (302, "跳转"), (500, "HTTP 500")])
def test_provider_errors_are_useful_and_never_echo_secrets(discovery, status, message):
    api, app, state, requests, options = discovery
    state["reply"] = lambda request: httpx.Response(status, text="server echoed draft-secret", headers={"Location": "https://other.example"})
    result = api.post("/api/models", json={"base_url": "https://provider.example/v1", "api_key": "draft-secret"})
    assert result.status_code == 400
    assert message in result.json()["detail"]
    assert "draft-secret" not in result.text
    assert len(requests) == 1


@pytest.mark.parametrize("payload", [[], {"data": None}, {"models": []}, {"data": {"id": "x"}}])
def test_unrecognized_lists_fall_back_to_manual_input(discovery, payload):
    api, app, state, requests, options = discovery
    state["reply"] = lambda request: httpx.Response(200, json=payload)
    result = api.post("/api/models", json={"base_url": "http://localhost:12345/v1"})
    assert result.status_code == 400
    assert "手动填写" in result.json()["detail"]


def test_empty_non_json_large_and_timeout_responses(discovery):
    api, app, state, requests, options = discovery
    values = {"base_url": "http://127.0.0.1:12345/v1"}
    state["reply"] = lambda request: httpx.Response(200, json={"data": []})
    assert api.post("/api/models", json=values).json() == {"models": []}
    state["reply"] = lambda request: httpx.Response(200, text="<html>login</html>")
    assert "有效的模型列表" in api.post("/api/models", json=values).json()["detail"]
    state["reply"] = lambda request: httpx.Response(200, content=b"x" * 2_000_001)
    assert "响应过大" in api.post("/api/models", json=values).json()["detail"]

    def timeout(request):
        raise httpx.ReadTimeout("draft-secret", request=request)

    state["reply"] = timeout
    result = api.post("/api/models", json=values)
    assert result.status_code == 400 and "超时" in result.json()["detail"]
    assert "draft-secret" not in result.text


@pytest.mark.parametrize("endpoint", ["ftp://provider.example/v1", "https://user:password@provider.example/v1",
    "https://provider.example/v1?token=secret", "https://provider.example/v1#fragment", "http://[broken", "not a url"])
def test_invalid_endpoints_and_unauthenticated_requests_never_contact_provider(discovery, endpoint):
    api, app, state, requests, options = discovery
    assert api.post("/api/models", json={"base_url": endpoint}).status_code == 400
    assert api.post("/api/models", json={"base_url": "http://localhost/v1"},
        headers={"Authorization": "wrong"}).status_code == 401
    assert not requests


def test_connection_probe_uses_draft_settings_without_saving_or_generating(discovery):
    api, app, state, requests, options = discovery
    before = api.get("/api/settings").json()
    result = api.post("/api/connection-test", json={"base_url": "http://localhost:12345/v1", "api_key": "draft-secret"})
    assert result.status_code == 200
    assert result.json()["status"] == "success"
    assert result.json()["latency_ms"] >= 0
    assert "连接成功" in result.json()["message"]
    assert requests[-1].method == "GET" and requests[-1].url.path == "/v1/models"
    assert requests[-1].headers["authorization"] == "Bearer draft-secret"
    assert api.get("/api/settings").json() == before
    assert "draft-secret" not in result.text
    state["reply"] = lambda request: httpx.Response(200, json={"data": []})
    result = api.post("/api/connection-test", json={"base_url": "http://localhost:12345/v1"})
    assert result.json()["status"] == "success"
    assert "未返回可用模型" in result.json()["message"]


@pytest.mark.parametrize("status", [404, 405, 501])
def test_unsupported_probe_is_reported_as_unverified_not_success(discovery, status):
    api, app, state, requests, options = discovery
    state["reply"] = lambda request: httpx.Response(status)
    result = api.post("/api/connection-test", json={"base_url": "http://localhost:12345/v1"})
    assert result.status_code == 200
    assert result.json()["status"] == "warning"
    assert "尚未确认调用权限" in result.json()["message"]


def test_probe_reuses_saved_key_and_handles_auth_timeout_and_private_api(discovery):
    api, app, state, requests, options = discovery
    values = {"base_url": "https://saved.example/v1"}
    api.put("/api/settings", json={**values, "model": "saved-model", "api_key": "saved-secret"})
    assert api.post("/api/connection-test", json=values).status_code == 200
    assert requests[-1].headers["authorization"] == "Bearer saved-secret"
    api.post("/api/connection-test", json={"base_url": "https://different.example/v1"})
    assert "authorization" not in requests[-1].headers
    state["reply"] = lambda request: httpx.Response(401, text="saved-secret")
    response = api.post("/api/connection-test", json=values)
    assert response.status_code == 400 and "连接测试失败" in response.json()["detail"]
    assert "saved-secret" not in response.text

    def timeout(request):
        raise httpx.ReadTimeout("saved-secret", request=request)

    state["reply"] = timeout
    response = api.post("/api/connection-test", json=values)
    assert response.status_code == 400 and "连接测试超时" in response.json()["detail"]
    assert "saved-secret" not in response.text
    count = len(requests)
    assert api.post("/api/connection-test", json=values, headers={"Authorization": "wrong"}).status_code == 401
    assert len(requests) == count


def test_saving_new_provider_never_reuses_the_old_providers_key(discovery):
    api, app, state, requests, options = discovery
    first = {"base_url": "https://api.deepseek.com", "model": "first-model"}
    api.put("/api/settings", json={**first, "api_key": "first-provider-secret"})
    removed = []

    class Keyring:
        def delete_password(self, service, account):
            removed.append((service, account))

    app.state.settings.keyring = Keyring()
    same = api.put("/api/settings", json={**first, "base_url": " https://api.deepseek.com/ "})
    assert same.json()["has_api_key"]
    assert same.json()["base_url"] == first["base_url"]
    assert app.state.settings.memory_key == "first-provider-secret"
    assert not removed
    second = {"base_url": "https://api.moonshot.cn/v1", "model": "second-model"}
    result = api.put("/api/settings", json=second)
    assert result.status_code == 200 and not result.json()["has_api_key"]
    assert app.state.settings.memory_key == ""
    assert removed == [("CodeAssistantAgent", "model-api-key:" + result.json()["connection_id"])]
    api.post("/api/models", json={"base_url": second["base_url"]})
    assert "authorization" not in requests[-1].headers
