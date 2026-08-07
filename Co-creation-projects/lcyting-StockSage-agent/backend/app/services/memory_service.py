"""
记忆系统 — 仪表盘快照的每日缓存与过期管理

记录每天第一次打开后端的时间日期；跨日或自选股数量变化时触发刷新。
每天首次启动时三线程并行获取指数、自选、热点资讯，写入 data/memory/dashboard_state.json。
与 HelloAgents 的 ConversationManager / MemoryManager 无关，本应用对话历史由前端与 SQLite 历史表管理。
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.models.memory_models import MemorySnapshot

logger = logging.getLogger(__name__)

_memory_lock = threading.Lock()


class MemoryService:
    """
    记忆系统核心服务

    职责：
    - 记录每日首次启动日期
    - 日切时清空前一日数据并重新获取
    - 三线程并行获取仪表盘数据（指数、自选、热点资讯）
    - 检测自选股数量变化触发刷新
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self._today: Optional[str] = None
        self._snapshot: Optional[MemorySnapshot] = None
        self._lock = threading.Lock()
        self._watchlist_count: int = 0

        self._storage_dir = storage_dir or (settings.DATA_DIR / "memory")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._storage_dir / "dashboard_state.json"

        self._load_state()

    # ---- 持久化 ----

    def _load_state(self) -> None:
        """从磁盘恢复上次的快照状态"""
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._today = data.get("today")
                self._watchlist_count = data.get("watchlist_count", 0)
                snap = data.get("snapshot")
                if snap:
                    self._snapshot = MemorySnapshot.from_dict(snap)
                logger.info("记忆系统状态已加载: date=%s, watchlist_count=%d", self._today, self._watchlist_count)
        except Exception as exc:
            logger.warning("加载记忆状态失败: %s", exc)

    def _save_state(self) -> None:
        """将当前快照状态持久化到磁盘"""
        try:
            data = {
                "today": self._today,
                "watchlist_count": self._watchlist_count,
                "snapshot": self._snapshot.to_dict() if self._snapshot else None,
            }
            self._state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("保存记忆状态失败: %s", exc)

    # ---- 日期检测 ----

    def _get_today(self) -> str:
        return date.today().isoformat()

    def is_new_day(self) -> bool:
        """检查是否为新的一天"""
        return self._today != self._get_today()

    def should_refresh(self) -> bool:
        """
        判断是否需要刷新数据：
        1. 新的一天
        2. 自选股数量发生变化
        """
        if self.is_new_day():
            logger.info("检测到新的一天，需要刷新仪表盘数据")
            return True

        try:
            from app.services import watchlist_service
            wl = watchlist_service.get_watchlist()
            current_count = wl.get("total", 0) if wl.get("success") else 0
            if current_count != self._watchlist_count and self._watchlist_count > 0:
                logger.info("自选股数量变化: %d -> %d，需要刷新", self._watchlist_count, current_count)
                self._watchlist_count = current_count
                self._save_state()
                return True
        except Exception as exc:
            logger.debug("检查自选股数量时出错: %s", exc)

        return False

    # ---- 数据获取 ----

    def _fetch_indices(self) -> list:
        """获取四大指数数据"""
        from app.services import market_service

        index_names = ("上证指数", "深证成指", "创业板指", "沪深300")
        results = []
        for name in index_names:
            try:
                data = market_service.get_index_quote(name)
                results.append({"name": name, "data": data})
            except Exception as exc:
                logger.debug("记忆系统获取指数失败 %s: %s", name, exc)
        return results

    def _fetch_watchlist(self) -> dict:
        """获取自选股列表（含行情数据）"""
        from app.services import watchlist_service

        try:
            wl = watchlist_service.get_watchlist()
            if wl.get("success"):
                self._watchlist_count = wl.get("total", 0)
            return wl
        except Exception as exc:
            logger.debug("记忆系统获取自选股失败: %s", exc)
            return {"success": False, "stocks": [], "total": 0}

    def _fetch_hot_news(self) -> dict:
        """获取热点资讯"""
        from app.services import news_service

        try:
            return news_service.search_market_news() or {}
        except Exception as exc:
            logger.debug("记忆系统获取热点资讯失败: %s", exc)
            return {}

    def parallel_fetch(self) -> MemorySnapshot:
        """
        三线程并行获取仪表盘数据：指数、自选、热点资讯
        """
        logger.info("记忆系统: 开始三线程并行获取仪表盘数据...")

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_indices = executor.submit(self._fetch_indices)
            future_watchlist = executor.submit(self._fetch_watchlist)
            future_news = executor.submit(self._fetch_hot_news)

            results: dict[str, Any] = {}
            for future in as_completed([future_indices, future_watchlist, future_news]):
                try:
                    value = future.result()
                except Exception as exc:
                    logger.warning("并行获取任务失败: %s", exc)
                    value = None

                if future == future_indices:
                    results["indices"] = value or []
                elif future == future_watchlist:
                    results["watchlist"] = value or {}
                elif future == future_news:
                    results["hot_news"] = value or {}

        today = self._get_today()
        snapshot = MemorySnapshot(
            date_str=today,
            indices=results.get("indices", []),
            watchlist=results.get("watchlist", {}),
            hot_news=results.get("hot_news", {}),
            watchlist_count=self._watchlist_count,
        )

        with self._lock:
            self._today = today
            self._snapshot = snapshot
            self._save_state()

        logger.info("记忆系统: 仪表盘数据获取完成 (date=%s, indices=%d, watchlist=%d)",
                     today, len(snapshot.indices), snapshot.watchlist_count)
        return snapshot

    # ---- 公共接口 ----

    def get_snapshot(self) -> Optional[MemorySnapshot]:
        """获取当前缓存的仪表盘快照"""
        with self._lock:
            return self._snapshot

    def get_indices(self) -> list:
        """获取缓存的指数数据"""
        snap = self.get_snapshot()
        return snap.indices if snap else []

    def get_watchlist(self) -> dict:
        """获取缓存的自选股数据"""
        snap = self.get_snapshot()
        return snap.watchlist if snap else {}

    def get_hot_news(self) -> dict:
        """获取缓存的热点资讯数据"""
        snap = self.get_snapshot()
        return snap.hot_news if snap else {}

    def clear(self) -> None:
        """清空所有记忆数据"""
        with self._lock:
            self._today = None
            self._snapshot = None
            self._watchlist_count = 0
            try:
                if self._state_file.exists():
                    self._state_file.unlink()
            except Exception:
                pass

    def get_stats(self) -> dict:
        """获取记忆系统状态"""
        with self._lock:
            return {
                "today": self._today,
                "has_snapshot": self._snapshot is not None,
                "watchlist_count": self._watchlist_count,
                "indices_count": len(self._snapshot.indices) if self._snapshot else 0,
                "storage_dir": str(self._storage_dir),
            }


_memory_svc: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """获取 MemoryService 全局单例"""
    global _memory_svc
    if _memory_svc is None:
        with _memory_lock:
            if _memory_svc is None:
                _memory_svc = MemoryService()
    return _memory_svc
