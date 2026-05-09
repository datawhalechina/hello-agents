"""
智能股票分析助手 — 行情数据服务层

封装金融数据查询、解析和格式化逻辑，供API路由层调用。
含妙想 mx_data 计时缓存与额度用尽时的缓存降级。
"""

from __future__ import annotations

import copy
import math
import re
import sys
from pathlib import Path
from typing import Any, Optional

# 确保skills路径可导入
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # backend/app/services -> project root
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_DATA = _PROJECT_ROOT / "skills" / "金融数据" / "mx-data"

for p in [_AGENTS_DIR, _SKILLS_DATA, str(_PROJECT_ROOT)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.config import settings
from app.services.mx_timed_cache import get_mx_timed_cache, mx_cache_ttl_seconds
from app.utils.mx_fixture import try_load_raw_fixture
from app.utils.mx_quota import MX_QUOTA_HINT, is_mx_quota_exhausted, quota_exhausted_no_cache_message

# 仪表盘指数卡片：从 mx tables 中解析列名（妙想返回的表头差异较大）
_PRICE_HDR = re.compile(
    r"点位|最新点|收盘点|指数点位|收盘价|最新价|现价|收盘|价格|数值|行情|昨收|今开|当前价|最新报价|报价",
    re.I,
)
_CHANGE_HDR = re.compile(
    r"涨跌幅|涨跌幅度|当日涨幅|日涨跌幅|涨跌|涨幅|变动率",
    re.I,
)
_DATE_HDR = re.compile(r"日期|时间|^date$", re.I)
_LONG_PRICE_LABEL = re.compile(
    r"点位|最新点|收盘点|指数点位|收盘价|最新价|现价|收盘|价格|最新|上证|深证|成指|沪深300|创业板指",
)
_LONG_CHANGE_LABEL = re.compile(r"涨跌幅|涨跌幅度|当日涨幅|涨跌|涨幅|变动率")


def _parse_pct_cell(val: Any) -> Optional[float]:
    """解析涨跌幅单元格为浮点数（百分比数值，不带 % 也可）"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        x = float(val)
        return x if math.isfinite(x) else None
    s = str(val).strip()
    if not s or s in ("--", "—", "-", "暂无"):
        return None
    s = re.sub(r"[%％,，]", "", s)
    s = s.replace("＋", "+").replace("−", "-").replace("－", "-")
    m = re.search(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", s, re.I)
    if not m:
        return None
    try:
        x = float(m.group(0))
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _cell_at(names: list, row: dict, idx: int) -> Any:
    if idx < 0 or not isinstance(row, dict):
        return None
    if idx >= len(names):
        return None
    return row.get(names[idx])


def _heuristic_index_from_row(row: dict, names: list[str]) -> tuple[Optional[str], Optional[float]]:
    """列名无法识别时，按数值量级与 % 符号兜底"""
    change: Optional[float] = None
    price_disp: Optional[str] = None
    best: float = -1.0
    keys = [n for n in names if n in row] if names else list(row.keys())
    for k in keys:
        if _DATE_HDR.search(str(k)):
            continue
        raw = row[k]
        if raw is None:
            continue
        sv = str(raw).strip()
        if not sv:
            continue
        if "%" in sv or "％" in sv:
            p = _parse_pct_cell(sv)
            if p is not None:
                change = p
            continue
        p = _parse_pct_cell(sv)
        if p is None:
            continue
        # A 股主要指数点位多在数百～数万之间
        if 500 <= abs(p) <= 50000:
            if abs(p) > best:
                best = abs(p)
                price_disp = sv
    return price_disp, change


def _extract_index_card_one_table(t0: dict) -> tuple[Optional[str], Optional[float]]:
    """从 mx_data 单个 sheet 解析点位与涨跌幅（字段名与行结构随品种变化较大）"""
    names: list = list(t0.get("fieldnames") or t0.get("fieldNames") or [])
    rows = t0.get("rows") or []
    if not rows:
        return None, None

    # 长表：恰两列，每行一个指标
    if len(names) == 2:
        lk, vk = names[0], names[1]
        price_s: Optional[str] = None
        change_v: Optional[float] = None
        for r in rows:
            if not isinstance(r, dict):
                continue
            lab = str(r.get(lk, "")).strip()
            raw = r.get(vk)
            if _LONG_CHANGE_LABEL.search(lab):
                c = _parse_pct_cell(raw)
                if c is not None:
                    change_v = c
            elif _LONG_PRICE_LABEL.search(lab):
                if price_s is None and raw is not None and str(raw).strip():
                    price_s = str(raw).strip()
        if price_s or change_v is not None:
            return price_s, change_v

    date_idx = next((i for i, n in enumerate(names) if _DATE_HDR.search(str(n))), -1)
    data_row = rows[-1] if date_idx >= 0 and len(rows) > 1 else rows[0]

    if isinstance(data_row, list):
        pi = next((i for i, n in enumerate(names) if _PRICE_HDR.search(str(n))), -1)
        ci = next((i for i, n in enumerate(names) if _CHANGE_HDR.search(str(n))), -1)
        raw_p = data_row[pi] if 0 <= pi < len(data_row) else None
        raw_c = data_row[ci] if 0 <= ci < len(data_row) else None
        ps = str(raw_p).strip() if raw_p is not None and str(raw_p).strip() else None
        cv = _parse_pct_cell(raw_c)
        if ps or cv is not None:
            return ps, cv
        return None, None

    if isinstance(data_row, dict):
        pi = next((i for i, n in enumerate(names) if _PRICE_HDR.search(str(n))), -1)
        ci = next((i for i, n in enumerate(names) if _CHANGE_HDR.search(str(n))), -1)
        raw_p = _cell_at(names, data_row, pi)
        raw_c = _cell_at(names, data_row, ci)
        ps = str(raw_p).strip() if raw_p is not None and str(raw_p).strip() else None
        cv = _parse_pct_cell(raw_c)
        if ps or cv is not None:
            return ps, cv
        return _heuristic_index_from_row(data_row, names)

    return None, None


def _extract_index_card_from_tables(tables: list) -> tuple[Optional[str], Optional[float]]:
    """从 mx_data 全部 sheet 解析仪表盘展示字段（妙想常返回多表，首表可能是说明性空表）"""
    if not tables:
        return None, None
    merged_p: Optional[str] = None
    merged_c: Optional[float] = None
    for t in tables:
        if not isinstance(t, dict):
            continue
        p, c = _extract_index_card_one_table(t)
        if p is not None and c is not None:
            return p, c
        if merged_p is None and p is not None:
            merged_p = p
        if merged_c is None and c is not None:
            merged_c = c
        if merged_p is not None and merged_c is not None:
            return merged_p, merged_c
    return merged_p, merged_c


def _enrich_index_quote_result(result: dict) -> dict:
    """成功返回时附加 display_*，供前端直接使用；deepcopy 避免污染进程内缓存对象"""
    if not result.get("success"):
        return result
    out = copy.deepcopy(result)
    price, chg = _extract_index_card_from_tables(out.get("tables") or [])
    if price is not None:
        out["display_price"] = price
    if chg is not None:
        out["display_change_pct"] = chg
    return out


def _mx_result_meta(*, from_cache: bool, quota_exhausted: bool, channel: str) -> dict:
    ttl = int(mx_cache_ttl_seconds())
    m = {
        "from_cache": from_cache,
        "quota_exhausted": quota_exhausted,
        "cache_ttl_seconds": ttl,
        "channel": channel,
    }
    if quota_exhausted:
        m["hint"] = MX_QUOTA_HINT
    return m


def _attach_meta(payload: dict, meta: dict) -> dict:
    out = copy.deepcopy(payload)
    out["_mx_meta"] = meta
    return out


def _fetch_mx_data_live(query: str) -> dict:
    """直连妙想 mx_data；MX_REPLAY_FIXTURES 时优先读本地原始 JSON（不修额度）"""
    import mx_data as _mx

    result = {
        "success": False,
        "query": query,
        "tables": [],
        "condition_parts": [],
        "total_rows": 0,
        "error": None,
    }

    raw_fixture = try_load_raw_fixture("mx_data", query)
    if raw_fixture is not None:
        try:
            tables, condition_parts, total_rows, error = _mx.MXData.parse_result(raw_fixture)
            if error:
                result["error"] = f"[fixture] {error}"
                return result
            result["success"] = True
            result["tables"] = tables
            result["condition_parts"] = condition_parts
            result["total_rows"] = total_rows
            return result
        except Exception as e:
            result["error"] = f"[fixture] 解析失败: {e}"
            return result

    key_ok = bool(settings.MX_APIKEY and settings.MX_APIKEY != "your-mx-apikey-here")
    if not key_ok:
        result["error"] = "MX_APIKEY 未配置，且无匹配的本地 fixture（设置 MX_REPLAY_FIXTURES=1 并放置 JSON）"
        return result

    try:
        querier = _mx.MXData(api_key=settings.MX_APIKEY)
        raw_result = querier.query(query)
        tables, condition_parts, total_rows, error = _mx.MXData.parse_result(raw_result)

        if error:
            result["error"] = error
            return result

        result["success"] = True
        result["tables"] = tables
        result["condition_parts"] = condition_parts
        result["total_rows"] = total_rows
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def query_financial_data(query: str) -> dict:
    """执行金融数据查询并返回结构化结果（带计时缓存与额度降级）

    缓存键为规范化后的自然语言 query：
    - 相同查询串在 TTL 内不会重复请求妙想；
    - 股票代码 / 财务指标不同会得到不同 query，从而自动区分。
    """
    result = {
        "success": False,
        "query": query,
        "tables": [],
        "condition_parts": [],
        "total_rows": 0,
        "error": None,
    }

    key_missing = not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here"
    if key_missing and not settings.MX_REPLAY_FIXTURES:
        result["error"] = "MX_APIKEY 未配置"
        return result

    cache = get_mx_timed_cache()
    ttl = mx_cache_ttl_seconds()
    key = cache.make_key("mx_data", query)

    fresh = cache.get_fresh(key, ttl)
    if fresh is not None:
        return _attach_meta(
            fresh,
            _mx_result_meta(from_cache=True, quota_exhausted=False, channel="mx_data"),
        )

    live = _fetch_mx_data_live(query)

    if live["success"]:
        cache.set(key, live)
        return _attach_meta(
            live,
            _mx_result_meta(from_cache=False, quota_exhausted=False, channel="mx_data"),
        )

    err = live.get("error") or ""
    if is_mx_quota_exhausted(err):
        stale = cache.get_stale(key)
        if stale:
            merged = copy.deepcopy(stale)
            merged["success"] = True
            merged["query"] = query
            return _attach_meta(
                merged,
                _mx_result_meta(from_cache=True, quota_exhausted=True, channel="mx_data"),
            )
        live["error"] = quota_exhausted_no_cache_message(err)
        return live

    return live


def get_stock_quote(code: str) -> dict:
    """查询个股实时行情

    一并请求 OHLC/昨收，供前端「当日价位快照」图使用；仅查最新价时五价合一易变成一条平线。
    优先从文件缓存读取，未命中或过期才调用接口。
    """
    from app.services.stock_file_cache import get_stock_file_cache
    fc = get_stock_file_cache()

    cached = fc.get(code, "quote")
    if cached and cached.get("data"):
        cached_data = cached["data"]
        if cached_data.get("success"):
            return cached_data

    extra = "今开 开盘 最高 最低 昨收 昨收盘价"
    if code.startswith(("6", "5", "9")):
        query = f"{code} 最新价 涨跌幅 涨跌额 {extra} 成交量 成交额 换手率"
    else:
        query = f"{code} 最新价 涨跌幅 涨跌额 {extra} 成交量 成交额 换手率"

    result = query_financial_data(query)
    if result.get("success"):
        fc.set(code, "quote", result)
    return result


def get_stock_financial(code: str, indicators: str = "净利润 营业收入 净资产收益率 每股收益") -> dict:
    """查询个股财务指标（文件缓存优先）"""
    from app.services.stock_file_cache import get_stock_file_cache
    fc = get_stock_file_cache()

    cached = fc.get(code, "financial")
    if cached and cached.get("data") and cached["data"].get("success"):
        return cached["data"]

    query = f"{code} {indicators}"
    result = query_financial_data(query)
    if result.get("success"):
        fc.set(code, "financial", result)
    return result


def get_stock_profile(code: str) -> dict:
    """查询公司概况（文件缓存优先）"""
    from app.services.stock_file_cache import get_stock_file_cache
    fc = get_stock_file_cache()

    cached = fc.get(code, "profile")
    if cached and cached.get("data") and cached["data"].get("success"):
        return cached["data"]

    query = f"{code} 公司简介 主营业务 成立时间 董事长 总股本"
    result = query_financial_data(query)
    if result.get("success"):
        fc.set(code, "profile", result)
    return result


def get_stock_holders(code: str) -> dict:
    """查询十大股东（文件缓存优先）"""
    from app.services.stock_file_cache import get_stock_file_cache
    fc = get_stock_file_cache()

    cached = fc.get(code, "holders")
    if cached and cached.get("data") and cached["data"].get("success"):
        return cached["data"]

    query = f"{code} 十大股东"
    result = query_financial_data(query)
    if result.get("success"):
        fc.set(code, "holders", result)
    return result


def get_index_quote(index_name: str = "沪深300") -> dict:
    """查询指数行情（附带 display_price / display_change_pct 供仪表盘稳定展示）"""
    # 避免「上证指数指数」重复；自然语言尽量简短明确
    query = f"{index_name} 最新点位 涨跌幅"
    base = query_financial_data(query)
    return _enrich_index_quote_result(base)


def get_sector_quote(sector_name: str) -> dict:
    """查询板块行情"""
    query = f"{sector_name}板块最新行情"
    return query_financial_data(query)
