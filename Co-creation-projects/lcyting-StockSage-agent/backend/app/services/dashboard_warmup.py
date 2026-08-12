"""
仪表盘数据预热

启动时通过 MemoryService 三线程并行获取指数、自选、热点资讯，
将结果写入 MXTimedCache，首屏请求即可命中缓存。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DASHBOARD_INDEX_NAMES: tuple[str, ...] = (
    "上证指数",
    "深证成指",
    "创业板指",
    "沪深300",
)


def warm_dashboard_cache() -> None:
    """通过记忆系统三线程并行预取仪表盘妙想缓存"""
    try:
        from app.services.memory_service import get_memory_service

        mem = get_memory_service()

        if mem.should_refresh():
            logger.info("仪表盘预热: 触发三线程并行获取...")
            mem.parallel_fetch()
            logger.info("仪表盘预热: 完成 (indices=%d, watchlist=%d)",
                         len(mem.get_indices()), mem.get_stats().get("watchlist_count", 0))
        else:
            logger.info("仪表盘预热: 今日已缓存，跳过刷新")
    except Exception as exc:
        logger.warning("仪表盘预热失败（可忽略）: %s", exc)
