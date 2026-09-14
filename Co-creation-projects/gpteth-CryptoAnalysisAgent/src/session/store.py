"""Multi-session chat history persisted as JSON files."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from ..workspace.manager import WorkspaceManager


class SessionStore:
    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace

    def _path(self, session_id: str) -> str:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")
        if not safe:
            raise ValueError("invalid session id")
        return os.path.join(self.workspace.sessions_path, f"{safe}.json")

    def create(self, title: str = "") -> str:
        session_id = uuid.uuid4().hex[:10]
        now = time.time()
        self._write(session_id, {
            "id": session_id,
            "title": title or "新会话",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        })
        return session_id

    def list(self) -> list[dict]:
        os.makedirs(self.workspace.sessions_path, exist_ok=True)
        sessions = []
        for filename in os.listdir(self.workspace.sessions_path):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.workspace.sessions_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
            sessions.append({
                "id": data.get("id") or filename[:-5],
                "title": data.get("title") or "会话",
                "created_at": data.get("created_at") or os.path.getctime(filepath),
                "updated_at": data.get("updated_at") or os.path.getmtime(filepath),
            })
        return sorted(sessions, key=lambda item: item["updated_at"], reverse=True)

    def get(self, session_id: str) -> dict | None:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def history(self, session_id: str) -> list[dict]:
        data = self.get(session_id)
        if not data:
            return []
        return list(data.get("messages") or [])

    def append(self, session_id: str, role: str, content: str, **extra: Any) -> None:
        data = self.get(session_id)
        if data is None:
            now = time.time()
            data = {
                "id": session_id,
                "title": _title_from(content) if role == "user" else "新会话",
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
        message = {"role": role, "content": content}
        message.update(extra)
        data["messages"].append(message)
        data["updated_at"] = time.time()
        if role == "user" and (not data.get("title") or data.get("title") == "新会话"):
            data["title"] = _title_from(content)
        self._write(session_id, data)

    def save_turn(self, session_id: str, user_message: str, assistant_message: str, tools: list[dict] | None = None) -> None:
        self.append(session_id, "user", user_message)
        payload: dict[str, Any] = {}
        if tools:
            payload["metadata"] = {"tools": tools}
        self.append(session_id, "assistant", assistant_message, **payload)

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _write(self, session_id: str, data: dict) -> None:
        os.makedirs(self.workspace.sessions_path, exist_ok=True)
        path = self._path(session_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def _title_from(content: str) -> str:
    text = (content or "").strip().replace("\n", " ")
    return (text[:24] + "…") if len(text) > 24 else (text or "新会话")
