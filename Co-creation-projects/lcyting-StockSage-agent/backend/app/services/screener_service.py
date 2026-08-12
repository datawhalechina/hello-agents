"""
智能股票分析助手 — 智能选股服务层

封装智能选股查询、条件解析和数据格式化逻辑。
含 mx-xuangu 计时缓存与额度用尽时的缓存降级。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_XUANGU = _PROJECT_ROOT / "skills" / "智能选股" / "mx-xuangu"

for p in [_AGENTS_DIR, _SKILLS_XUANGU, str(_PROJECT_ROOT)]:
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


def _fetch_screen_live(query: str) -> dict:
    import mx_xuangu as _mx

    result = {
        "success": False,
        "query": query,
        "total_count": 0,
        "data_source": "",
        "stocks": [],
        "conditions": [],
        "error": None,
    }

    raw_fixture = try_load_raw_fixture("mx_xuangu", query)
    raw_result = raw_fixture

    try:
        if raw_result is None:
            key_ok = bool(settings.MX_APIKEY and settings.MX_APIKEY != "your-mx-apikey-here")
            if not key_ok:
                result["error"] = "MX_APIKEY 未配置，且无匹配的本地 fixture"
                return result
            screener = _mx.MXSelectStock(api_key=settings.MX_APIKEY)
            raw_result = screener.search(query)

        rows, data_source, error = _mx.MXSelectStock.extract_data(raw_result)

        if error:
            result["error"] = (f"[fixture] {error}" if raw_fixture is not None else error)
            return result

        data = raw_result.get("data", {})
        inner_data = data.get("data", {})
        response_conditions = inner_data.get("responseConditionList", []) or []

        conditions = []
        for cond in response_conditions:
            if isinstance(cond, dict):
                conditions.append({
                    "describe": cond.get("describe", ""),
                    "stock_count": cond.get("stockCount", 0),
                })

        result["success"] = True
        result["total_count"] = len(rows)
        result["data_source"] = data_source
        result["stocks"] = rows
        result["conditions"] = conditions
        return result

    except Exception as e:
        result["error"] = (f"[fixture] {e}" if raw_fixture is not None else str(e))
        return result


def screen_stocks(query: str) -> dict:
    """执行智能选股（选股条件字符串不同则缓存键不同）"""
    result = {
        "success": False,
        "query": query,
        "total_count": 0,
        "data_source": "",
        "stocks": [],
        "conditions": [],
        "error": None,
    }

    key_missing = not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here"
    if key_missing and not settings.MX_REPLAY_FIXTURES:
        result["error"] = "MX_APIKEY 未配置"
        return result

    cache = get_mx_timed_cache()
    ttl = mx_cache_ttl_seconds()
    key = cache.make_key("mx_xuangu", query)

    fresh = cache.get_fresh(key, ttl)
    if fresh is not None:
        return _attach(fresh, _meta_block(from_cache=True, quota_exhausted=False, channel="mx_xuangu"))

    live = _fetch_screen_live(query)

    if live["success"]:
        cache.set(key, live)
        return _attach(live, _meta_block(from_cache=False, quota_exhausted=False, channel="mx_xuangu"))

    err = live.get("error") or ""
    if is_mx_quota_exhausted(err):
        stale = cache.get_stale(key)
        if stale:
            merged = copy.deepcopy(stale)
            merged["success"] = True
            merged["query"] = query
            return _attach(merged, _meta_block(from_cache=True, quota_exhausted=True, channel="mx_xuangu"))
        live["error"] = quota_exhausted_no_cache_message(err)
        return live

    return live


def get_available_conditions() -> dict:
    """获取常用的选股条件参考（静态说明，不调用妙想）"""
    return {
        "success": True,
        "categories": [
            {
                "name": "行情指标",
                "description": "基于实时行情数据的筛选条件",
                "examples": [
                    "今日涨幅大于2%",
                    "成交量大于10亿",
                    "股价在10元到20元之间",
                    "换手率大于5%",
                ],
            },
            {
                "name": "财务指标",
                "description": "基于财务报表数据的筛选条件",
                "examples": [
                    "市盈率小于20",
                    "市净率小于2",
                    "ROE大于15%",
                    "净利润增长率大于20%",
                    "股息率大于3%",
                ],
            },
            {
                "name": "行业板块",
                "description": "限定行业或板块范围的筛选",
                "examples": [
                    "新能源板块",
                    "白酒板块",
                    "半导体行业",
                    "银行股",
                ],
            },
            {
                "name": "指数成分",
                "description": "指定指数成分股内筛选",
                "examples": [
                    "沪深300成分股",
                    "创业板成分股",
                    "上证50成分股",
                ],
            },
        ],
    }
