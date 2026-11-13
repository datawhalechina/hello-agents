"""Saved configurations retain their own secrets and survive selection and restart."""
import json
import sys
import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.settings import Settings
from backend.store import Store


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"):
        monkeypatch.delenv(key, raising=False)


def values(name, key="", **extra):
    return {"name": name, "base_url": "https://provider.example/v1", "model": name + "-model",
            "api_key": key, "max_steps": 8, **extra}


def test_execution_budget_defaults_after_creating_and_deleting_last_connection(tmp_path):
    settings = Settings(Store(tmp_path / "state.sqlite3"), persist_secrets=False)
    assert settings.public()["max_steps"] == 1000
    assert "task_timeout" not in settings.public()
    saved = settings.save_connection({"model": "default-model", "base_url": "https://provider.example/v1"})
    assert saved["max_steps"] == 1000 and "task_timeout" not in saved
    custom = settings.save_connection(values("Custom", id=saved["connection_id"]))
    assert custom["max_steps"] == 8 and "task_timeout" not in custom
    cleared = settings.delete_connection(custom["connection_id"])["settings"]
    assert cleared["max_steps"] == 1000 and "task_timeout" not in cleared


@pytest.mark.parametrize("method, route", [("PUT", "/api/settings"), ("POST", "/api/connections")])
def test_execution_budget_api_defaults_and_limits(tmp_path, method, route):
    app = create_app(tmp_path, token="budget-token", persist_secrets=False)
    payload = {"model": "budget-model", "base_url": "https://provider.example/v1"}
    with TestClient(app, headers={"Authorization": "Bearer budget-token"}) as api:
        response = api.request(method, route, json=payload)
        assert response.status_code == 200
        assert response.json()["max_steps"] == 1000
        assert "task_timeout" not in response.json()
        for steps in (101, 1000, 5000, 100000):
            response = api.request(method, route, json={**payload, "max_steps": steps})
            assert response.status_code == 200
            assert response.json()["max_steps"] == steps
            assert api.get("/api/settings").json()["max_steps"] == steps
            assert "task_timeout" not in response.json()
        for invalid in (0, -1, 1.5):
            assert api.request(method, route, json={**payload, "max_steps": invalid}).status_code == 422
        assert "maximum" not in api.get("/openapi.json").json()["components"]["schemas"]["ModelSettings"]["properties"]["max_steps"]
        assert "task_timeout" not in api.get("/api/settings").json()
        assert "task_timeout" not in api.get("/openapi.json").json()["components"]["schemas"]["ModelSettings"]["properties"]


def test_custom_step_budget_above_default_survives_restart_and_activation(tmp_path):
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store, persist_secrets=False)
    large = settings.save_connection(values("Large", max_steps=5000))
    assert large["max_steps"] == 5000
    small = settings.save_connection(values("Small", max_steps=8))
    reopened = Settings(store, persist_secrets=False)
    assert reopened.activate(large["connection_id"])["max_steps"] == 5000
    assert reopened.activate(small["connection_id"])["max_steps"] == 8


def test_legacy_timeout_is_removed_from_saved_profiles_and_not_restored(tmp_path):
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store, persist_secrets=False)
    profile = settings.save_connection(values("Legacy"))
    records = store.settings()["connections"]
    records[0]["task_timeout"] = 1
    store.set_settings({"task_timeout": 1, "connections": records})
    reopened = Settings(store, persist_secrets=False)
    assert "task_timeout" not in store.settings()
    assert "task_timeout" not in reopened.connections()["connections"][0]
    activated = reopened.activate(profile["connection_id"])
    assert activated["max_steps"] == 8 and activated["model"] == "Legacy-model"
    assert "task_timeout" not in activated
    assert "task_timeout" not in store.settings()["connections"][0]


