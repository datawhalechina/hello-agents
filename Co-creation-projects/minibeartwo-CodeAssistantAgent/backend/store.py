"""SQLite persistence for workspaces, conversations, tasks, events and checkpoints."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def identifier() -> str:
    return uuid.uuid4().hex


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS workspaces (
                  id TEXT PRIMARY KEY, root TEXT NOT NULL UNIQUE, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                  title TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                  prompt TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
                  messages TEXT NOT NULL DEFAULT '[]', test_argv TEXT NOT NULL DEFAULT '[]',
                  selected_file TEXT, steps INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                  kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_task ON events(task_id,id);
                CREATE TABLE IF NOT EXISTS patches (
                  id TEXT PRIMARY KEY, task_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                  status TEXT NOT NULL, changes TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (
                  key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS annotation_progress (
                  task_id TEXT PRIMARY KEY, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS annotation_drafts (
                  task_id TEXT NOT NULL, path TEXT NOT NULL, base_hash TEXT NOT NULL,
                  state TEXT NOT NULL, PRIMARY KEY(task_id,path));
                CREATE TABLE IF NOT EXISTS annotation_draft_owners (
                  task_id TEXT PRIMARY KEY, owner TEXT NOT NULL);
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(tasks)")}
            if "elapsed" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN elapsed REAL NOT NULL DEFAULT 0")
            if "skill" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN skill TEXT")
            if "skill_instructions" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN skill_instructions TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connect(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    def rows(self, query: str, params=()) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute(query, params)]

    def one(self, table: str, item_id: str) -> dict:
        if table not in {"workspaces", "sessions", "tasks", "patches"}:
            raise ValueError("Unknown table")
        rows = self.rows(f"SELECT * FROM {table} WHERE id=?", (item_id,))
        if not rows:
            raise LookupError(f"{table} record not found")
        return rows[0]

    def execute(self, query: str, params=()):
        with self.connect() as db:
            db.execute(query, params)

    def update_task(self, task_id: str, **values):
        allowed = {"status", "result", "messages", "steps", "elapsed"}
        if not values or not values.keys() <= allowed:
            raise ValueError("Invalid task update")
        values["updated_at"] = now()
        self.execute(
            "UPDATE tasks SET " + ",".join(f"{key}=?" for key in values) + " WHERE id=?",
            (*values.values(), task_id),
        )

    def delete_task(self, task_id: str):
        """Delete a task and its records atomically, without touching files."""
        with self.connect() as db:
            task = db.execute("SELECT session_id FROM tasks WHERE id=?", (task_id,)).fetchone()
            if task is None:
                raise LookupError("tasks record not found")
            db.execute("DELETE FROM events WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM patches WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM annotation_progress WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM annotation_drafts WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM annotation_draft_owners WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            db.execute("DELETE FROM sessions WHERE id=? AND NOT EXISTS (SELECT 1 FROM tasks WHERE session_id=?)",
                       (task["session_id"], task["session_id"]))

    def event(self, task_id: str, kind: str, data: dict) -> dict:
        created = now()
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO events(task_id,kind,data,created_at) VALUES(?,?,?,?)",
                (task_id, kind, json.dumps(data, ensure_ascii=False), created),
            )
            event_id = cursor.lastrowid
        return {"id": event_id, "task_id": task_id, "kind": kind, "data": data, "created_at": created}

    def events(self, task_id: str, after: int = 0) -> list[dict]:
        rows = self.rows("SELECT * FROM events WHERE task_id=? AND id>? ORDER BY id LIMIT 500", (task_id, after))
        for row in rows:
            row["data"] = json.loads(row["data"])
        return rows

    def settings(self) -> dict:
        return {row["key"]: json.loads(row["value"]) for row in self.rows("SELECT * FROM settings")}

    def set_settings(self, values: dict):
        with self.connect() as db:
            for key, value in values.items():
                db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(value)))

    def recover(self):
        for task in self.rows("SELECT * FROM tasks WHERE status IN ('queued','running','cancelling')"):
            self.update_task(task["id"], status="interrupted", result="服务已重启。任务被中断，请创建新任务继续。")
            self.event(task["id"], "task.interrupted", {"message": "服务重启，未自动重复执行任务。"})
        self.execute("UPDATE patches SET status='recovery_required' WHERE status IN ('applying','undoing')")
