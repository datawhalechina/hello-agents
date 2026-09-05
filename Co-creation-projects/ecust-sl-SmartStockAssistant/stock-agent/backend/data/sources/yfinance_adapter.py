# backend/data/sources/yfinance_adapter.py
import asyncio
from datetime import datetime

import yfinance as yf

from data.sources.base import (
    BaseDataSource,
    FundamentalData,
    KlineBar,
    StockQuote,
)


class YFinanceAdapter(BaseDataSource):
    """
    美股数据源，基于 yfinance。
    同样用 asyncio.to_thread 包装同步调用。
    """

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return info

        try:
            info = await asyncio.to_thread(_fetch)
            return StockQuote(
                symbol=symbol,
                price=float(info.last_price or 0),
                volume=int(info.last_volume or 0),
                change_pct=round(
                    (info.last_price - info.previous_close)
                    / info.previous_close * 100, 2
                ) if info.previous_close else 0.0,
                open=float(info.open or 0),
                high=float(info.day_high or 0),
                low=float(info.day_low or 0),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            raise RuntimeError(f"yfinance 实时行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        period_map = {
            "daily": ("1d", f"{limit}d"),
            "weekly": ("1wk", f"{limit * 7}d"),
            "monthly": ("1mo", f"{limit * 30}d"),
            "60min": ("60m", f"{min(limit, 60)}d"),  # yfinance 分钟数据最多60天
            "30min": ("30m", f"{min(limit, 60)}d"),
        }
        interval, yf_period = period_map.get(period, ("1d", f"{limit}d"))

        def _fetch():
            ticker = yf.Ticker(symbol)
            return ticker.history(period=yf_period, interval=interval)

        try:
            df = await asyncio.to_thread(_fetch)
            if df.empty:
                raise ValueError(f"未获取到 K 线数据：{symbol}")
            df = df.tail(limit)
            return [
                KlineBar(
                    date=str(idx.date()),
                    open=round(float(row["Open"]), 4),
                    high=round(float(row["High"]), 4),
                    low=round(float(row["Low"]), 4),
                    close=round(float(row["Close"]), 4),
                    volume=int(row["Volume"]),
                )
                for idx, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"yfinance K线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        def _fetch():
            ticker = yf.Ticker(symbol)
            return ticker.info

        try:
            info = await asyncio.to_thread(_fetch)
            return FundamentalData(
                symbol=symbol,
                pe_ratio=float(info.get("trailingPE") or 0),
                pb_ratio=float(info.get("priceToBook") or 0),
                market_cap=float(info.get("marketCap") or 0) / 1e8,  # 转换为亿
                revenue_growth=round(
                    float(info.get("revenueGrowth") or 0) * 100, 2
                ),
                profit_growth=round(
                    float(info.get("earningsGrowth") or 0) * 100, 2
                ),
            )
        except Exception as e:
            raise RuntimeError(f"yfinance 基本面获取失败 [{symbol}]: {e}") from e