
from __future__ import annotations

import contextlib
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass

from ...utils import build_in_clause

@dataclass
class UserInterestProfile:

    top_keywords: list[tuple[str, float]]

    top_subdomains: list[tuple[str, float]]

    high_interest_paper_ids: list[int]

    recent_active_topics: list[str]

    preferred_years: list[int]

    preferred_sources: list[str]

class UserBehaviorAnalytics:

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextlib.contextmanager
    def _cursor(self):
        conn = self._get_connection()
        try:
            yield conn.cursor()
        finally:
            conn.close()

    def extract_keywords_from_text(self, text: str) -> list[str]:

        if not text:
            return []
        t = text.lower()
        t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
        tokens = [x.strip() for x in t.split() if x.strip()]
        stop = {
            "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
            "we", "our", "is", "are", "be", "via", "from", "this", "that",
            "using", "use", "based", "towards", "paper", "propose", "method",
            "learning", "network", "model", "deep", "neural",
        }
        return [x for x in tokens if x not in stop and len(x) >= 4][:200]

    def get_papers_by_reading_time(
        self, *, days: int = 30, min_duration: int = 30, top_n: int = 50,
    ) -> list[tuple[int, float]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT paper_id,SUM(duration_sec) AS total_duration FROM paper_reading_sessions WHERE day_key>=date('now',?) AND duration_sec>=? GROUP BY paper_id ORDER BY total_duration DESC LIMIT ?",
                (f"-{days} days", min_duration, top_n),
            )
            return [(int(r["paper_id"]), float(r["total_duration"])) for r in cur.fetchall()]

    def get_papers_by_reading_frequency(
        self, *, days: int = 30, min_sessions: int = 2, top_n: int = 30,
    ) -> list[tuple[int, int]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT paper_id,COUNT(*) AS session_count FROM paper_reading_sessions WHERE day_key>=date('now',?) GROUP BY paper_id HAVING COUNT(*)>=? ORDER BY session_count DESC LIMIT ?",
                (f"-{days} days", min_sessions, top_n),
            )
            return [(int(r["paper_id"]), int(r["session_count"])) for r in cur.fetchall()]

    def get_recently_saved_papers(
        self, *, days: int = 30, top_n: int = 50,
    ) -> list[tuple[int, str]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id,category FROM papers WHERE created_at>=strftime('%s','now',?) ORDER BY created_at DESC LIMIT ?",
                (f"-{days} days", top_n),
            )
            return [(int(r["id"]), str(r["category"] or "")) for r in cur.fetchall()]

    def extract_keywords_from_high_interest_papers(
        self, paper_ids: list[int],
    ) -> Counter[str]:
        if not paper_ids:
            return Counter()
        with self._cursor() as cur:
            in_clause, params = build_in_clause("id", paper_ids)
            cur.execute(f"SELECT title,abstract,keywords FROM papers WHERE {in_clause}", params)
            all_kw: list[str] = []
            for row in cur.fetchall():
                all_kw.extend(self.extract_keywords_from_text(str(row["title"] or "")))
                all_kw.extend(self.extract_keywords_from_text(str(row["abstract"] or "")))
                for kw in (str(row["keywords"] or "")).split(","):
                    k = kw.strip().lower()
                    if k and len(k) >= 3:
                        all_kw.append(k)
        return Counter(all_kw)

    def get_interest_subdomains_from_papers(self, paper_ids: list[int]) -> Counter[str]:
        if not paper_ids:
            return Counter()
        with self._cursor() as cur:
            in_clause, params = build_in_clause("id", paper_ids)
            cur.execute(f"SELECT title,category,journal FROM papers WHERE {in_clause}", params)
            subdomains = self._extract_subdomains_from_rows(cur.fetchall())
        return subdomains

    def _extract_subdomains_from_rows(self, rows) -> Counter[str]:
        """Count topics from paper metadata. LLM daily pipeline handles semantic classification."""
        subdomains: Counter[str] = Counter()
        for row in rows:
            cat = (row.get("category") or "").strip()
            if cat:
                subdomains[cat.lower()] += 1
        return subdomains

    def get_feedback_enhanced_keywords(
        self,
        *,
        days: int = 21,
    ) -> Counter[str]:
        from .daily_recommend_feedback import get_high_value_keywords_from_feedback

        try:
            keywords_set = get_high_value_keywords_from_feedback(self.db_path, days=days, top_n=30)
            return Counter({kw: 2.0 for kw in keywords_set})
        except Exception:
            return Counter()

    def get_user_interest_profile(
        self,
        *,
        reading_days: int = 30,
        saved_days: int = 60,
        feedback_days: int = 21,
    ) -> UserInterestProfile:
        high_duration_papers = self.get_papers_by_reading_time(days=reading_days, top_n=50)
        high_duration_ids = [pid for pid, _ in high_duration_papers]

        freq_papers = self.get_papers_by_reading_frequency(days=reading_days, top_n=30)
        freq_ids = [pid for pid, _ in freq_papers]

        saved_papers = self.get_recently_saved_papers(days=saved_days, top_n=50)
        saved_ids = [pid for pid, _ in saved_papers]

        all_interest_ids = list(set(high_duration_ids + freq_ids + saved_ids))

        reading_keywords = self.extract_keywords_from_high_interest_papers(all_interest_ids)

        feedback_keywords = self.get_feedback_enhanced_keywords(days=feedback_days)

        combined_keywords: Counter[str] = Counter()
        for kw, count in reading_keywords.items():
            combined_keywords[kw] += count * 1.0
        for kw, weight in feedback_keywords.items():
            combined_keywords[kw] += weight

        if saved_ids:
            saved_paper_ids = [pid for pid, _ in saved_papers]
            if saved_paper_ids:
                saved_keywords = self.extract_keywords_from_high_interest_papers(saved_paper_ids)
                for kw, count in saved_keywords.items():

                    if kw in reading_keywords:
                        combined_keywords[kw] += count * 0.5
                    else:
                        combined_keywords[kw] += count * 1.5

        subdomains = self.get_interest_subdomains_from_papers(all_interest_ids)

        preferred_years = self._extract_preferred_years(all_interest_ids)

        recent_topics = self._extract_recent_active_topics(reading_days=14)

        top_keywords = combined_keywords.most_common(40)
        top_subdomains = subdomains.most_common(10)

        return UserInterestProfile(
            top_keywords=top_keywords,
            top_subdomains=top_subdomains,
            high_interest_paper_ids=all_interest_ids[:100],
            recent_active_topics=recent_topics,
            preferred_years=preferred_years,
            preferred_sources=[],
        )

    def _extract_preferred_years(self, paper_ids: list[int]) -> list[int]:
        if not paper_ids:
            return []
        with self._cursor() as cur:
            in_clause, params = build_in_clause("id", paper_ids)
            cur.execute(f"SELECT year,COUNT(*) AS cnt FROM papers WHERE {in_clause} AND year IS NOT NULL GROUP BY year ORDER BY cnt DESC LIMIT 5", params)
            return [int(r["year"]) for r in cur.fetchall() if r["year"]]

    def _extract_recent_active_topics(self, reading_days: int = 14) -> list[str]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT DISTINCT p.title,p.abstract,p.category FROM papers p INNER JOIN paper_reading_sessions prs ON p.id=prs.paper_id WHERE prs.day_key>=date('now',?) LIMIT 30",
                (f"-{reading_days} days",),
            )
            topics = self._extract_subdomains_from_rows(cur.fetchall())
        return [t for t, _ in topics.most_common(5)]

def get_user_interest_profile_for_daily_recommend(db_path: str) -> UserInterestProfile:
    analytics = UserBehaviorAnalytics(db_path)
    return analytics.get_user_interest_profile(
        reading_days=30,
        saved_days=60,
        feedback_days=21,
    )
