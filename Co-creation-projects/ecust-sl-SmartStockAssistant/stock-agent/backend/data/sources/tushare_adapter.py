# backend/data/sources/tushare_adapter.py
import asyncio
import json
import time
import requests
from datetime import datetime, timedelta

import tushare as ts

from data.sources.base import BaseDataSource, FundamentalData, KlineBar, StockQuote


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn/",
}

# 简单内存缓存，避免短时间重复请求
_cache: dict = {}
_CACHE_TTL = 60  # 秒


def _get_cache(key: str):
    if key in _cache:
        val, ts_time = _cache[key]
        if time.time() - ts_time < _CACHE_TTL:
            return val
    return None


def _set_cache(key: str, val):
    _cache[key] = (val, time.time())


class TushareAdapter(BaseDataSource):

    def __init__(self, token: str):
        ts.set_token(token)
        self.pro = ts.pro_api()

    def _sina_symbol(self, symbol: str) -> str:
        """
        转换为新浪格式：
        6xxxxx → sh6xxxxx（沪市）
        0xxxxx / 3xxxxx → sz0xxxxx（深市/创业板）
        688xxx → sh688xxx（科创板）
        """
        if symbol.startswith("6") or symbol.startswith("688"):
            return f"sh{symbol}"
        return f"sz{symbol}"

    async def get_realtime_quote(self, symbol: str) -> StockQuote:
        cache_key = f"quote_{symbol}"
        cached = _get_cache(cache_key)
        if cached:
            return cached

        def _fetch():
            df = ts.get_realtime_quotes(symbol)
            if df is None or df.empty:
                raise ValueError(f"未找到股票：{symbol}")
            return df.iloc[0]

        try:
            row = await asyncio.wait_for(
                asyncio.to_thread(_fetch), timeout=15
            )
            price = float(row["price"] or row["pre_close"])
            pre_close = float(row["pre_close"])
            change_pct = round(
                (price - pre_close) / pre_close * 100, 2
            ) if pre_close else 0.0

            result = StockQuote(
                symbol=symbol,
                price=price,
                volume=int(float(row.get("volume") or 0)),
                change_pct=change_pct,
                open=float(row.get("open") or price),
                high=float(row.get("high") or price),
                low=float(row.get("low") or price),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            _set_cache(cache_key, result)
            return result
        except asyncio.TimeoutError:
            raise RuntimeError(f"实时行情请求超时 [{symbol}]")
        except Exception as e:
            raise RuntimeError(f"Tushare 实时行情获取失败 [{symbol}]: {e}") from e

    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        limit: int = 30,
    ) -> list[KlineBar]:
        cache_key = f"kline_{symbol}_{period}_{limit}"
        cached = _get_cache(cache_key)
        if cached:
            return cached

        sina_sym = self._sina_symbol(symbol)
        scale_map = {"daily": "240", "weekly": "1200", "monthly": "7200"}
        scale = scale_map.get(period, "240")

        def _fetch():
            url = (
                f"https://quotes.sina.cn/cn/api/jsonp_v2.php/"
                f"var%20_{sina_sym}=/CN_MarketDataService.getKLineData"
                f"?symbol={sina_sym}&scale={scale}&ma=no&datalen={limit}"
            )
            resp = requests.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            text = resp.text
            if "([" not in text or "])" not in text:
                raise ValueError(f"K线数据格式异常：{text[:100]}")
            start = text.index("([") + 2
            end = text.rindex("])")
            return json.loads("[" + text[start:end] + "]")

        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(_fetch), timeout=15
            )
            if not data:
                raise ValueError(f"无 K 线数据：{symbol}")
            result = [
                KlineBar(
                    date=item["day"],
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=int(float(item["volume"])),
                )
                for item in data
            ]
            _set_cache(cache_key, result)
            return result
        except asyncio.TimeoutError:
            raise RuntimeError(f"K线请求超时 [{symbol}]")
        except Exception as e:
            raise RuntimeError(f"新浪 K线获取失败 [{symbol}]: {e}") from e

    async def get_fundamental(self, symbol: str) -> FundamentalData:
        cache_key = f"fundamental_{symbol}"
        cached = _get_cache(cache_key)
        if cached:
            return cached

        sina_sym = self._sina_symbol(symbol)

        def _fetch():
            url = f"https://qt.gtimg.cn/q={sina_sym}"
            resp = requests.get(url, headers={
                **HEADERS, "Referer": "https://gu.qq.com/",
            }, timeout=12)
            resp.encoding = "gbk"
            text = resp.text
            start = text.index('"') + 1
            end = text.rindex('"')
            return text[start:end].split("~")

        try:
            parts = await asyncio.wait_for(
                asyncio.to_thread(_fetch), timeout=15
            )
            pe = float(parts[39]) if len(parts) > 39 and parts[39] else 0.0
            pb = float(parts[46]) if len(parts) > 46 and parts[46] else 0.0
            market_cap = float(parts[45]) if len(parts) > 45 and parts[45] else 0.0

            result = FundamentalData(
                symbol=symbol,
                pe_ratio=pe,
                pb_ratio=pb,
                market_cap=market_cap,
                revenue_growth=0.0,
                profit_growth=0.0,
            )
            _set_cache(cache_key, result)
            return result
        except asyncio.TimeoutError:
            raise RuntimeError(f"基本面请求超时 [{symbol}]")
        except Exception as e:
            raise RuntimeError(f"腾讯财经基本面获取失败 [{symbol}]: {e}") from e