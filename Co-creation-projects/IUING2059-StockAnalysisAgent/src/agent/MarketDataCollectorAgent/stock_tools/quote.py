# stock_tools/quote.py
from datetime import datetime

from ..schemas import StockQuoteSchema
from .technical import get_cached_kline  # 直接复用带缓存的K线


def fetch_quote(stock_code: str, stock_name: str = "") -> StockQuoteSchema:
    # 直接从历史缓存中拿最新一天的数据，0 网络请求，绝对不会报错！
    df = get_cached_kline(stock_code)
    if df.empty:
        raise ValueError(f"无行情数据: {stock_code}")


    latest = df.iloc[-1]

    return StockQuoteSchema(
        stock_code=stock_code,
        stock_name=stock_name,  # 名称可以让大模型去查，或者留空
        time_range=str(latest["日期"]),
        open_price=float(latest["开盘"]),
        close_price=float(latest["收盘"]),
        high_price=float(latest["最高"]),
        low_price=float(latest["最低"]),
        volume=float(latest["成交量"]),
        amount=float(latest.get("成交额", 0)),
        turnover_rate=None,  # 缓存里没有换手率就不填了
    )