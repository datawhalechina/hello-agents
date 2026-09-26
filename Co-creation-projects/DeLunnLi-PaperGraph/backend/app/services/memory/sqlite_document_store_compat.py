from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class SQLiteDocumentStore:
    """Small compatibility store for the subset of hello-agents memory APIs we use."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_tables(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS memories (
                        memory_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL DEFAULT 'working',
                        importance REAL DEFAULT 0.5,
                        properties TEXT DEFAULT '{}',
                        timestamp REAL NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )"""
                )
                columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(memories)")}
                if "properties" not in columns:
                    conn.execute("ALTER TABLE memories ADD COLUMN properties TEXT DEFAULT '{}'")
                    if "metadata" in columns:
                        conn.execute("UPDATE memories SET properties = metadata WHERE metadata IS NOT NULL")
                if "timestamp" not in columns:
                    conn.execute("ALTER TABLE memories ADD COLUMN timestamp REAL DEFAULT 0")
                    conn.execute("UPDATE memories SET timestamp = COALESCE(updated_at, created_at, 0)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, memory_type)"
                )
                conn.commit()
            finally:
                conn.close()

    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "working",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        memory_id: str | None = None,
        timestamp: float | None = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        mid = str(memory_id or uuid.uuid4().hex)
        now = time.time()
        event_time = float(timestamp if timestamp is not None else now)
        values = properties if properties is not None else metadata
        props_json = json.dumps(values or {}, ensure_ascii=False)
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO memories
                       (memory_id, user_id, content, memory_type, importance, properties,
                        timestamp, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mid, user_id, content, memory_type, importance, props_json,
                     event_time, now, now),
                )
                conn.commit()
            finally:
                conn.close()
        return mid

    def delete_memory(self, memory_id: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def search_memories(
        self,
        user_id: str,
        memory_type: str = "",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        where = "WHERE user_id = ?"
        params: list[Any] = [user_id]
        if memory_type:
            where += " AND memory_type = ?"
            params.append(memory_type)
        params.append(max(1, int(limit)))
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    f"""SELECT memory_id, user_id, content, memory_type, importance,
                               properties, timestamp, created_at, updated_at
                        FROM memories {where}
                        ORDER BY timestamp DESC, updated_at DESC LIMIT ?""",
                    params,
                ).fetchall()
            finally:
                conn.close()
        result: List[Dict[str, Any]] = []
        for row in rows:
            try:
                props = json.loads(row[5]) if row[5] else {}
            except (TypeError, json.JSONDecodeError):
                props = {}
            result.append({
                "memory_id": row[0],
                "user_id": row[1],
                "content": row[2],
                "memory_type": row[3],
                "importance": row[4],
                "properties": props,
                "metadata": props,
                "timestamp": row[6],
                "created_at": row[7],
                "updated_at": row[8],
            })
        return result
