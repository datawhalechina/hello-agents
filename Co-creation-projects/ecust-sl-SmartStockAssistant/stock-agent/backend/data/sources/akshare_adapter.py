# backend/data/sources/akshare_adapter.py
import asyncio
import time
from datetime import datetime
from functools import lru_cache

import akshare as ak

from data.sources.base import (
    BaseDataSource,
    FundamentalData,
    KlineBar,
    StockQuote,
)
from data.sources.yfinance_adapter import YFinanceAdapter


# ── Sina 通道共享锁 ───────────────────────────────────────────────────
# akshare 的 stock_us_daily / stock_hk_daily / stock_zh_a_daily 内部都用
# py_mini_racer (V8) 解密 Sina payload。多线程并发实例化 V8 会触发
# partition_address_space 崩溃。所有 Sina daily 调用必须串行化。
_SINA_LOCK = asyncio.Lock()
_SINA_CACHE: dict[tuple[str, str], tuple[float, "object"]] = {}
_SINA_CACHE_TTL_SEC = 300  # 5 分钟，对热门股票列表足够


async def _sina_daily_cached(market: str, symbol: str):
    """统一缓存 + 锁 + asyncio.to_thread 的 Sina daily 调用入口。"""
    import akshare as _ak
    key = (market, symbol)
    cached = _SINA_CACHE.get(key)
    if cached and time.time() - cached[0] < _SINA_CACHE_TTL_SEC:
        return cached[1]
    async with _SINA_LOCK:
        cached = _SINA_CACHE.get(key)
        if cached and time.time() - cached[0] < _SINA_CACHE_TTL_SEC:
            return cached[1]
        # 三个函数签名不同：
        # stock_us_daily(symbol, adjust)
        # stock_hk_daily(symbol, adjust)
        # stock_zh_a_daily(symbol, start_date, end_date, adjust)
        # 统一用 kwargs 安全调用
        if market == "A":
            df = await asyncio.to_thread(_ak.stock_zh_a_daily, symbol=symbol, adjust="")
        elif market == "HK":
            df = await asyncio.to_thread(_ak.stock_hk_daily, symbol=symbol, adjust="")
        else:  # US
            df = await asyncio.to_thread(_ak.stock_us_daily, symbol=symbol, adjust="")
        _SINA_CACHE[key] = (time.time(), df)
        return df


