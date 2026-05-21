
from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable

from ...utils.common import normalize_arxiv_id as _norm_arxiv_id
from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        """CREATE TABLE IF NOT EXISTS daily_recommendations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date_key TEXT NOT NULL,
          source TEXT NOT NULL,
          arxiv_id TEXT,
          title TEXT,
          created_at INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_daily_reco_date ON daily_recommendations(date_key, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_daily_reco_arxiv ON daily_recommendations(source, arxiv_id)",
    )

def record_arxiv_recommendations(
    db_path: str,
    *,
    date_key: str,
    items: Iterable[tuple[str | None, str]],
) -> int:
    ensure_tables(db_path)
    now = int(time.time())
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        n = 0
        for arxiv_id, title in items:
            aid = _norm_arxiv_id(arxiv_id)
            t = (title or "").strip()
            cur.execute(
                """
                INSERT INTO daily_recommendations(date_key, source, arxiv_id, title, created_at)
                VALUES(?,?,?,?,?)
                """,
                (str(date_key), "arxiv", aid, t[:400] if t else None, int(now)),
            )
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()
