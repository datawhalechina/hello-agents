
from __future__ import annotations

import contextlib
import re
import sqlite3
import time
from collections import Counter

from ...models.schemas import FeedbackActionEnum as FeedbackAction
from ...utils.common import exec_sql

@contextlib.contextmanager
def _conn(db_path: str):
    ensure_tables(db_path)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        """CREATE TABLE IF NOT EXISTS daily_recommend_feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date_key TEXT NOT NULL,
          paper_identity_key TEXT NOT NULL,
          identity_type TEXT NOT NULL,
          title TEXT,
          action TEXT NOT NULL,
          source_list TEXT,
          score_at_recommend REAL,
          created_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS paper_impressions (
          paper_identity_key TEXT PRIMARY KEY,
          identity_type TEXT NOT NULL,
          title TEXT,
          first_seen_date TEXT NOT NULL,
          last_seen_date TEXT NOT NULL,
          total_impressions INTEGER DEFAULT 0,
          clicks INTEGER DEFAULT 0,
          saves INTEGER DEFAULT 0,
          skips INTEGER DEFAULT 0,
          reads INTEGER DEFAULT 0,
          ctr REAL DEFAULT 0.0,
          save_rate REAL DEFAULT 0.0,
          skip_rate REAL DEFAULT 0.0,
          updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS user_interest_evolution (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date_key TEXT NOT NULL,
          keyword TEXT NOT NULL,
          category TEXT,
          interaction_weight REAL DEFAULT 0.0,
          source TEXT,
          created_at INTEGER NOT NULL,
          UNIQUE(date_key, keyword, category, source)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_feedback_date ON daily_recommend_feedback(date_key, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_paper ON daily_recommend_feedback(paper_identity_key, identity_type)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_action ON daily_recommend_feedback(action)",
        "CREATE INDEX IF NOT EXISTS idx_interest_date ON user_interest_evolution(date_key)",
        "CREATE INDEX IF NOT EXISTS idx_interest_kw ON user_interest_evolution(keyword, date_key)",
    )

def record_feedback(
    db_path: str,
    *,
    date_key: str,
    paper_identity_key: str,
    identity_type: str,
    title: str | None = None,
    action: FeedbackAction,
    source_list: str | None = None,
    score_at_recommend: float | None = None,
    keywords: list[str | None] = None,
    category: str | None = None,
) -> bool:
    try:
        now = int(time.time())
        with _conn(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO daily_recommend_feedback(date_key,paper_identity_key,identity_type,title,action,source_list,score_at_recommend,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (str(date_key), str(paper_identity_key), str(identity_type),
                 (title or "")[:400] if title else None, str(action.value),
                 source_list, float(score_at_recommend) if score_at_recommend is not None else None, now),
            )
            _update_impression_stats(cur, paper_identity_key, identity_type, title or "", date_key, action, now)
            if keywords:
                weight = _action_to_weight(action)
                for kw in keywords[:8]:
                    if kw and len(kw.strip()) >= 3:
                        _upsert_interest_evolution(cur, date_key, kw.strip(), category, weight, "feedback", now)
        return True
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"记录推荐反馈失败: {e}")
        return False

def _action_to_weight(action: FeedbackAction) -> float:
    weights = {
        FeedbackAction.SAVE: 3.0,
        FeedbackAction.READ: 2.5,
        FeedbackAction.CLICK: 1.5,
        FeedbackAction.SKIP: -1.0,
        FeedbackAction.IGNORE: 0.0,
    }
    return weights.get(action, 0.0)

def _update_impression_stats(
    cur: sqlite3.Cursor,
    paper_identity_key: str,
    identity_type: str,
    title: str,
    date_key: str,
    action: FeedbackAction,
    now: int,
) -> None:
    cur.execute(
        """
        SELECT total_impressions, clicks, saves, skips, reads
        FROM paper_impressions WHERE paper_identity_key = ?
        """,
        (str(paper_identity_key),),
    )
    row = cur.fetchone()

    if row:
        total, clicks, saves, skips, reads = row
        total = (total or 0) + 1
        clicks = (clicks or 0) + (1 if action == FeedbackAction.CLICK else 0)
        saves = (saves or 0) + (1 if action == FeedbackAction.SAVE else 0)
        skips = (skips or 0) + (1 if action == FeedbackAction.SKIP else 0)
        reads = (reads or 0) + (1 if action == FeedbackAction.READ else 0)
    else:
        total, clicks, saves, skips, reads = 1, 0, 0, 0, 0
        if action == FeedbackAction.CLICK:
            clicks = 1
        elif action == FeedbackAction.SAVE:
            saves = 1
        elif action == FeedbackAction.SKIP:
            skips = 1
        elif action == FeedbackAction.READ:
            reads = 1

    ctr = clicks / total if total > 0 else 0.0
    save_rate = saves / total if total > 0 else 0.0
    skip_rate = skips / total if total > 0 else 0.0

    cur.execute(
        """
        INSERT INTO paper_impressions
        (paper_identity_key, identity_type, title, first_seen_date, last_seen_date,
         total_impressions, clicks, saves, skips, reads, ctr, save_rate, skip_rate, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_identity_key) DO UPDATE SET
          title = excluded.title,
          last_seen_date = excluded.last_seen_date,
          total_impressions = excluded.total_impressions,
          clicks = excluded.clicks,
          saves = excluded.saves,
          skips = excluded.skips,
          reads = excluded.reads,
          ctr = excluded.ctr,
          save_rate = excluded.save_rate,
          skip_rate = excluded.skip_rate,
          updated_at = excluded.updated_at
        """,
        (
            str(paper_identity_key),
            str(identity_type),
            title[:400] if title else "",
            str(date_key),
            str(date_key),
            total,
            clicks,
            saves,
            skips,
            reads,
            ctr,
            save_rate,
            skip_rate,
            now,
        ),
    )

def _upsert_interest_evolution(
    cur: sqlite3.Cursor,
    date_key: str,
    keyword: str,
    category: str | None,
    weight: float,
    source: str,
    now: int,
) -> None:
    cur.execute(
        """
        INSERT INTO user_interest_evolution (date_key, keyword, category, interaction_weight, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(date_key, keyword, category, source) DO UPDATE SET
          interaction_weight = interaction_weight + excluded.interaction_weight,
          created_at = excluded.created_at
        """,
        (str(date_key), keyword.lower(), category, weight, source, now),
    )

def get_skipped_papers(
    db_path: str,
    *,
    days: int = 30,
    include_shown: bool = True,
) -> set[str]:
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    actions = ("skip", "shown") if include_shown else ("skip",)
    placeholders = ",".join("?" for _ in actions)
    with _conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT DISTINCT paper_identity_key FROM daily_recommend_feedback "
            f"WHERE date_key>=? AND action IN ({placeholders})",
            (cutoff, *actions),
        )
        skipped = {str(row[0]) for row in cur.fetchall()}
    return skipped


def clear_daily_shown_for_date(db_path: str, date_key: str) -> int:
    """手动刷新时清除当日 shown 记录，避免候选池被永久锁死。"""
    with _conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM daily_recommend_feedback WHERE date_key=? AND action='shown'",
            (str(date_key),),
        )
        return int(cur.rowcount or 0)

def record_daily_shown_papers(
    db_path: str,
    date_key: str,
    papers: list[dict[str, str]],
) -> None:
    if not papers:
        return
    now = int(time.time())
    with _conn(db_path) as conn:
        conn.cursor().executemany(
            """INSERT OR IGNORE INTO daily_recommend_feedback(date_key,paper_identity_key,identity_type,title,action,source_list,score_at_recommend,created_at)
            VALUES(?,?,'title_hash',?,'shown','daily',0.0,?)""",
            [(date_key, p.get("identity_key", ""), p.get("title", ""), now) for p in papers],
        )

def get_high_value_keywords_from_feedback(
    db_path: str,
    *,
    days: int = 21,
    top_n: int = 20,
) -> set[str]:
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    with _conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT title FROM daily_recommend_feedback WHERE date_key>=? AND action IN ('click','save','read') AND title IS NOT NULL ORDER BY created_at DESC LIMIT 200",
            (cutoff,),
        )
        titles = [str(row[0]) for row in cur.fetchall() if row[0]]

    def _extract_tokens(text: str) -> list[str]:
        t = (text or "").lower()
        t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
        tokens = [x.strip() for x in t.split() if x.strip()]
        stop = {
            "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
            "we", "our", "is", "are", "be", "via", "from", "this", "that",
            "using", "use", "based", "towards", "paper", "propose", "method",
            "learning", "network", "model", "deep", "neural",
        }
        return [x for x in tokens if x not in stop and len(x) >= 4][:50]

    all_tokens = []
    for t in titles:
        all_tokens.extend(_extract_tokens(t))

    freq = Counter(all_tokens)
    top_keywords = {w for w, _ in freq.most_common(top_n)}
    return top_keywords
