"""Saved model connections with separate OS-keyring secrets and one active connection."""
from __future__ import annotations

import os
from urllib.parse import urlparse

from .store import Store, identifier

DEFAULT_MAX_STEPS = 1000


class Settings:
    def __init__(self, store: Store, persist_secrets: bool = True):
        self.store = store
        self.keyring = None
        self.keys = {}
        self.memory_key, self.storage = "", "none"
        if persist_secrets:
            try:
                import keyring
                self.keyring = keyring
            except Exception:
                pass
        saved = store.settings()
        # Retired wall-clock limits must not survive profile selection or restart.
        if "task_timeout" in saved:
            store.execute("DELETE FROM settings WHERE key=?", ("task_timeout",))
        if any("task_timeout" in record for record in saved.get("connections", [])):
            records = [{key: value for key, value in record.items() if key != "task_timeout"}
                       for record in saved["connections"]]
            store.set_settings({"connections": records})
        saved = store.settings()
        if "connections" not in saved:
            # Import the previous single connection once, including its existing secret.
            key = os.getenv("LLM_API_KEY", "")
            storage = "environment" if key else "none"
            if self.keyring:
                try:
                    legacy = self.keyring.get_password("CodeAssistantAgent", "model-api-key")
                    if legacy:
                        key, storage = legacy, "keyring"
                except Exception:
                    self.keyring = None
            current = self.public()
            if current["model"] and current["base_url"]:
                connection_id = identifier()
                record = {"id": connection_id, "name": "默认配置", **self._fields(current)}
                self.keys[connection_id] = (key, storage)
                if key and self.keyring:
                    self._save_key(connection_id, key)
                store.set_settings({**self._fields(current), "connections": [record],
                                    "active_connection_id": connection_id,
                                    "environment_connection_id": connection_id if storage == "environment" else None})
            else:
                self.memory_key, self.storage = key, storage
        active = store.settings().get("active_connection_id")
        if active:
            self.memory_key, self.storage = self._secret(active)

    @staticmethod
    def _fields(values: dict) -> dict:
        return {key: values[key] for key in ("model", "base_url", "max_steps")}

    def _records(self) -> list[dict]:
        return self.store.settings().get("connections", [])

    def _record(self, connection_id: str) -> dict:
        for record in self._records():
            if record["id"] == connection_id:
                return record
        raise LookupError("保存的配置不存在，请刷新配置列表。")

    def _secret(self, connection_id: str) -> tuple[str, str]:
        if connection_id not in self.keys:
            key = ""
            if self.keyring:
                try:
                    key = self.keyring.get_password("CodeAssistantAgent", "model-api-key:" + connection_id) or ""
                except Exception:
                    pass
            storage = "keyring" if key else "none"
            if not key and self.store.settings().get("environment_connection_id") == connection_id:
                record = self._record(connection_id)
                if record["base_url"].rstrip("/") == os.getenv("LLM_BASE_URL", "").strip().rstrip("/"):
                    key = os.getenv("LLM_API_KEY", "")
                    storage = "environment" if key else "none"
            self.keys[connection_id] = (key, storage)
        return self.keys[connection_id]

    def _save_key(self, connection_id: str, key: str):
        storage = "memory"
        if self.keyring:
            try:
                self.keyring.set_password("CodeAssistantAgent", "model-api-key:" + connection_id, key)
                storage = "keyring"
            except Exception:
                pass
        self.keys[connection_id] = (key, storage)

    def _clear_key(self, connection_id: str):
        self.keys[connection_id] = ("", "none")
        if self.keyring:
            try:
                self.keyring.delete_password("CodeAssistantAgent", "model-api-key:" + connection_id)
            except Exception:
                pass

    def public(self) -> dict:
        saved = self.store.settings()
        connection_id = saved.get("active_connection_id")
        name = next((item["name"] for item in saved.get("connections", [])
                     if item["id"] == connection_id), "")
        return {"model": saved.get("model", os.getenv("LLM_MODEL_ID", "")),
                "base_url": saved.get("base_url", os.getenv("LLM_BASE_URL", "")),
                "max_steps": saved.get("max_steps", DEFAULT_MAX_STEPS),
                "has_api_key": bool(self.memory_key), "key_storage": self.storage,
                "connection_id": connection_id, "connection_name": name}

    def connections(self) -> dict:
        records = []
        for record in self._records():
            key, storage = self._secret(record["id"])
            records.append({**record, "has_api_key": bool(key), "key_storage": storage})
        return {"connections": records, "active_id": self.public()["connection_id"]}

    def key_for(self, endpoint: str, connection_id: str | None = None) -> str:
        if connection_id:
            record = self._record(connection_id)
            return self._secret(connection_id)[0] if endpoint == record["base_url"] else ""
        return self.memory_key if endpoint == self.public()["base_url"].strip().rstrip("/") else ""

    def activate(self, connection_id: str) -> dict:
        record = self._record(connection_id)
        self.store.set_settings({**self._fields(record), "active_connection_id": connection_id})
        self.memory_key, self.storage = self._secret(connection_id)
        return self.public()

    def delete_connection(self, connection_id: str) -> dict:
        self._record(connection_id)
        records = [item for item in self._records() if item["id"] != connection_id]
        saved = self.store.settings()
        changes = {"connections": records}
        if saved.get("environment_connection_id") == connection_id:
            changes["environment_connection_id"] = None
        if saved.get("active_connection_id") == connection_id:
            replacement = records[0] if records else None
            changes.update(self._fields(replacement) if replacement else {
                "model": "", "base_url": "", "max_steps": DEFAULT_MAX_STEPS})
            changes["active_connection_id"] = replacement["id"] if replacement else None
        self.store.set_settings(changes)
        self._clear_key(connection_id)
        self.keys.pop(connection_id, None)
        active = self.store.settings().get("active_connection_id")
        self.memory_key, self.storage = self._secret(active) if active else ("", "none")
        return {"settings": self.public(), **self.connections()}

    def save_connection(self, values: dict) -> dict:
        endpoint = values.get("base_url", "").strip().rstrip("/")
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("模型地址需要为有效的 HTTP(S) API 地址。")
        if not values.get("model", "").strip():
            raise ValueError("请输入模型名称。")
        connection_id = values.get("id") or identifier()
        existing = self._record(connection_id) if values.get("id") else None
        fields = {"model": values["model"].strip(), "base_url": endpoint,
                  "max_steps": max(1, int(values.get("max_steps", DEFAULT_MAX_STEPS)))}
        name = values.get("name", "").strip() or (existing["name"] if existing else "")
        record = {"id": connection_id, "name": name or (parsed.hostname + " / " + fields["model"])[:100], **fields}
        key = values.get("api_key", "").strip()
        if key:
            self._save_key(connection_id, key)
        elif not existing or endpoint != existing["base_url"]:
            self._clear_key(connection_id)
        records = self._records()
        records = [record if item["id"] == connection_id else item for item in records]
        if not existing:
            records.append(record)
        metadata = {}
        if self.store.settings().get("environment_connection_id") == connection_id and (
                key or not existing or endpoint != existing["base_url"]):
            metadata["environment_connection_id"] = None
        self.store.set_settings({**fields, **metadata, "connections": records, "active_connection_id": connection_id})
        self.memory_key, self.storage = self._secret(connection_id)
        return self.public()

    def save(self, values: dict) -> dict:
        # Preserve the original settings API: update its active connection in place.
        connection_id = self.public()["connection_id"]
        return self.save_connection({**values, "id": connection_id,
                                     "name": self.public()["connection_name"]})
