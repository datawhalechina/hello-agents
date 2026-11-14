# src/agent/NewsSentimentAgent/news_tools/collector.py
import os
import json
import time
from datetime import datetime
import akshare as ak
import pandas as pd
from typing import List

# 导入你的 Schema
from src.agent.NewsSentimentAgent.schemas import RawNewsSchema

# 复用你 Agent1 里的重试 Session（如果你的路径不同，请调整 import）
try:
    from src.agent.MarketDataCollectorAgent.stock_tools._common import _create_retry_session

    # 尝试注入重试机制
    if hasattr(ak, "requests"):
        ak.requests = _create_retry_session(retries=3, backoff_factor=1.5)
except ImportError:
    print("[Warning] 未找到 Agent1 的 _common 模块，将使用默认网络请求。")

CACHE_DIR = "./news_data_cache"


def _get_cache_file(symbol: str) -> str:
    """获取当天的缓存文件路径"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    today_str = datetime.today().strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, f"{symbol}_news_{today_str}.json")


def _fetch_from_em(symbol: str) -> pd.DataFrame:
    """数据源 1：东方财富"""
    return ak.stock_news_em(symbol=symbol)


def _fetch_from_sina(symbol: str) -> pd.DataFrame:
    """数据源 2：新浪财经 (备用)"""
    # akshare 的 stock_news_sina 接口需要带前缀，如 'sh600519' 或 'sz000001'
    prefix = "sh" if symbol.startswith(("6", "5")) else "sz"
    ak_symbol = f"{prefix}{symbol}"
    return ak.stock_news_sina(symbol=ak_symbol)


def fetch_stock_news(symbol: str, limit: int = 30, force_refresh: bool = False) -> List[RawNewsSchema]:
    """
    获取个股新闻，带按天缓存与多源回退。
    :param symbol: 股票代码，如 "000001"
    :param limit: 限制条数
    :param force_refresh: 是否强制刷新（忽略当日缓存）
    """
    cache_file = _get_cache_file(symbol)

    # 1. 检查缓存
    if not force_refresh and os.path.exists(cache_file):
        print(f"[Cache Hit] 发现今日缓存，直接从文件读取: {cache_file}")
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 将 JSON 数据转回 Pydantic 对象
            return [RawNewsSchema(**item) for item in data[:limit]]
        except Exception as e:
            print(f"[Warning] 读取缓存失败，将重新拉取: {e}")

    print(f"[Network] 正在采集股票 {symbol} 的新闻数据 (Limit={limit})...")
    df = pd.DataFrame()

    # 2. 多源回退机制
    # 尝试东财
    try:
        df = _fetch_from_em(symbol)
    except Exception as e:
        print(f"[Warning] 东方财富新闻接口失败: {e}")

    # 如果东财失败，尝试新浪
    if df.empty:
        try:
            print("[Info] 尝试新浪新闻接口...")
            df = _fetch_from_sina(symbol)
        except Exception as e:
            print(f"[Warning] 新浪新闻接口也失败: {e}")
            return []  # 如果全军覆没，返回空列表

    if df.empty:
        return []

    # 3. 清洗与格式化
    # 注意：不同数据源返回的列名可能不同，需要统一
    column_mapping = {
        "新闻标题": "title", "title": "title",
        "新闻内容": "content", "content": "content",
        "发布时间": "publish_time", "datetime": "publish_time", "时间": "publish_time",
        "文章来源": "source", "source": "source", "媒体名称": "source",
        "新闻链接": "url", "url": "url"
    }
    df = df.rename(columns=column_mapping)

    # 确保所需列存在
    for col in ["title", "content", "publish_time", "source", "url"]:
        if col not in df.columns:
            df[col] = ""

    # 去重 (按 URL 或 Title)
    df = df.drop_duplicates(subset=["url", "title"])

    # 清洗正文长度
    df["content"] = df["content"].astype(str).apply(lambda x: x[:300] if len(x) > 300 else x)

    # 格式化时间 (如果是 datetime 对象则转字符串)
    df["publish_time"] = df["publish_time"].astype(str)

    # 转换为 Pydantic 对象
    news_list = []
    for _, row in df.iterrows():
        if not row.get("title") or not str(row.get("title")).strip():
            continue

        news_item = RawNewsSchema(
            title=str(row.get("title")),
            content=str(row.get("content")) if row.get("content") else None,
            publish_time=str(row.get("publish_time")),
            source=str(row.get("source")),
            url=str(row.get("url"))
        )
        news_list.append(news_item)

    # 4. 写入缓存 (保存未截断的全部数据，供当日复用)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            # 使用 Pydantic 的 model_dump() 转换为 dict
            json.dump([item.model_dump() for item in news_list], f, ensure_ascii=False, indent=2)
        print(f"[Cache Save] 已保存 {len(news_list)} 条新闻至今日缓存。")
    except Exception as e:
        print(f"[Warning] 缓存文件保存失败: {e}")

    # 5. 返回限制条数的结果
    return news_list[:limit]
