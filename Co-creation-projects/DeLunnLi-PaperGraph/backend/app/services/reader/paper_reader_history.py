"""阅读历史记录 —— 对话会话持久化、恢复与上下文延续."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        "CREATE TABLE IF NOT EXISTS paper_reader_turns(id INTEGER PRIMARY KEY AUTOINCREMENT,paper_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL,is_opening INTEGER NOT NULL DEFAULT 0)",
        "CREATE INDEX IF NOT EXISTS idx_paper_reader_turns_paper ON paper_reader_turns(paper_id,created_at)",
    )
    with _conn(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(paper_reader_turns)")}
        if "is_opening" not in columns:
            try:
                conn.execute("ALTER TABLE paper_reader_turns ADD COLUMN is_opening INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                if "is_opening" not in {r[1] for r in conn.execute("PRAGMA table_info(paper_reader_turns)")}:
                    raise
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reader_single_opening ON paper_reader_turns(paper_id) WHERE is_opening=1")


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
    ensure_tables(db_path)
    with _conn(db_path, row_factory=sqlite3.Row) as conn:
        # Serialize adoption/insertion of the single generated opening. Ordinary
        # chat turns never participate in updates after this explicit marker.
        conn.execute("BEGIN IMMEDIATE")
        marked = conn.execute(
            "SELECT id FROM paper_reader_turns WHERE paper_id=? AND is_opening=1",
            (int(paper_id),),
        ).fetchone()
        if marked:
            conn.execute("UPDATE paper_reader_turns SET content=? WHERE id=?", (op, marked["id"]))
            return
        first = conn.execute(
            "SELECT id,role,content,created_at FROM paper_reader_turns WHERE paper_id=? ORDER BY created_at ASC,id ASC LIMIT 1",
            (int(paper_id),),
        ).fetchone()
        previous_opening = None
        try:
            cache = conn.execute("SELECT opening FROM paper_opening_cache WHERE paper_id=?", (int(paper_id),)).fetchone()
            previous_opening = (cache["opening"] or "").strip() if cache else None
        except sqlite3.OperationalError:
            pass  # Existing history databases need not have an opening cache.
        if first and previous_opening and first["role"] == "assistant" and first["content"].strip() == previous_opening:
            conn.execute("UPDATE paper_reader_turns SET content=?,is_opening=1 WHERE id=?", (op, first["id"]))
            return
        # An unmarked assistant reply that does not match the cache is ordinary
        # history. Preserve it and add an explicit opening before all chat turns.
        created_at = int(first["created_at"]) - 1 if first else int(time.time())
        conn.execute(
            "INSERT INTO paper_reader_turns(paper_id,role,content,created_at,is_opening) VALUES(?,?,?,?,1)",
            (int(paper_id), "assistant", op, created_at),
        )

def list_turns(db_path: str, *, paper_id: int, limit: int = 200) -> list[dict[str, str | None]]:
    ensure_tables(db_path)
    with _conn(db_path, row_factory=sqlite3.Row) as conn:
        rows = conn.execute(
            "SELECT role,content,created_at FROM paper_reader_turns WHERE paper_id=? ORDER BY created_at DESC,id DESC LIMIT ?",
            (int(paper_id), max(1, min(1000, int(limit)))),
        ).fetchall()
        out: list[dict[str, str | None]] = []
        for r in reversed(rows):
            out.append({
                "role": (r["role"] or "").strip(),
                "content": (r["content"] or "").strip(),
                "created_at": int(r["created_at"] or 0),
            })
        return out