class AKShareAdapter(BaseDataSource):
    """
    A 股数据源，基于 AKShare。
    所有 akshare 调用都是同步的，用 asyncio.to_thread 包装
    避免阻塞 LangGraph 的异步事件循环。
    """

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        """
        获取 A 股实时行情。
        symbol: 6 位股票代码，如 "600519"
        """
        def _fetch():
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if row.empty:
                raise ValueError(f"未找到股票代码：{symbol}")
            return row.iloc[0]

        try:
            row = await asyncio.to_thread(_fetch)
            return StockQuote(
                symbol=symbol,
                price=float(row["最新价"]),
                volume=int(row["成交量"]),
                change_pct=float(row["涨跌幅"]),
                open=float(row["今开"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 实时行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        """
        获取 A 股 K 线数据。
        period: "daily" | "weekly" | "monthly"
        """
        period_map = {
            "daily": "daily",
            "weekly": "weekly",
            "monthly": "monthly",
        }
        ak_period = period_map.get(period, "daily")

        def _fetch():
            return ak.stock_zh_a_hist(
                symbol=symbol,
                period=ak_period,
                adjust="qfq",   # 前复权
            )

        try:
            df = await asyncio.to_thread(_fetch)
            df = df.tail(limit)
            return [
                KlineBar(
                    date=str(row["日期"]),
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=int(row["成交量"]),
                )
                for _, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"AKShare K线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        """获取 A 股基本面数据"""

        def _fetch():
            return ak.stock_zh_a_spot_em()

        try:
            df = await asyncio.to_thread(_fetch)
            row = df[df["代码"] == symbol]
            if row.empty:
                raise ValueError(f"未找到股票代码：{symbol}")
            r = row.iloc[0]

            return FundamentalData(
                symbol=symbol,
                pe_ratio=float(r["市盈率-动态"]) if r["市盈率-动态"] else 0.0,
                pb_ratio=float(r["市净率"]) if r["市净率"] else 0.0,
                market_cap=float(r["总市值"]) / 1e8,  # 转换为亿
                revenue_growth=0.0,   # AKShare 实时接口无此字段，Phase 2 补充财报接口
                profit_growth=0.0,
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 基本面获取失败 [{symbol}]: {e}") from e


class AKShareUSAdapter(BaseDataSource):
    """
    美股数据源，基于 AKShare 的 Sina 通道（stock_us_daily）。
    Sina 通道在国内访问稳定，能覆盖 quote + K 线；
    基本面数据 Sina 不提供，由上层 USCompositeAdapter 兜底到 yfinance。
    """

    @staticmethod
    def _normalize(symbol: str) -> str:
        return symbol.strip().upper()

    async def _daily(self, symbol: str):
        return await _sina_daily_cached("US", self._normalize(symbol))

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        try:
            df = await self._daily(symbol)
            if df is None or df.empty:
                raise ValueError(f"未获取到美股行情：{symbol}")
            last = df.iloc[-1]
            prev_close = float(df.iloc[-2]["close"]) if len(df) >= 2 else float(last["close"])
            change_pct = (
                round((float(last["close"]) - prev_close) / prev_close * 100, 2)
                if prev_close else 0.0
            )
            return StockQuote(
                symbol=self._normalize(symbol),
                price=float(last["close"]),
                volume=int(last["volume"]),
                change_pct=change_pct,
                open=float(last["open"]),
                high=float(last["high"]),
                low=float(last["low"]),
                timestamp=str(last["date"]),
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 美股行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        try:
            df = await self._daily(symbol)
            if df is None or df.empty:
                raise ValueError(f"未获取到美股 K 线：{symbol}")
            df = df.tail(limit)
            return [
                KlineBar(
                    date=str(row["date"])[:10],
                    open=round(float(row["open"]), 4),
                    high=round(float(row["high"]), 4),
                    low=round(float(row["low"]), 4),
                    close=round(float(row["close"]), 4),
                    volume=int(row["volume"]),
                )
                for _, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"AKShare 美股 K 线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        # Sina 通道不提供基本面字段；返回零值占位，避免上层为此重试外部源。
        return FundamentalData(
            symbol=self._normalize(symbol),
            pe_ratio=0.0,
            pb_ratio=0.0,
            market_cap=0.0,
            revenue_growth=0.0,
            profit_growth=0.0,
        )


class USCompositeAdapter(BaseDataSource):
    """
    美股组合数据源：akshare（Sina）优先，yfinance 兜底。

    每个方法独立 fallback，单方法的失败只影响自己。
    在 yfinance 被 Yahoo 限流时，quote/kline 仍能从 akshare 拿到真实数据。
    """

    def __init__(self) -> None:
        self._primary = AKShareUSAdapter()
        self._fallback = YFinanceAdapter()

    async def _try(self, name: str, *args, **kwargs):
        primary_err: Exception | None = None
        try:
            return await getattr(self._primary, name)(*args, **kwargs)
        except Exception as e:
            primary_err = e
        try:
            return await getattr(self._fallback, name)(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(
                f"美股数据获取失败 [primary={primary_err}; fallback={e}]"
            ) from e

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        return await self._try("get_realtime_quote", symbol)

    async def get_kline(
        self, symbol: str, period: str = "daily", limit: int = 30
    ) -> list[KlineBar]:
        return await self._try("get_kline", symbol, period=period, limit=limit)

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        return await self._try("get_fundamental", symbol)


class AKShareHKAdapter(BaseDataSource):
    """
    港股数据源，基于 AKShare。
    symbol: 5 位港股代码，如 "00700"
    """

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        def _fetch():
            df = ak.stock_hk_spot_em()
            row = df[df["代码"] == symbol]
            if row.empty:
                raise ValueError(f"未找到港股代码：{symbol}")
            return row.iloc[0]

        try:
            row = await asyncio.to_thread(_fetch)
            return StockQuote(
                symbol=symbol,
                price=float(row["最新价"]),
                volume=int(row["成交量"]),
                change_pct=float(row["涨跌幅"]),
                open=float(row["今开"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 港股实时行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        ak_period = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}.get(period, "daily")

        def _fetch():
            return ak.stock_hk_hist(symbol=symbol, period=ak_period, adjust="qfq")

        try:
            df = await asyncio.to_thread(_fetch)
            df = df.tail(limit)
            return [
                KlineBar(
                    date=str(row["日期"]),
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=int(row["成交量"]),
                )
                for _, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"AKShare 港股 K线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        def _fetch():
            return ak.stock_hk_spot_em()

        try:
            df = await asyncio.to_thread(_fetch)
            row = df[df["代码"] == symbol]
            if row.empty:
                raise ValueError(f"未找到港股代码：{symbol}")
            r = row.iloc[0]
            return FundamentalData(
                symbol=symbol,
                pe_ratio=0.0,
                pb_ratio=0.0,
                market_cap=float(r["总市值"]) / 1e8 if "总市值" in r and r["总市值"] else 0.0,
                revenue_growth=0.0,
                profit_growth=0.0,
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 港股基本面获取失败 [{symbol}]: {e}") from e


class AKShareHKSinaAdapter(BaseDataSource):
    """
    港股数据源，基于 AKShare 的 Sina 通道（stock_hk_daily）。
    eastmoney 通道 (AKShareHKAdapter) 在国内代理环境下经常 RemoteDisconnected，
    Sina 通道稳定。共享 _SINA_LOCK 串行化 mini_racer。
    """

    @staticmethod
    def _normalize(symbol: str) -> str:
        s = symbol.strip()
        return s.zfill(5) if s.isdigit() else s

    async def _daily(self, symbol: str):
        return await _sina_daily_cached("HK", self._normalize(symbol))

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        try:
            df = await self._daily(symbol)
            if df is None or df.empty:
                raise ValueError(f"未获取到港股行情：{symbol}")
            last = df.iloc[-1]
            prev_close = float(df.iloc[-2]["close"]) if len(df) >= 2 else float(last["close"])
            change_pct = (
                round((float(last["close"]) - prev_close) / prev_close * 100, 2)
                if prev_close else 0.0
            )
            return StockQuote(
                symbol=self._normalize(symbol),
                price=float(last["close"]),
                volume=int(last["volume"]),
                change_pct=change_pct,
                open=float(last["open"]),
                high=float(last["high"]),
                low=float(last["low"]),
                timestamp=str(last["date"]),
            )
        except Exception as e:
            raise RuntimeError(f"AKShare 港股 Sina 行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        try:
            df = await self._daily(symbol)
            if df is None or df.empty:
                raise ValueError(f"未获取到港股 K 线：{symbol}")
            df = df.tail(limit)
            return [
                KlineBar(
                    date=str(row["date"])[:10],
                    open=round(float(row["open"]), 4),
                    high=round(float(row["high"]), 4),
                    low=round(float(row["low"]), 4),
                    close=round(float(row["close"]), 4),
                    volume=int(row["volume"]),
                )
                for _, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"AKShare 港股 Sina K 线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        return FundamentalData(
            symbol=self._normalize(symbol),
            pe_ratio=0.0,
            pb_ratio=0.0,
            market_cap=0.0,
            revenue_growth=0.0,
            profit_growth=0.0,
        )


class HKCompositeAdapter(BaseDataSource):
    """港股组合数据源：Sina 优先，eastmoney 兜底（万一 Sina 暂时不可用）。"""

    def __init__(self) -> None:
        self._primary = AKShareHKSinaAdapter()
        self._fallback = AKShareHKAdapter()

    async def _try(self, name: str, *args, **kwargs):
        primary_err: Exception | None = None
        try:
            return await getattr(self._primary, name)(*args, **kwargs)
        except Exception as e:
            primary_err = e
        try:
            return await getattr(self._fallback, name)(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(
                f"港股数据获取失败 [primary={primary_err}; fallback={e}]"
            ) from e

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        return await self._try("get_realtime_quote", symbol)

    async def get_kline(
        self, symbol: str, period: str = "daily", limit: int = 30
    ) -> list[KlineBar]:
        return await self._try("get_kline", symbol, period=period, limit=limit)

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        return await self._try("get_fundamental", symbol)