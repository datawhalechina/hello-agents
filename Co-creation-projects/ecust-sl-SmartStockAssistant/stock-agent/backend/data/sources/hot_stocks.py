# backend/data/sources/hot_stocks.py
"""
首页热门股票服务：按当日涨幅取 A股 / 港股 / 美股 各前 8。
候选池为各市场 30 只大盘股，全部走 Sina daily，结果整体缓存 5 分钟。
"""
import asyncio
import time
from typing import Optional

from data.sources.akshare_adapter import _sina_daily_cached


# 每只股票：(symbol_for_search, sina_symbol, display_name)
# symbol_for_search 是前端搜索/分析使用的代码（A股 6 位、港股 5 位、美股原代码）
# sina_symbol 是传给 _sina_daily_cached 的 Sina 通道符号（A股需 sh/sz 前缀）

CANDIDATE_POOLS: dict[str, list[tuple[str, str, str]]] = {
    "A股": [
        ("600519", "sh600519", "贵州茅台"),
        ("000858", "sz000858", "五粮液"),
        ("300750", "sz300750", "宁德时代"),
        ("601318", "sh601318", "中国平安"),
        ("000333", "sz000333", "美的集团"),
        ("600036", "sh600036", "招商银行"),
        ("002594", "sz002594", "比亚迪"),
        ("600276", "sh600276", "恒瑞医药"),
        ("601398", "sh601398", "工商银行"),
        ("601857", "sh601857", "中国石油"),
        ("600028", "sh600028", "中国石化"),
        ("601988", "sh601988", "中国银行"),
        ("601628", "sh601628", "中国人寿"),
        ("600030", "sh600030", "中信证券"),
        ("601166", "sh601166", "兴业银行"),
        ("000001", "sz000001", "平安银行"),
        ("000002", "sz000002", "万科A"),
        ("600887", "sh600887", "伊利股份"),
        ("600690", "sh600690", "海尔智家"),
        ("002415", "sz002415", "海康威视"),
        ("000651", "sz000651", "格力电器"),
        ("002475", "sz002475", "立讯精密"),
        ("603259", "sh603259", "药明康德"),
        ("603288", "sh603288", "海天味业"),
        ("601012", "sh601012", "隆基绿能"),
        ("000725", "sz000725", "京东方A"),
        ("002230", "sz002230", "科大讯飞"),
        ("688981", "sh688981", "中芯国际"),
        ("688041", "sh688041", "海光信息"),
        ("300059", "sz300059", "东方财富"),
    ],
    "港股": [
        ("00700", "00700", "腾讯控股"),
        ("09988", "09988", "阿里巴巴-W"),
        ("03690", "03690", "美团-W"),
        ("00388", "00388", "香港交易所"),
        ("09618", "09618", "京东集团-SW"),
        ("02318", "02318", "中国平安"),
        ("00005", "00005", "汇丰控股"),
        ("01810", "01810", "小米集团-W"),
        ("00939", "00939", "建设银行"),
        ("01398", "01398", "工商银行"),
        ("00941", "00941", "中国移动"),
        ("00857", "00857", "中国石油股份"),
        ("00386", "00386", "中国石化"),
        ("03988", "03988", "中国银行"),
        ("02628", "02628", "中国人寿"),
        ("02382", "02382", "舜宇光学科技"),
        ("06618", "06618", "京东健康"),
        ("09999", "09999", "网易-S"),
        ("09888", "09888", "百度集团-SW"),
        ("03968", "03968", "招商银行"),
        ("02020", "02020", "安踏体育"),
        ("02331", "02331", "李宁"),
        ("01211", "01211", "比亚迪股份"),
        ("00992", "00992", "联想集团"),
        ("00688", "00688", "中国海外发展"),
        ("01024", "01024", "快手-W"),
        ("02899", "02899", "紫金矿业"),
        ("01378", "01378", "中国宏桥"),
        ("01088", "01088", "中国神华"),
        ("00386", "00386", "中国石化"),
    ],
    "美股": [
        ("AAPL",  "AAPL",  "苹果"),
        ("MSFT",  "MSFT",  "微软"),
        ("NVDA",  "NVDA",  "英伟达"),
        ("TSLA",  "TSLA",  "特斯拉"),
        ("AMZN",  "AMZN",  "亚马逊"),
        ("GOOGL", "GOOGL", "谷歌-A"),
        ("META",  "META",  "Meta"),
        ("PDD",   "PDD",   "拼多多"),
        ("BABA",  "BABA",  "阿里巴巴"),
        ("JPM",   "JPM",   "摩根大通"),
        ("V",     "V",     "维萨"),
        ("WMT",   "WMT",   "沃尔玛"),
        ("JNJ",   "JNJ",   "强生"),
        ("PG",    "PG",    "宝洁"),
        ("XOM",   "XOM",   "埃克森美孚"),
        ("HD",    "HD",    "家得宝"),
        ("MA",    "MA",    "万事达"),
        ("LLY",   "LLY",   "礼来"),
        ("ABBV",  "ABBV",  "艾伯维"),
        ("BAC",   "BAC",   "美国银行"),
        ("KO",    "KO",    "可口可乐"),
        ("AVGO",  "AVGO",  "博通"),
        ("TSM",   "TSM",   "台积电"),
        ("PEP",   "PEP",   "百事"),
        ("COST",  "COST",  "好市多"),
        ("CSCO",  "CSCO",  "思科"),
        ("ADBE",  "ADBE",  "奥多比"),
        ("NFLX",  "NFLX",  "网飞"),
        ("ORCL",  "ORCL",  "甲骨文"),
        ("AMD",   "AMD",   "AMD"),
    ],
}

