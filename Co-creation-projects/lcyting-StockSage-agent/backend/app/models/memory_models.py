"""
记忆系统数据模型 — 单日仪表盘快照（指数 / 自选 / 热点资讯）
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional


class MemorySnapshot:
    """单日仪表盘数据快照"""

    def __init__(
        self,
        date_str: str = "",
        indices: Optional[list] = None,
        watchlist: Optional[dict] = None,
        hot_news: Optional[dict] = None,
        watchlist_count: int = 0,
    ):
        self.date_str = date_str or date.today().isoformat()
        self.indices = indices or []
        self.watchlist = watchlist or {}
        self.hot_news = hot_news or {}
        self.watchlist_count = watchlist_count
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "date_str": self.date_str,
            "indices": self.indices,
            "watchlist": self.watchlist,
            "hot_news": self.hot_news,
            "watchlist_count": self.watchlist_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MemorySnapshot:
        return cls(
            date_str=d.get("date_str", ""),
            indices=d.get("indices", []),
            watchlist=d.get("watchlist", {}),
            hot_news=d.get("hot_news", {}),
            watchlist_count=d.get("watchlist_count", 0),
        )
