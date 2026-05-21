
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        """CREATE TABLE IF NOT EXISTS daily_papers_cache (
          date_key TEXT NOT NULL,
          cache_key TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL,
          hit_count INTEGER DEFAULT 0,
          PRIMARY KEY (date_key, cache_key)
        )""",
    )

def get_cache(db_path: str, *, date_key: str, cache_key: str) -> dict[str, Any | None]:
    ensure_tables(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload_json FROM daily_papers_cache WHERE date_key=? AND cache_key=?",
            (str(date_key), str(cache_key)),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw = row[0] or ""
        try:
            data = json.loads(raw)
        except Exception:
            data = None

        try:
            cur.execute(
                "UPDATE daily_papers_cache SET hit_count=hit_count+1, updated_at=? WHERE date_key=? AND cache_key=?",
                (int(time.time()), str(date_key), str(cache_key)),
            )
            conn.commit()
        except Exception:
            pass
        return data if isinstance(data, dict) else None
    finally:
        conn.close()

def set_cache(db_path: str, *, date_key: str, cache_key: str, payload: dict[str, Any]) -> None:
    ensure_tables(db_path)
    now = int(time.time())
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO daily_papers_cache(date_key, cache_key, payload_json, created_at, updated_at, hit_count)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(date_key, cache_key) DO UPDATE SET
              payload_json=excluded.payload_json,
              updated_at=excluded.updated_at
            """,
            (str(date_key), str(cache_key), json.dumps(payload, ensure_ascii=False), now, now, 0),
        )
        conn.commit()
    finally:
        conn.close()