# 市场 → _sina_daily_cached 的市场代码
_MARKET_KEY = {"A股": "A", "港股": "HK", "美股": "US"}

TOP_N = 8

_RESULT_CACHE: dict[str, tuple[float, dict]] = {}
_RESULT_CACHE_TTL_SEC = 300  # 整体结果 5 分钟


async def _fetch_one(market: str, search_symbol: str, sina_symbol: str, name: str) -> Optional[dict]:
    try:
        df = await _sina_daily_cached(_MARKET_KEY[market], sina_symbol)
        if df is None or df.empty or len(df) < 2:
            return None
        tail = df.tail(8)
        last = tail.iloc[-1]
        prev = tail.iloc[-2]
        close = float(last["close"])
        prev_close = float(prev["close"])
        change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0.0
        sparkline = [round(float(c), 4) for c in tail["close"].tolist()]
        return {
            "symbol": search_symbol,
            "name": name,
            "market": market,
            "price": round(close, 4),
            "change_pct": round(change_pct, 2),
            "sparkline": sparkline,
            "date": str(last["date"])[:10],
        }
    except Exception:
        return None  # 失败直接丢弃，不进入排序


async def get_hot_stocks(market: Optional[str] = None) -> dict:
    """
    返回 { "A股": [Top8 by change_pct desc], "港股": [...], "美股": [...] }
    market 指定时只返回该市场。
    """
    cache_key = market or "all"
    cached = _RESULT_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _RESULT_CACHE_TTL_SEC:
        return cached[1]

    markets = [market] if market in CANDIDATE_POOLS else list(CANDIDATE_POOLS.keys())
    tasks = []
    flat_index: list[tuple[str, int]] = []
    for m in markets:
        for i, (search_sym, sina_sym, name) in enumerate(CANDIDATE_POOLS[m]):
            tasks.append(_fetch_one(m, search_sym, sina_sym, name))
            flat_index.append((m, i))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    by_market: dict[str, list[dict]] = {m: [] for m in markets}
    for (m, _i), r in zip(flat_index, results):
        if isinstance(r, dict):
            by_market[m].append(r)

    # 按当日涨幅降序，取 Top N
    top_by_market: dict[str, list[dict]] = {}
    for m, items in by_market.items():
        items.sort(key=lambda x: (x.get("change_pct") if x.get("change_pct") is not None else -1e9), reverse=True)
        top_by_market[m] = items[:TOP_N]

    _RESULT_CACHE[cache_key] = (time.time(), top_by_market)
    return top_by_market


async def prewarm() -> None:
    """启动时预热缓存，使首屏访问立即返回。"""
    try:
        await get_hot_stocks()
    except Exception as e:
        print(f"[WARN] 热门股票预热失败: {e}")
