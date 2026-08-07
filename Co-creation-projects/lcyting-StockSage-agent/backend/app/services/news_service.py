"""
智能股票分析助手 — 资讯搜索服务层

封装金融资讯搜索、个股舆情分析的数据查询逻辑。
含 mx-search 计时缓存与额度用尽时的缓存降级。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_SEARCH = _PROJECT_ROOT / "skills" / "资讯搜索" / "mx-search"

for p in [_AGENTS_DIR, _SKILLS_SEARCH, str(_PROJECT_ROOT)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.config import settings
from app.services.mx_timed_cache import get_mx_timed_cache, mx_cache_ttl_seconds
from app.utils.mx_fixture import try_load_raw_fixture
from app.utils.mx_quota import MX_QUOTA_HINT, is_mx_quota_exhausted, quota_exhausted_no_cache_message


def _meta_block(*, from_cache: bool, quota_exhausted: bool, channel: str) -> dict:
    m = {
        "from_cache": from_cache,
        "quota_exhausted": quota_exhausted,
        "cache_ttl_seconds": int(mx_cache_ttl_seconds()),
        "channel": channel,
    }
    if quota_exhausted:
        m["hint"] = MX_QUOTA_HINT
    return m


def _attach(payload: dict, meta: dict) -> dict:
    out = copy.deepcopy(payload)
    out["_mx_meta"] = meta
    return out


def _merge_item_text_fields(item: dict) -> str:
    """合并正文/摘要等字段（妙想不同条目可能落在 content、summary 等键上）。"""
    chunks: list[str] = []
    seen: set[str] = set()
    for key in (
        "content",
        "summary",
        "abstract",
        "digest",
        "snippet",
        "description",
        "desc",
        "text",
    ):
        v = item.get(key)
        if not isinstance(v, str):
            continue
        s = v.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        chunks.append(s)
    return "\n\n".join(chunks)


def _normalize_information_type(item: dict) -> tuple[str, str]:
    """将妙想条目上的类型字段统一为 (NEWS|REPORT|ANNOUNCEMENT|OTHER, 中文标签)。

    常见坑：仅写了 info_type 默认 NEWS，但 info_type_cn 因 informationType 为空变成「资讯」，
    前端饼图只认三种中文，导致大量条目不计入分布。
    """
    raw = item.get("informationType")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        for k in ("infoType", "information_type", "info_type", "docType", "category", "dataType"):
            v = item.get(k)
            if v is not None and str(v).strip():
                raw = v
                break

    cn_by_en = {"NEWS": "新闻", "REPORT": "研报", "ANNOUNCEMENT": "公告", "OTHER": "其他"}

    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        return "NEWS", cn_by_en["NEWS"]

    if isinstance(raw, (int, float)):
        # 无公开数字枚举说明时不猜测，避免错分进「仅研报」等畸形分布
        return "OTHER", cn_by_en["OTHER"]

    s = str(raw).strip()
    u = s.upper().replace(" ", "_").replace("-", "_")

    if u in ("NEWS", "REPORT", "ANNOUNCEMENT"):
        return u, cn_by_en[u]

    # 小写 json：news / report / announcement
    low = s.lower()
    if low in ("news",):
        return "NEWS", cn_by_en["NEWS"]
    if low in ("report",):
        return "REPORT", cn_by_en["REPORT"]
    if low in ("announcement", "announce"):
        return "ANNOUNCEMENT", cn_by_en["ANNOUNCEMENT"]

    # 中文或混合文案
    if "公告" in s:
        return "ANNOUNCEMENT", cn_by_en["ANNOUNCEMENT"]
    if "研报" in s or "研究报告" in s:
        return "REPORT", cn_by_en["REPORT"]
    if "新闻" in s:
        return "NEWS", cn_by_en["NEWS"]

    if "ANNOUNCE" in u or "NOTICE" in u:
        return "ANNOUNCEMENT", cn_by_en["ANNOUNCEMENT"]
    if "REPORT" in u:
        return "REPORT", cn_by_en["REPORT"]
    if "NEWS" in u:
        return "NEWS", cn_by_en["NEWS"]

    return "OTHER", cn_by_en["OTHER"]


# 妙想 / 东方财富资讯条目可能出现的链接字段（含嵌套 dict 扫描）
_URL_KEYS_ORDERED = (
    "url",
    "link",
    "articleUrl",
    "sourceUrl",
    "detailUrl",
    "pcUrl",
    "h5Url",
    "jumpUrl",
    "artUrl",
    "newsUrl",
    "oriUrl",
    "originUrl",
    "showUrl",
    "pageUrl",
    "wapUrl",
    "pcLink",
    "h5Link",
    "article_url",
    "news_url",
    "srcUrl",
    "webUrl",
    "mobileUrl",
    "urlPc",
    "urlH5",
    "pc_url",
    "h5_url",
    "shareUrl",
    "share_link",
)

# 递归扫描时跳过明显正文/标题字段，避免误把片段当外链
_SKIP_URL_SCAN_KEYS = frozenset(
    {
        "content",
        "summary",
        "abstract",
        "digest",
        "snippet",
        "description",
        "desc",
        "text",
        "title",
        "body",
        "rawContent",
        "answer",
    }
)


def _item_original_url(item: dict, *, depth: int = 0) -> str:
    """提取可外链打开的原文地址（若有）。兼容多层嵌套与非常规字段名。"""
    if not isinstance(item, dict) or depth > 6:
        return ""

    for key in _URL_KEYS_ORDERED:
        v = item.get(key)
        if isinstance(v, str):
            s = v.strip()
            if s.lower().startswith(("http://", "https://")):
                return s

    for k, v in item.items():
        if k in _SKIP_URL_SCAN_KEYS:
            continue
        if isinstance(v, str):
            s = v.strip()
            if len(s) > 2048:
                continue
            if s.lower().startswith(("http://", "https://")):
                return s
        elif isinstance(v, dict):
            inner = _item_original_url(v, depth=depth + 1)
            if inner:
                return inner
        elif isinstance(v, list) and depth < 4:
            for el in v[:24]:
                if isinstance(el, dict):
                    inner = _item_original_url(el, depth=depth + 1)
                    if inner:
                        return inner
    return ""


def _mx_search_from_raw(query: str, raw_result: dict) -> dict:
    """将 mx-search 原始响应转为统一 payload"""
    result = {
        "success": False,
        "query": query,
        "total_count": 0,
        "items": [],
        "error": None,
    }

    status = raw_result.get("status")
    if status != 0:
        result["error"] = raw_result.get("message", f"API返回错误，状态码: {status}")
        return result

    data = raw_result.get("data", {})
    inner_data = data.get("data", {})
    search_response = inner_data.get("llmSearchResponse", {})
    items = search_response.get("data", []) or []

    parsed_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        body = _merge_item_text_fields(item)
        en_type, cn_type = _normalize_information_type(item)
        parsed_items.append({
            "title": item.get("title", "无标题"),
            "content": body,
            "date": item.get("date", ""),
            "institution": item.get("insName", ""),
            "info_type": en_type,
            "info_type_cn": cn_type,
            "rating": item.get("rating", ""),
            "entity_name": item.get("entityFullName", ""),
            "url": _item_original_url(item),
        })

    result["success"] = True
    result["total_count"] = len(parsed_items)
    result["items"] = parsed_items
    return result


def _fetch_mx_search_live(query: str) -> dict:
    """直连 mx-search；MX_REPLAY_FIXTURES 时优先读本地原始 JSON"""
    raw_fixture = try_load_raw_fixture("mx_search", query)
    if raw_fixture is not None:
        try:
            return _mx_search_from_raw(query, raw_fixture)
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "total_count": 0,
                "items": [],
                "error": f"[fixture] {e}",
            }

    key_ok = bool(settings.MX_APIKEY and settings.MX_APIKEY != "your-mx-apikey-here")
    if not key_ok:
        return {
            "success": False,
            "query": query,
            "total_count": 0,
            "items": [],
            "error": "MX_APIKEY 未配置，且无匹配的本地 fixture",
        }

    try:
        import mx_search as _mx

        search_client = _mx.MXSearch(api_key=settings.MX_APIKEY)
        raw_result = search_client.search(query)
        return _mx_search_from_raw(query, raw_result)

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "total_count": 0,
            "items": [],
            "error": str(e),
        }


def search_news(query: str) -> dict:
    """搜索金融资讯（同一 query 在 TTL 内走缓存；关键词/个股不同则 query 不同）"""
    result = {
        "success": False,
        "query": query,
        "total_count": 0,
        "items": [],
        "error": None,
    }

    key_missing = not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here"
    if key_missing and not settings.MX_REPLAY_FIXTURES:
        result["error"] = "MX_APIKEY 未配置"
        return result

    cache = get_mx_timed_cache()
    ttl = mx_cache_ttl_seconds()
    key = cache.make_key("mx_search", query)

    fresh = cache.get_fresh(key, ttl)
    if fresh is not None:
        return _attach(fresh, _meta_block(from_cache=True, quota_exhausted=False, channel="mx_search"))

    live = _fetch_mx_search_live(query)

    if live["success"]:
        cache.set(key, live)
        return _attach(live, _meta_block(from_cache=False, quota_exhausted=False, channel="mx_search"))

    err = live.get("error") or ""
    if is_mx_quota_exhausted(err):
        stale = cache.get_stale(key)
        if stale:
            merged = copy.deepcopy(stale)
            merged["success"] = True
            merged["query"] = query
            return _attach(merged, _meta_block(from_cache=True, quota_exhausted=True, channel="mx_search"))
        live["error"] = quota_exhausted_no_cache_message(err)
        return live

    return live


def search_stock_news(code: str) -> dict:
    """搜索个股相关资讯"""
    query = f"{code} 最新研报 新闻 公告"
    return search_news(query)


def search_sector_news(sector: str) -> dict:
    """搜索行业/板块相关资讯"""
    query = f"{sector}板块近期新闻 政策解读"
    return search_news(query)


def search_market_news() -> dict:
    """搜索市场热门资讯"""
    query = "今日A股市场热点 大盘动态 北向资金"
    return search_news(query)


def analyze_sentiment(code: str) -> dict:
    """个股舆情分析（文件缓存优先 + 继承底层 search 的 _mx_meta）"""
    from app.services.stock_file_cache import get_stock_file_cache
    fc = get_stock_file_cache()

    cached = fc.get(code, "sentiment")
    if cached and cached.get("data") and cached["data"].get("success"):
        return cached["data"]

    base = search_stock_news(code)
    meta = base.get("_mx_meta")

    if not base["success"]:
        out = {
            "success": False,
            "code": code,
            "total_count": 0,
            "news_items": [],
            "report_items": [],
            "announce_items": [],
            "error": base["error"],
        }
        if meta:
            out["_mx_meta"] = meta
        return out

    items = base["items"]
    report_items = [i for i in items if i["info_type"] == "REPORT"]
    announce_items = [i for i in items if i["info_type"] == "ANNOUNCEMENT"]
    news_items = [i for i in items if i["info_type"] not in ("REPORT", "ANNOUNCEMENT")]
    out = {
        "success": True,
        "code": code,
        "total_count": base["total_count"],
        "news_items": news_items,
        "report_items": report_items,
        "announce_items": announce_items,
        "error": None,
    }
    if meta:
        out["_mx_meta"] = meta

    fc.set(code, "sentiment", out)
    return out
