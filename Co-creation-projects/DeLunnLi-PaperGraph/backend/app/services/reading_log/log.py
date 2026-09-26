"""阅读日志服务 —— 论文阅读时间记录、阅读日历数据生成与统计."""

from __future__ import annotations
import datetime as _dt, sqlite3, time

def ensure_tables(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        # Serialize schema inspection/upgrade when concurrent beacons arrive on an old DB.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS paper_reading_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NOT NULL, duration_sec INTEGER NOT NULL,
          day_key TEXT NOT NULL, created_at INTEGER NOT NULL, session_id TEXT)""")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(paper_reading_sessions)")}
        if "session_id" not in cols:
            conn.execute("ALTER TABLE paper_reading_sessions ADD COLUMN session_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prs_day ON paper_reading_sessions(day_key, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prs_paper ON paper_reading_sessions(paper_id, created_at)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_prs_session ON paper_reading_sessions(paper_id, session_id)")

def append_session(
    db_path: str, *, paper_id: int, duration_sec: int,
    client_ts: int | None = None, session_id: str | None = None,
) -> None:
    if not db_path or int(duration_sec or 0) <= 0:
        return
    ensure_tables(db_path)
    dur = min(int(duration_sec), 86400)
    ts = int(client_ts) if client_ts else int(time.time())
    day = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO paper_reading_sessions(paper_id,duration_sec,day_key,created_at,session_id)
               VALUES(?,?,?,?,?)
               ON CONFLICT(paper_id,session_id) DO UPDATE SET
                 duration_sec=MAX(paper_reading_sessions.duration_sec,excluded.duration_sec)""",
            (int(paper_id), dur, day, int(time.time()), (session_id or "").strip() or None),
        )
        conn.commit()
    finally:
        conn.close()

def list_daily_aggregate(db_path: str, *, days: int = 180) -> list[dict[str, int | str]]:
    if not db_path:
        return []
    ensure_tables(db_path)
    d = max(7, min(int(days or 180), 366))
    start = _dt.datetime.fromtimestamp(int(time.time()) - (d - 1) * 86400).strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT day_key, SUM(duration_sec) AS seconds, COUNT(*) AS sessions FROM paper_reading_sessions WHERE day_key>=? GROUP BY day_key ORDER BY day_key",
            (start,)).fetchall()
        return [{"date": r["day_key"], "seconds": int(r["seconds"] or 0), "sessions": int(r["sessions"] or 0)} for r in rows]
    finally:
        conn.close()
