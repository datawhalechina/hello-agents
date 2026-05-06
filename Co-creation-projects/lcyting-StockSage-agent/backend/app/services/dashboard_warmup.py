"""
仪表盘数据预热

用户首页通常为仪表盘，会在短时间内并发请求指数、自选、热点资讯。
进程启动后在后台调用与这些接口相同的 service 层逻辑，将结果写入 MXTimedCache，
首屏请求即可命中缓存，显著缩短等待（仍受妙想 RTT 与 TTL 约束）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 须与 frontend/src/views/Dashboard.vue 中 INDEX_LIST 保持一致
DASHBOARD_INDEX_NAMES: tuple[str, ...] = (
    "上证指数",
    "深证成指",
    "创业板指",
    "沪深300",
)


def warm_dashboard_cache() -> None:
    """同步填充仪表盘相关妙想缓存；任一步失败不影响其它步骤。"""
    try:
        from app.services import market_service, news_service, watchlist_service
    except Exception as exc:
        logger.warning("仪表盘预热：导入失败 %s", exc)
        return

    # 1) 四大指数卡片（与 GET /market/index?name= 一致）
    for name in DASHBOARD_INDEX_NAMES:
        try:
            market_service.get_index_quote(name)
        except Exception as exc:
            logger.debug("仪表盘预热指数失败 %s: %s", name, exc)

    # 2) 自选列表 + 各股行情（与 GET /watchlist + /market/quote 一致）
    try:
        wl = watchlist_service.get_watchlist()
        if wl.get("success") and wl.get("stocks"):
            for row in wl["stocks"]:
                code = str(row.get("code") or "").strip()
                if len(code) >= 4:
                    try:
                        market_service.get_stock_quote(code)
                    except Exception as exc:
                        logger.debug("仪表盘预热个股行情失败 %s: %s", code, exc)
    except Exception as exc:
        logger.debug("仪表盘预热自选失败: %s", exc)

    # 3) 热点快讯（与 GET /news/hot -> search_market_news 一致）
    try:
        news_service.search_market_news()
    except Exception as exc:
        logger.debug("仪表盘预热热点资讯失败: %s", exc)
