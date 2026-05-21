
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

@contextmanager
def _conn(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS paper_opening_cache(paper_id INTEGER PRIMARY KEY,opening TEXT,updated_at INTEGER,hit_count INTEGER DEFAULT 0,miss_count INTEGER DEFAULT 0,last_hit_at INTEGER,last_miss_at INTEGER)"
    )

def get_cached_opening(db_path: str, paper_id: int, max_age_hours: int = 72) -> tuple[str | None, bool]:
    if not db_path:
        return None, False
    now = int(time.time())
    try:
        with _conn(db_path) as conn:
            _ensure_table(conn)
            row = conn.execute("SELECT opening,updated_at FROM paper_opening_cache WHERE paper_id=?", (int(paper_id),)).fetchone()
            if not row:
                conn.execute(
                    "INSERT OR IGNORE INTO paper_opening_cache(paper_id,opening,updated_at,miss_count,last_miss_at) VALUES(?,?,?,?,?)",
                    (int(paper_id), "", 0, 1, now),
                )
                return None, False
            opening = (row[0] or "").strip()
            updated_at = int(row[1] or 0)
            fresh = bool(opening and updated_at and (now - updated_at) <= int(max_age_hours) * 3600)
            if opening:
                conn.execute(
                    "UPDATE paper_opening_cache SET hit_count=hit_count+1,last_hit_at=? WHERE paper_id=?",
                    (now, int(paper_id)),
                )
            else:
                conn.execute(
                    "UPDATE paper_opening_cache SET miss_count=miss_count+1,last_miss_at=? WHERE paper_id=?",
                    (now, int(paper_id)),
                )
            return (opening or None), fresh
    except Exception:
        return None, False

def set_cached_opening(db_path: str, paper_id: int, opening: str) -> None:
    if not db_path:
        return
    now = int(time.time())
    try:
        with _conn(db_path) as conn:
            _ensure_table(conn)
            conn.execute(
                "INSERT INTO paper_opening_cache(paper_id,opening,updated_at) VALUES(?,?,?) ON CONFLICT(paper_id) DO UPDATE SET opening=excluded.opening,updated_at=excluded.updated_at",
                (int(paper_id), str(opening or "").strip(), now),
            )
    except Exception:
        return