def test_save_list_activate_update_and_new_draft_are_independent(tmp_path):
    app = create_app(tmp_path, token="connections-token", persist_secrets=False)
    with TestClient(app, headers={"Authorization": "Bearer connections-token"}) as api:
        assert api.get("/api/connections").json() == {"connections": [], "active_id": None}
        a = api.post("/api/connections", json=values("A", "private-A")).json()
        b = api.post("/api/connections", json=values("B", "private-B")).json()
        assert a["connection_id"] != b["connection_id"]
        listing = api.get("/api/connections").json()
        assert len(listing["connections"]) == 2 and listing["active_id"] == b["connection_id"]
        assert "private-A" not in json.dumps(listing) and "private-B" not in json.dumps(listing)
        selected = api.post(f'/api/connections/{a["connection_id"]}/activate').json()
        assert selected["model"] == "A-model" and selected["max_steps"] == 8
        assert app.state.settings.memory_key == "private-A"
        edited = api.post("/api/connections", json=values("A edited", id=a["connection_id"], model="new-A-model")).json()
        assert edited["connection_id"] == a["connection_id"] and edited["has_api_key"]
        assert app.state.settings.memory_key == "private-A"
        assert len(api.get("/api/connections").json()["connections"]) == 2
        api.post(f'/api/connections/{b["connection_id"]}/activate')
        assert app.state.settings.memory_key == "private-B"
        assert api.get("/api/settings").json()["model"] == "B-model"
        empty = api.post("/api/connections", json=values("No key")).json()
        assert not empty["has_api_key"] and app.state.settings.memory_key == ""
        assert len(api.get("/api/connections").json()["connections"]) == 3
        assert "private-A" not in json.dumps(app.state.store.settings())
        assert "private-B" not in json.dumps(app.state.store.settings())
        assert api.get("/api/connections", headers={"Authorization": "wrong"}).status_code == 401
        assert api.post('/api/connections/' + 'f' * 32 + '/activate').status_code == 404
        assert api.post("/api/connections", json=values("Missing", id='f' * 32)).status_code == 404


def test_delete_inactive_active_and_last_connection(tmp_path):
    app = create_app(tmp_path, token="delete-token", persist_secrets=False)
    with TestClient(app, headers={"Authorization": "Bearer delete-token"}) as api:
        a, b, c = [api.post("/api/connections", json=values(name, name + "-secret")).json()
                   for name in ("A", "B", "C")]
        route = lambda item: '/api/connections/' + item["connection_id"]
        assert api.delete(route(a), headers={"Authorization": "wrong"}).status_code == 401
        deleted = api.delete(route(a)).json()
        assert deleted["active_id"] == c["connection_id"]
        assert app.state.settings.memory_key == "C-secret"
        assert a["connection_id"] not in app.state.settings.keys
        assert api.delete(route(a)).status_code == 404
        switched = api.delete(route(c)).json()
        assert switched["settings"]["connection_id"] == b["connection_id"]
        assert switched["settings"]["model"] == "B-model"
        assert app.state.settings.memory_key == "B-secret"
        empty = api.delete(route(b)).json()
        assert empty["connections"] == [] and empty["active_id"] is None
        assert empty["settings"]["model"] == empty["settings"]["base_url"] == ""
        assert not empty["settings"]["has_api_key"]
        assert app.state.settings.memory_key == ""
        assert "secret" not in json.dumps(empty)


def test_deleted_environment_connection_does_not_return_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "environment-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://environment.example/v1")
    monkeypatch.setenv("LLM_MODEL_ID", "environment-model")
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store, persist_secrets=False)
    settings.delete_connection(settings.public()["connection_id"])
    reopened = Settings(store, persist_secrets=False)
    assert reopened.connections() == {"connections": [], "active_id": None}
    assert reopened.public()["base_url"] == reopened.public()["model"] == ""
    assert reopened.memory_key == ""
    assert store.settings()["environment_connection_id"] is None


class Vault:
    def __init__(self):
        self.entries = {}

    def get_password(self, service, account):
        return self.entries.get((service, account))

    def set_password(self, service, account, value):
        self.entries[service, account] = value

    def delete_password(self, service, account):
        self.entries.pop((service, account), None)


def test_keyring_connections_survive_restart_and_edit_only_their_own_key(tmp_path, monkeypatch):
    vault = Vault()
    monkeypatch.setitem(sys.modules, "keyring", vault)
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store)
    a = settings.save_connection(values("A", "persisted-A"))
    b = settings.save_connection(values("B", "persisted-B"))
    reopened = Settings(store)
    assert reopened.public()["connection_id"] == b["connection_id"]
    assert reopened.memory_key == "persisted-B"
    reopened.activate(a["connection_id"])
    assert reopened.memory_key == "persisted-A"
    reopened.save_connection(values("A changed", id=a["connection_id"], base_url="https://different.example/v1"))
    assert not reopened.public()["has_api_key"]
    reopened.activate(b["connection_id"])
    assert reopened.memory_key == "persisted-B"
    assert all(item["key_storage"] in {"keyring", "none"} for item in reopened.connections()["connections"])
    assert "persisted-" not in store.path.read_bytes().decode("latin1")


