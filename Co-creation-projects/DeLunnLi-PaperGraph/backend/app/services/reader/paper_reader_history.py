
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        "CREATE TABLE IF NOT EXISTS paper_reader_turns(id INTEGER PRIMARY KEY AUTOINCREMENT,paper_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_paper_reader_turns_paper ON paper_reader_turns(paper_id,created_at)",
    )

@contextmanager
def _conn(db_path: str, *, row_factory=None):
    conn = sqlite3.connect(db_path)
    if row_factory:
        conn.row_factory = row_factory
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def append_turn(db_path: str, *, paper_id: int, role: str, content: str) -> None:
    ensure_tables(db_path)
    role2 = (role or "").strip().lower()
    if role2 not in ("user", "assistant"):
        role2 = "user"
    text = (content or "").strip()
    if not text:
        return
    now = int(time.time())
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO paper_reader_turns(paper_id,role,content,created_at) VALUES(?,?,?,?)",
            (int(paper_id), role2, text, now),
        )

def prepend_turn(
    db_path: str,
    *,
    paper_id: int,
    role: str,
    content: str,
    before_created_at: int,
) -> None:
    ensure_tables(db_path)
    role2 = (role or "").strip().lower()
    if role2 not in ("user", "assistant"):
        role2 = "user"
    text = (content or "").strip()
    if not text:
        return
    ts = int(before_created_at) - 1
    if ts < 0:
        ts = 0
    now = int(time.time())
    if ts >= now:
        ts = now - 1
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO paper_reader_turns(paper_id,role,content,created_at) VALUES(?,?,?,?)",
            (int(paper_id), role2, text, ts),
        )

def ensure_opening_turn(db_path: str, *, paper_id: int, opening_text: str) -> None:
    op = (opening_text or "").strip()
    if not op:
        return
    turns = list_turns(db_path, paper_id=int(paper_id), limit=5)
    if not turns:
        append_turn(db_path, paper_id=int(paper_id), role="assistant", content=op)
        return
    first = turns[0]
    r0 = (first.get("role") or "").strip().lower()
    c0 = (first.get("content") or "").strip()
    if r0 == "assistant" and c0 == op:
        return
    if r0 == "assistant":
        return
    if r0 == "user":
        try:
            ts0 = int(first.get("created_at") or 0)
        except Exception:
            ts0 = int(time.time())
        prepend_turn(db_path, paper_id=int(paper_id), role="assistant", content=op, before_created_at=ts0)
        return

def list_turns(db_path: str, *, paper_id: int, limit: int = 200) -> list[dict[str, str | None]]:
    ensure_tables(db_path)
    with _conn(db_path, row_factory=sqlite3.Row) as conn:
        rows = conn.execute(
            "SELECT role,content,created_at FROM paper_reader_turns WHERE paper_id=? ORDER BY created_at ASC,id ASC LIMIT ?",
            (int(paper_id), int(limit)),
        ).fetchall()
        out: list[dict[str, str | None]] = []
        for r in rows:
            out.append({
                "role": (r["role"] or "").strip(),
                "content": (r["content"] or "").strip(),
                "created_at": int(r["created_at"] or 0),
            })
        return out
