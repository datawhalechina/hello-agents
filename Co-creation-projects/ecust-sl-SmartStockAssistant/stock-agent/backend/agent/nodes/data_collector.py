# backend/agent/nodes/data_collector.py
import asyncio
from dataclasses import asdict

from agent.state import StockAnalysisState
from app.config import settings
from data.sources.akshare_adapter import (
    AKShareAdapter,
    HKCompositeAdapter,
    USCompositeAdapter,
)
from data.sources.news_adapter import fetch_stock_news
from data.sources.base import BaseDataSource
from data.sources.stock_list import resolve_symbol  # 新增：名称转代码


def _get_data_source(market: str) -> BaseDataSource:
    if market == "A股":
        if settings.tushare_token:
            from data.sources.tushare_adapter import TushareAdapter
            return TushareAdapter(token=settings.tushare_token)
        return AKShareAdapter()
    if market == "港股":
        return HKCompositeAdapter()
    return USCompositeAdapter()


async def data_collector_node(state: StockAnalysisState) -> StockAnalysisState:

    # ── 关键改动：先把名称/关键词解析成真实股票代码 ──────────────────
    resolved_symbol = resolve_symbol(state["symbol"], state["market"])

    if settings.use_mock_data:
        return {
            **state,
            "symbol": resolved_symbol,
            "realtime_data": {
                "symbol": resolved_symbol,
                "price": 1800.0,
                "volume": 5_000_000,
                "change_pct": 1.5,
                "open": 1780.0,
                "high": 1810.0,
                "low": 1775.0,
                "timestamp": "2026-05-15 10:30:00",
            },
            "kline_data": [
                {"date": "2026-05-13", "open": 1760.0, "high": 1790.0,
                 "low": 1755.0, "close": 1780.0, "volume": 4_800_000},
                {"date": "2026-05-14", "open": 1780.0, "high": 1800.0,
                 "low": 1770.0, "close": 1795.0, "volume": 5_100_000},
                {"date": "2026-05-15", "open": 1795.0, "high": 1815.0,
                 "low": 1788.0, "close": 1800.0, "volume": 5_000_000},
            ],
            "news_data": [
                {"title": "一季度业绩超预期，净利润同比增长15%",
                 "time": "2026-05-15 09:30:00", "source": "东方财富"},
            ],
            "fundamental_data": {
                "symbol": resolved_symbol,
                "pe_ratio": 28.5,
                "pb_ratio": 9.2,
                "market_cap": 22600.0,
                "revenue_growth": 18.3,
                "profit_growth": 15.7,
            },
        }

    # ── 用解析后的代码去拉数据 ────────────────────────────────────────
    source = _get_data_source(state["market"])

    results = await asyncio.gather(
        source.get_realtime_quote(resolved_symbol),
        source.get_kline(resolved_symbol, period="daily", limit=30),
        source.get_fundamental(resolved_symbol),
        fetch_stock_news(resolved_symbol, limit=10),
        return_exceptions=True,
    )

    quote, kline, fundamental, news = results
    errors = []

    realtime_data = None
    if isinstance(quote, Exception):
        errors.append(f"行情数据获取失败: {quote}")
    else:
        realtime_data = asdict(quote)

    kline_data = None
    if isinstance(kline, Exception):
        errors.append(f"K线数据获取失败: {kline}")
    else:
        kline_data = [asdict(bar) for bar in kline]

    fundamental_data = None
    if isinstance(fundamental, Exception):
        errors.append(f"基本面数据获取失败: {fundamental}")
    else:
        fundamental_data = asdict(fundamental)

    news_data = [] if isinstance(news, Exception) else news

    return {
        **state,
        "symbol": resolved_symbol,  # 用解析后的真实代码更新 symbol
        "realtime_data": realtime_data,
        "kline_data": kline_data,
        "fundamental_data": fundamental_data,
        "news_data": news_data,
        "error": "; ".join(errors) if errors else None,
    }