def test_deleting_configuration_removes_only_its_vault_secret(tmp_path, monkeypatch):
    vault = Vault()
    monkeypatch.setitem(sys.modules, "keyring", vault)
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store)
    a = settings.save_connection(values("A", "persisted-A"))
    b = settings.save_connection(values("B", "persisted-B"))
    settings.delete_connection(a["connection_id"])
    assert ("CodeAssistantAgent", "model-api-key:" + a["connection_id"]) not in vault.entries
    assert vault.entries["CodeAssistantAgent", "model-api-key:" + b["connection_id"]] == "persisted-B"
    reopened = Settings(store)
    assert len(reopened.connections()["connections"]) == 1
    assert reopened.memory_key == "persisted-B"
    reopened.delete_connection(b["connection_id"])
    assert vault.entries == {}
    assert Settings(store).connections() == {"connections": [], "active_id": None}


def test_legacy_configuration_is_imported_once_with_its_key(tmp_path, monkeypatch):
    vault = Vault()
    vault.entries["CodeAssistantAgent", "model-api-key"] = "legacy-secret"
    monkeypatch.setitem(sys.modules, "keyring", vault)
    store = Store(tmp_path / "state.sqlite3")
    store.set_settings({"model": "old-model", "base_url": "https://old.example/v1", "max_steps": 6})
    settings = Settings(store)
    assert settings.public()["model"] == "old-model" and settings.public()["max_steps"] == 6
    assert settings.memory_key == "legacy-secret"
    assert len(settings.connections()["connections"]) == 1
    assert settings.public()["connection_name"] == "默认配置"
    assert "legacy-secret" not in json.dumps(store.settings())
    reopened = Settings(store)
    assert len(reopened.connections()["connections"]) == 1
    assert reopened.memory_key == "legacy-secret"


def test_memory_only_connections_keep_names_after_restart_without_mixing_keys(tmp_path):
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store, persist_secrets=False)
    a = settings.save_connection(values("A", "memory-A"))
    settings.save_connection(values("B", "memory-B"))
    settings.activate(a["connection_id"])
    assert settings.memory_key == "memory-A"
    reopened = Settings(store, persist_secrets=False)
    assert reopened.public()["connection_id"] == a["connection_id"]
    assert reopened.memory_key == "" and not reopened.public()["has_api_key"]
    assert len(reopened.connections()["connections"]) == 2


def test_environment_key_only_returns_to_its_imported_connection(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "environment-secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://environment.example/v1")
    monkeypatch.setenv("LLM_MODEL_ID", "environment-model")
    store = Store(tmp_path / "state.sqlite3")
    settings = Settings(store, persist_secrets=False)
    original = settings.public()["connection_id"]
    assert original and settings.memory_key == "environment-secret"
    settings.save_connection(values("Other"))
    reopened = Settings(store, persist_secrets=False)
    assert reopened.memory_key == ""
    reopened.activate(original)
    assert reopened.memory_key == "environment-secret"
    reopened.save_connection(values("Replacement", "temporary-key", id=original,
                                    base_url="https://environment.example/v1"))
    assert Settings(store, persist_secrets=False).memory_key == ""


def test_switching_profiles_during_a_task_still_redacts_its_original_key(tmp_path):
    started, switched = threading.Event(), threading.Event()

    class FailingModel:
        async def generate(self, messages, emit):
            started.set()
            while not switched.is_set():
                await asyncio.sleep(.01)
            raise ValueError("provider error with original-secret")

        def close(self):
            pass

    app = create_app(tmp_path / "data", token="task-token", model_factory=FailingModel, persist_secrets=False)
    root = tmp_path / "workspace"
    root.mkdir()
    with TestClient(app, headers={"Authorization": "Bearer task-token"}) as api:
        a = api.post("/api/connections", json=values("A", "original-secret")).json()
        b = api.post("/api/connections", json=values("B", "other-secret")).json()
        api.post(f'/api/connections/{a["connection_id"]}/activate')
        workspace = api.post("/api/workspaces", json={"path": str(root)}).json()
        task = api.post("/api/tasks", json={"workspace_id": workspace["id"], "prompt": "read the project"}).json()
        assert started.wait(10)
        api.post(f'/api/connections/{b["connection_id"]}/activate')
        switched.set()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = api.get(f'/api/tasks/{task["id"]}').json()
            if result["status"] == "failed":
                break
            time.sleep(.02)
        assert result["status"] == "failed"
        assert "original-secret" not in result["result"]
        assert "[redacted]" in result["result"]
