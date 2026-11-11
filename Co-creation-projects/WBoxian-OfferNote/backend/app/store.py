from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return uuid.uuid4().hex


class Conflict(Exception):
    pass


class Store:
    """One JSON aggregate per workspace; revisions prevent lost concurrent writes."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, workspace_id TEXT, created_at TEXT, data TEXT)"
            )

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def create(
        self,
        name: str,
        role: str,
        resume: str = "",
        job: str = "",
        *,
        workspace_id: str | None = None,
        demo_role: str | None = None,
    ) -> dict:
        item = {
            "id": workspace_id or uid(),
            "demo_role": demo_role,
            "name": name,
            "role": role,
            "resume": resume,
            "job": job,
            "created_at": now(),
            "updated_at": now(),
            "analysis": None,
            "sessions": [],
            "revision": 0,
        }
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO workspaces VALUES (?, ?, ?)",
                (item["id"], 0, json.dumps(item, ensure_ascii=False)),
            )
        return self.get(item["id"])

    def ensure_demos(self):
        from .demo import PROFILES

        # 仅迁移内置演示；个人工作区及其历史不参与清理。
        with self.connect() as conn:
            for key in ("product", "algorithm"):
                row = conn.execute(
                    "SELECT data FROM workspaces WHERE id=?", ("demo-" + key,)
                ).fetchone()
                if row and json.loads(row["data"]).get("demo_role") == key:
                    conn.execute(
                        "DELETE FROM events WHERE workspace_id=?", ("demo-" + key,)
                    )
                    conn.execute("DELETE FROM workspaces WHERE id=?", ("demo-" + key,))
        for key, profile in PROFILES.items():
            self.create(
                profile["name"],
                profile["role"],
                profile["resume"],
                profile["job"],
                workspace_id="demo-" + key,
                demo_role=key,
            )
        item = self.get("demo-development")
        if item.get("demo_role") == "development":
            sessions = [s for s in item["sessions"] if s["mode"] != "demo"]
            offline_analysis = item["analysis"] and item["analysis"]["mode"] == "demo"
            if sessions != item["sessions"] or offline_analysis:
                item["sessions"] = sessions
                if offline_analysis:
                    item["analysis"] = None
                self.save(item, item["revision"])

    def get(self, key: str) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT data FROM workspaces WHERE id=?", (key,)
            ).fetchone()
        if not row:
            raise KeyError(key)
        return json.loads(row["data"])

    def list(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT data FROM workspaces").fetchall()
        items = [json.loads(row["data"]) for row in rows]
        return sorted(items, key=lambda item: item["updated_at"], reverse=True)

    def save(self, item: dict, expected_revision: int) -> dict:
        item = {**item, "revision": expected_revision + 1, "updated_at": now()}
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE workspaces SET revision=?,data=? WHERE id=? AND revision=?",
                (
                    item["revision"],
                    json.dumps(item, ensure_ascii=False),
                    item["id"],
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise Conflict("材料或会话已被另一请求更新，请刷新后重试。")
        return item

    def delete(self, key: str):
        self.get(key)
        with self.connect() as conn:
            conn.execute("DELETE FROM workspaces WHERE id=?", (key,))
            conn.execute("DELETE FROM events WHERE workspace_id=?", (key,))

    def event(self, workspace_id: str, data: dict):
        event = {"id": uid(), "created_at": now(), **data}
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO events SELECT ?,?,?,? WHERE EXISTS (SELECT 1 FROM workspaces WHERE id=?)",
                (
                    event["id"],
                    workspace_id,
                    event["created_at"],
                    json.dumps(event, ensure_ascii=False),
                    workspace_id,
                ),
            )

    def events(self, key: str, *, model_only: bool = False) -> list[dict]:
        self.get(key)
        # 在 LIMIT 前过滤，避免工具细项挤掉真正有用量的模型记录。
        model_filter = (
            """
            AND json_extract(data, '$.mode') = 'live'
            AND json_extract(data, '$.stage') != 'tool'
            AND (
                json_extract(data, '$.tokens') > 0
                OR (
                    COALESCE(json_extract(data, '$.model_requests'), 1) > 0
                    AND (
                        json_extract(data, '$.tokens') IS NULL
                        OR COALESCE(json_extract(data, '$.usage_complete'), 1) = 0
                    )
                )
            )
        """
            if model_only
            else ""
        )
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT data FROM events WHERE workspace_id=? "
                + model_filter
                + " ORDER BY created_at DESC LIMIT 100",
                (key,),
            ).fetchall()
        return [json.loads(row["data"]) for row in rows]
