# stock_tools/_common.py
import functools
import signal
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime

import akshare as ak
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================= 方案一：全局重试适配器与伪装 =================
def _create_retry_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple = (500, 502, 503, 504),
) -> requests.Session:
    """创建一个带指数退避重试的 requests Session。"""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,  # 等待 1s, 2s, 4s...
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # 模拟浏览器 UA，降低被拦截概率
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

# 尝试将重试 Session 注入到 akshare 模块（针对部分直接使用 ak.requests 的接口）
try:
    _retry_session = _create_retry_session()
    if hasattr(ak, "requests"):
        ak.requests = _retry_session
except Exception:
    pass
# ==============================================================


def _latest_non_null(series: pd.Series):
    s = series.dropna()
    return s.iloc[0] if len(s) > 0 else None


def _safe_float(row, *names):
    for n in names:
        if n in row.index and pd.notna(row[n]):
            try:
                return float(row[n])
            except (TypeError, ValueError):
                continue
    return None


# ================= 方案二：数据源回退机制 =================
@functools.lru_cache(maxsize=1)
def get_spot_snapshot() -> pd.DataFrame:
    """全市场快照，带缓存。优先使用新浪源，失败或空时回退到东财源。"""
    # 1. 优先尝试新浪接口
    try:
        df = ak.stock_zh_a_spot()
        if not df.empty and "代码" in df.columns:
            # 新浪接口的数据量可能较大，返回前可做简单清洗
            return df
    except Exception as e:
        print(f"[Warning] 新浪行情源获取失败，尝试回退到东方财富源。原因: {e}")

    # 2. 回退到东方财富接口
    try:
        df_em = ak.stock_zh_a_spot_em()
        return df_em
    except Exception as e:
        print(f"[Error] 东方财富行情源也获取失败: {e}")
        raise e
# =========================================================


def clear_spot_cache():
    get_spot_snapshot.cache_clear()


@contextmanager
def timeout(seconds: int):
    """跨平台超时控制。
    Windows 系统或子线程环境下会优雅降级（跳过超时控制），
    Linux/Mac 主线程使用 signal 实现。"""
    if sys.platform == "win32" or threading.current_thread() is not threading.main_thread():
        yield
        return

    def handler(signum, frame):
        raise TimeoutError(f"AKShare 调用超过 {seconds}s")

    old = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _latest_report_date(stock_code: str) -> str | None:
    """从财务指标接口推断最新报告期，用于 stock_xjll_em 的 date 参数。"""
    try:
        df = ak.stock_financial_analysis_indicator_em(symbol=stock_code)
        if df.empty or "报告期" not in df.columns:
            return None
        periods = df["报告期"].dropna().astype(str).tolist()
        if not periods:
            return None
        latest = max(periods)
        if "Q" in latest:
            year, q = latest.split("Q")
            q_end = {"1": "0331", "2": "0630", "3": "0930", "4": "1231"}
            return f"{year}{q_end.get(q, '1231')}"
        if len(latest) == 8 and latest.isdigit():
            return latest
        return None
    except Exception:
        return None


def trade_status() -> str:
    now = datetime.now()
    if now.weekday() >= 5:
        return "non_trading_weekend"
    if 9 <= now.hour < 15:
        return "trading_or_lunch_break"
    return "non_trading_after_hours"