"""Durable storage and JSON normalization for the local web UI."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import WORKDIR


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def json_safe(value: Any) -> Any:
    """Convert Anthropic SDK objects and other values into JSON data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return json_safe(model_dump())
        except Exception:
            pass
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return json_safe(to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return json_safe(vars(value))
    return str(value)


class ConversationStore:
    """Small file-backed conversation store; no database dependency required."""

    def __init__(self, root: Path | None = None):
        self.root = (root or WORKDIR / ".web_sessions").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, conversation_id: str) -> Path:
        if not conversation_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in conversation_id):
            raise ValueError("Invalid conversation id")
        return self.root / f"{conversation_id}.json"

    def _read(self, conversation_id: str) -> dict:
        path = self._path(conversation_id)
        if not path.is_file():
            raise FileNotFoundError(conversation_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, record: dict) -> dict:
        path = self._path(record["id"])
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(json_safe(record), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return record

    def list(self) -> list[dict]:
        with self._lock:
            records = []
            for path in self.root.glob("*.json"):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                    records.append(self.summary(record))
                except (OSError, json.JSONDecodeError):
                    continue
            return sorted(records, key=lambda item: item["updated_at"], reverse=True)

    @staticmethod
    def summary(record: dict) -> dict:
        messages = record.get("messages", [])
        return {
            "id": record["id"],
            "title": record.get("title") or "新对话",
            "workdir": record.get("workdir", str(WORKDIR)),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "status": record.get("status", "idle"),
            "message_count": len(messages),
            "last_message": next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""),
        }

    def get(self, conversation_id: str) -> dict:
        with self._lock:
            return self._read(conversation_id)

    def create(self, title: str = "", workdir: str | Path | None = None) -> dict:
        chosen = Path(workdir or WORKDIR).expanduser().resolve()
        if not chosen.is_dir():
            raise ValueError(f"Working directory does not exist: {chosen}")
        now = utc_now()
        record = {
            "id": uuid.uuid4().hex,
            "title": title.strip()[:120] or "新对话",
            "workdir": str(chosen),
            "created_at": now,
            "updated_at": now,
            "status": "idle",
            "messages": [],
            "debug_events": [],
        }
        with self._lock:
            return self._write(record)

    def update(self, conversation_id: str, **changes) -> dict:
        with self._lock:
            record = self._read(conversation_id)
            for key in ("title", "workdir", "status", "messages", "debug_events", "token_usage", "error"):
                if key in changes and changes[key] is not None:
                    record[key] = json_safe(changes[key])
            record["updated_at"] = utc_now()
            return self._write(record)

    def append_debug(self, conversation_id: str, event_type: str, payload: dict) -> dict:
        with self._lock:
            record = self._read(conversation_id)
            event = {"id": uuid.uuid4().hex, "type": event_type, "at": utc_now(), "data": json_safe(payload)}
            # Messages snapshots refresh the live conversation view but are not
            # recorded as debug events – otherwise the trace panel would dump the
            # whole history on every round trip.
            if event_type == "messages_snapshot":
                snapshot = payload.get("messages")
                if isinstance(snapshot, list):
                    record["messages"] = json_safe(snapshot)
                record["updated_at"] = event["at"]
                self._write(record)
                return event
            record.setdefault("debug_events", []).append(event)
            if event_type == "llm_usage":
                data = event["data"]
                usage = record.setdefault("token_usage", {})
                previous_requests = int(usage.get("request_count", 0))
                previous_calls = int(usage.get("call_count", previous_requests))
                usage["call_count"] = previous_calls + 1
                usage["request_count"] = previous_requests + max(
                    1, int(data.get("attempt_count", 1) or 1)
                )
                for key in (
                    "input_tokens", "output_tokens", "cache_creation_input_tokens",
                    "cache_read_input_tokens", "estimated_saved_input_tokens",
                ):
                    usage[key] = int(usage.get(key, 0)) + int(data.get(key, 0) or 0)
                usage["cache_hit_count"] = int(usage.get("cache_hit_count", 0)) + int(bool(data.get("cache_hit")))
                count = max(1, usage["call_count"])
                usage["cache_hit_rate"] = usage["cache_hit_count"] / count
                savings = data.get("estimated_savings_usd")
                if savings is not None:
                    usage["estimated_savings_usd"] = float(usage.get("estimated_savings_usd", 0)) + float(savings)
            record["updated_at"] = event["at"]
            self._write(record)
            return event
