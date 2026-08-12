"""
智能股票分析助手 — 自选股管理服务层

封装自选股查询、添加、删除的数据查询逻辑，供API路由层调用。
"""

import sys
from pathlib import Path
# 确保skills路径可导入
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # backend/app/services -> project root
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_ZIXUAN = _PROJECT_ROOT / "skills" / "自选股管理" / "mx-zixuan"

for p in [_AGENTS_DIR, _SKILLS_ZIXUAN, str(_PROJECT_ROOT)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.config import settings
from app.services.mx_timed_cache import get_mx_timed_cache, mx_cache_ttl_seconds

# 与 mx_data / mx_search 共用 TTL（默认 600s）：逾时才再打妙想侧自选接口
_WATCHLIST_CACHE_QUERY = "mx_zixuan_self_select_list"


def _watchlist_cache_key() -> str:
    return get_mx_timed_cache().make_key("mx_zixuan", _WATCHLIST_CACHE_QUERY)


def _invalidate_watchlist_cache() -> None:
    get_mx_timed_cache().delete(_watchlist_cache_key())


def _get_mx_zixuan_instance():
    """创建mx_zixuan API调用实例"""
    import mx_zixuan as _mx
    return _mx


def get_watchlist() -> dict:
    """查询自选股列表

    Returns:
        {
            "success": True/False,
            "stocks": [{"code": str, "name": str, "price": float, ...}, ...],
            "total": int,
            "error": str or None
        }
    """
    import mx_zixuan as _mx

    ttl = mx_cache_ttl_seconds()
    if ttl > 0:
        cached = get_mx_timed_cache().get_fresh(_watchlist_cache_key(), ttl)
        if cached is not None:
            return cached

    result = {
        "success": False,
        "stocks": [],
        "total": 0,
        "error": None,
    }

    if not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here":
        result["error"] = "MX_APIKEY 未配置"
        return result

    try:
        raw_result = _mx.query_self_select(settings.MX_APIKEY)

        # 检查API状态
        status = raw_result.get("status", -1)
        code = raw_result.get("code", -1)
        if status != 0 and code != 0:
            result["error"] = raw_result.get("message", "查询自选股失败")
            return result

        # 解析查询结果
        data = raw_result.get("data", {})
        all_results = data.get("allResults", {})
        result_data = all_results.get("result", {})
        data_list = result_data.get("dataList", [])

        stocks = []
        for stock in (data_list or []):
            stocks.append({
                "code": stock.get("SECURITY_CODE", ""),
                "name": stock.get("SECURITY_SHORT_NAME", ""),
                "price": stock.get("NEWEST_PRICE", ""),
                "change_pct": stock.get("CHG", ""),
                "change_amount": stock.get("PCHG", ""),
                "turnover_rate": stock.get("010000_TURNOVER_RATE", ""),
                "volume_ratio": stock.get("010000_LIANGBI", ""),
            })

        result["success"] = True
        result["stocks"] = stocks
        result["total"] = len(stocks)
        if ttl > 0:
            get_mx_timed_cache().set(_watchlist_cache_key(), result)
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def add_to_watchlist(stock_input: str) -> dict:
    """添加股票到自选股

    Args:
        stock_input: 股票名称或代码，如 "贵州茅台" 或 "600519"

    Returns:
        {
            "success": True/False,
            "message": str,
            "error": str or None
        }
    """
    import mx_zixuan as _mx

    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    if not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here":
        result["error"] = "MX_APIKEY 未配置"
        return result

    try:
        # 构造自然语言添加指令
        query = f"把{stock_input}添加到我的自选股列表"
        raw_result = _mx.manage_self_select(settings.MX_APIKEY, query)

        status = raw_result.get("status", -1)
        code = raw_result.get("code", -1)
        if status != 0 and code != 0:
            result["error"] = raw_result.get("message", "添加自选股失败")
            return result

        result["success"] = True
        result["message"] = raw_result.get("message", f"已将 {stock_input} 加入自选")
        _invalidate_watchlist_cache()
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def delete_from_watchlist(stock_input: str) -> dict:
    """从自选股中删除股票

    Args:
        stock_input: 股票名称或代码，如 "贵州茅台" 或 "600519"

    Returns:
        {
            "success": True/False,
            "message": str,
            "error": str or None
        }
    """
    import mx_zixuan as _mx

    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    if not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here":
        result["error"] = "MX_APIKEY 未配置"
        return result

    try:
        # 构造自然语言删除指令
        query = f"把{stock_input}从我的自选股列表删除"
        raw_result = _mx.manage_self_select(settings.MX_APIKEY, query)

        status = raw_result.get("status", -1)
        code = raw_result.get("code", -1)
        if status != 0 and code != 0:
            result["error"] = raw_result.get("message", "删除自选股失败")
            return result

        result["success"] = True
        result["message"] = raw_result.get("message", f"已将 {stock_input} 从自选中移除")
        _invalidate_watchlist_cache()
        return result

    except Exception as e:
        result["error"] = str(e)
        return result
