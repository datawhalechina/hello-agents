# backend/data/sources/news_adapter.py
import asyncio
import json
import requests
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.eastmoney.com/",
}


async def fetch_stock_news(symbol: str, limit: int = 10) -> list[dict]:
    """
    从东方财富抓取个股公告和新闻。
    使用公告接口，数据稳定，不依赖搜索接口。
    """
    def _fetch_announcements():
        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "sr": -1,
            "page_size": limit,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": symbol,
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("list", [])
        return [
            {
                "title": item.get("title", ""),
                "time": item.get("display_time", ""),
                "source": "东方财富公告",
                "type": "announcement",
            }
            for item in items
        ]

    def _fetch_news():
        """补充新浪财经快讯"""
        url = "https://zhibo.sina.com.cn/api/zhibo/feed"
        params = {
            "page": 1,
            "page_size": limit,
            "zhibo_id": "152",
            "tag_id": 0,
            "dire": "f",
            "dpc": 1,
            "type": 0,
        }
        resp = requests.get(url, params=params, headers={
            **HEADERS, "Referer": "https://finance.sina.com.cn/",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
        results = []
        for item in items[:limit]:
            rich_text = item.get("rich_text", "")
            # 过滤掉 unicode 转义，取纯文本
            try:
                text = rich_text.encode().decode("unicode_escape")
            except Exception:
                text = rich_text
            if len(text) > 10:
                results.append({
                    "title": text[:80],
                    "time": item.get("create_time", ""),
                    "source": "新浪财经",
                    "type": "news",
                })
        return results

    try:
        # 并行拉取公告 + 快讯
        ann_task = asyncio.to_thread(_fetch_announcements)
        news_task = asyncio.to_thread(_fetch_news)
        results = await asyncio.gather(ann_task, news_task, return_exceptions=True)

        combined = []
        for r in results:
            if isinstance(r, Exception):
                print(f"新闻子接口失败: {r}")
            else:
                combined.extend(r)

        return combined[:limit]

    except Exception as e:
        print(f"新闻获取失败 [{symbol}]: {e}")
        return []


async def fetch_market_news(limit: int = 10) -> list[dict]:
    """获取市场整体财经快讯"""
    def _fetch():
        url = "https://zhibo.sina.com.cn/api/zhibo/feed"
        params = {
            "page": 1,
            "page_size": limit,
            "zhibo_id": "152",
            "tag_id": 0,
            "dire": "f",
            "dpc": 1,
            "type": 0,
        }
        resp = requests.get(url, params=params, headers={
            **HEADERS, "Referer": "https://finance.sina.com.cn/",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
        return [
            {
                "title": item.get("rich_text", "")[:80],
                "time": item.get("create_time", ""),
                "source": "新浪财经",
            }
            for item in items
        ]

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        print(f"市场新闻获取失败: {e}")
        return []