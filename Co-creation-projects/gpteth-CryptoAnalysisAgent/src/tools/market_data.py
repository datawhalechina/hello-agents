"""
共享市场数据访问层

所有工具的 HTTP 请求统一经过这里，提供:
- 连接复用: 共享 requests.Session (避免每次请求重建 TCP/TLS 连接)
- TTL 缓存: 同一轮分析中多个工具请求相同数据时直接命中缓存
  (例如技术分析的 3 个工具都需要同一份 K 线; 链上/情绪工具都需要 24h ticker)
- 自动重试: 网络抖动时按指数退避重试

缓存默认 TTL 为 60 秒——足够覆盖一轮多 Agent 分析，
又不会让行情数据明显过期。可通过 clear_cache() 手动失效。
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry

BINANCE_SPOT_API = "https://api.binance.com"
BINANCE_FUTURES_API = "https://fapi.binance.com"
ALTERNATIVE_ME_API = "https://api.alternative.me"

DEFAULT_TTL = 60.0  # 秒
DEFAULT_TIMEOUT = 10  # 秒

_session: Optional[requests.Session] = None
_session_lock = threading.Lock()

_cache: Dict[Tuple, Tuple[float, Any]] = {}
_cache_lock = threading.Lock()

# 调用统计 (供评估模块考核工具调用效率: 请求数越少、命中率越高越好)
_stats = {"http_requests": 0, "cache_hits": 0}


def get_stats() -> Dict[str, int]:
    """返回累计的 HTTP 请求数和缓存命中数"""
    with _cache_lock:
        return dict(_stats)


def reset_stats() -> None:
    """重置统计计数 (开始一轮新的考核前调用)"""
    with _cache_lock:
        _stats["http_requests"] = 0
        _stats["cache_hits"] = 0


def get_session() -> requests.Session:
    """获取共享 Session (带连接池和重试策略)"""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                session = requests.Session()
                retry = Retry(
                    total=2,
                    backoff_factor=0.5,
                    status_forcelist=(429, 500, 502, 503, 504),
                    allowed_methods=("GET",),
                )
                adapter = HTTPAdapter(max_retries=retry, pool_maxsize=10)
                session.mount("https://", adapter)
                session.mount("http://", adapter)
                _session = session
    return _session


def clear_cache() -> None:
    """清空缓存 (需要强制刷新最新行情时调用)"""
    with _cache_lock:
        _cache.clear()


def cached_get(url: str, params: Optional[dict] = None,
               ttl: float = DEFAULT_TTL, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """带 TTL 缓存的 GET 请求，返回解析后的 JSON"""
    key = (url, tuple(sorted((params or {}).items())))
    now = time.monotonic()

    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None and now - hit[0] < ttl:
            _stats["cache_hits"] += 1
            return hit[1]

    response = get_session().get(url, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    with _cache_lock:
        _stats["http_requests"] += 1
        _cache[key] = (now, data)
        # 简单的容量保护，防止长会话下缓存无限增长
        if len(_cache) > 256:
            cutoff = sorted(_cache.values(), key=lambda v: v[0])[len(_cache) // 2][0]
            for k in [k for k, v in _cache.items() if v[0] <= cutoff]:
                _cache.pop(k, None)

    return data


# ---------------------------------------------------------------------------
# 业务级数据接口
# ---------------------------------------------------------------------------

def get_klines(symbol: str, interval: str = "4h", limit: int = 100,
               start_time_ms: Optional[int] = None) -> List[list]:
    """获取 K 线原始数据 (Binance 格式的二维数组)

    start_time_ms: 可选的起始时间戳 (毫秒)，用于查询历史某时刻的价格
    """
    params: Dict[str, Any] = {
        "symbol": symbol.upper(), "interval": interval, "limit": limit,
    }
    if start_time_ms is not None:
        params["startTime"] = int(start_time_ms)
    return cached_get(f"{BINANCE_SPOT_API}/api/v3/klines", params=params)


def get_price_at(symbol: str, timestamp: float) -> Optional[float]:
    """查询某个历史时刻的成交价 (该时刻所在 1h K 线的开盘价)

    timestamp: Unix 秒级时间戳。返回 None 表示该时刻尚无数据。
    """
    pair = symbol.upper()
    if not pair.endswith("USDT"):
        pair += "USDT"
    klines = get_klines(pair, "1h", 1, start_time_ms=int(timestamp * 1000))
    if not klines:
        return None
    return float(klines[0][1])


def get_ticker_24h(symbol: str) -> Dict[str, Any]:
    """获取 24 小时行情统计"""
    pair = symbol.upper()
    if not pair.endswith("USDT"):
        pair += "USDT"
    return cached_get(
        f"{BINANCE_SPOT_API}/api/v3/ticker/24hr",
        params={"symbol": pair},
        timeout=5,
    )


def get_funding_rates(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """获取永续合约历史资金费率"""
    pair = symbol.upper()
    if not pair.endswith("USDT"):
        pair += "USDT"
    return cached_get(
        f"{BINANCE_FUTURES_API}/fapi/v1/fundingRate",
        params={"symbol": pair, "limit": limit},
    )


def get_fear_greed(limit: int = 7) -> Dict[str, Any]:
    """获取恐惧贪婪指数 (Alternative.me)，该指数每日更新，缓存可更久"""
    return cached_get(
        f"{ALTERNATIVE_ME_API}/fng/",
        params={"limit": min(limit, 30), "format": "json"},
        ttl=300.0,
    )
