"""
妙想模拟交易 — 委托列表字段规范化

上游 `/api/claw/mockTrading/orders` 返回的字段名与取值在不同版本间可能不一致：
- 买卖方向可能是数值（如 1=买入、2=卖出）而非字符串 buy/sell
- 委托状态多为数值枚举，需映射为前端可用的 pending/done 等
- 代码、名称、委托号、时间等可能存在 snake_case 或其它别名

此处集中做兼容解析，供 simulation_service 与 Agent 工具共用。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def extract_orders_dicts(data: Any) -> list[dict[str, Any]]:
    """从妙想 data 中取出委托对象列表（兼容 list、或 { rows/list/... } 包裹）。"""
    if not isinstance(data, Mapping):
        return []

    def coerce_dict_list(raw: Any) -> list[dict[str, Any]]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
        if isinstance(raw, dict):
            for inner_key in ("rows", "records", "list", "items", "data"):
                inner = raw.get(inner_key)
                if isinstance(inner, list):
                    return [x for x in inner if isinstance(x, dict)]
        return []

    # 单一列表字段优先（避免把多个片段重复拼接）
    for key in ("orders", "orderList", "list", "entrustList"):
        chunk = coerce_dict_list(data.get(key))
        if chunk:
            return chunk

    # 当日 + 历史分段返回时合并（仅当顶层未给出统一 orders）
    merged: list[dict[str, Any]] = []
    for key in ("todayOrders", "today_order_list", "historyOrders", "hisOrders"):
        merged.extend(coerce_dict_list(data.get(key)))
    return merged


def _first(d: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    """从左到右取第一个非空值（None / 空字符串跳过）。"""
    for k in keys:
        if k not in d:
            continue
        v = d[k]
        if v is None or v == "":
            continue
        return v
    return None


def _nested_stock(order: Mapping[str, Any]) -> Mapping[str, Any]:
    """部分响应把证券信息放在子对象里。"""
    for k in ("stock", "security", "stockInfo"):
        sub = order.get(k)
        if isinstance(sub, Mapping):
            return sub
    return {}


def parse_trade_type(order: Mapping[str, Any]) -> str:
    """解析为 'buy' 或 'sell'（妙想常见：数值 1=买入，2=卖出）。"""
    # 关键：不能用「第一个非空字段」—— tradeType/trade_type 常为委托类别(如 5)，
    # 真正的买卖方向在 orderDrt/orderBs 等字段，必须逐个尝试直到解析成功。
    dir_keys = (
        "orderDrt",
        "orderBs",
        "orderDirection",
        "bsFlag",
        "bsType",
        "entrustBs",
        "mmlx",
        "direction",
        "side",
        "tradeType",
        "trade_type",
    )
    nested = _nested_stock(order)

    def norm(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            iv = int(val)
            # 东方财富系常见：1 买入，2 卖出
            if iv == 1:
                return "buy"
            if iv == 2:
                return "sell"
            return None
        s = str(val).strip().lower()
        if s in ("buy", "b", "1", "买入", "买"):
            return "buy"
        if s in ("sell", "s", "2", "卖出", "卖"):
            return "sell"
        return None

    for src in (order, nested):
        for k in dir_keys:
            if k not in src:
                continue
            val = src[k]
            if val is None or val == "":
                continue
            parsed = norm(val)
            if parsed:
                return parsed

    # type：部分接口表示买卖；也可能是限价/市价等业务类型，故仅在可识别时采用
    for src in (order, nested):
        t_raw = src.get("type")
        parsed_t = norm(t_raw)
        if parsed_t:
            return parsed_t

    return ""


def parse_order_status(order: Mapping[str, Any]) -> tuple[str, str]:
    """
    返回 (canonical_status, chinese_label)。

    canonical 供前端撤单逻辑使用：pending / done / part_deal / canceled / unknown
    """
    nested = _nested_stock(order)
    status_keys = (
        "status",
        "order_status",
        "orderStatus",
        "entrustStatus",
        "wtStatus",
        "dealStatus",
    )

    def to_canonical_and_label(val: Any) -> tuple[str, str]:
        if val is None:
            return "unknown", "未知"
        if isinstance(val, str):
            sl = val.strip().lower()
            known = {
                "pending": ("pending", "未成交"),
                "unfilled": ("pending", "未成交"),
                "open": ("pending", "未成交"),
                "done": ("done", "已成交"),
                "filled": ("done", "已成交"),
                "success": ("done", "已成交"),
                "part_deal": ("part_deal", "部分成交"),
                "partial": ("part_deal", "部分成交"),
                "canceled": ("canceled", "已撤销"),
                "cancelled": ("canceled", "已撤销"),
                "withdrawn": ("canceled", "已撤销"),
            }
            if sl in known:
                return known[sl]
            # 已是中文等情况：当作未知但保留原文展示
            if sl.isdigit():
                return to_canonical_and_label(int(sl))
            return "unknown", str(val)

        try:
            iv = int(val)
        except (TypeError, ValueError):
            return "unknown", str(val)

        # 常见券商委托状态码（保守映射，未覆盖的显示「状态{n}」）
        mapping: dict[int, tuple[str, str]] = {
            0: ("pending", "待报/待成交"),
            1: ("pending", "未成交"),
            2: ("part_deal", "部分成交"),
            3: ("done", "已成交"),
            4: ("part_deal", "部成部撤"),
            5: ("canceled", "已撤销"),
            6: ("canceled", "已撤"),
            7: ("done", "成交"),
            8: ("canceled", "废单"),
        }
        if iv in mapping:
            return mapping[iv]
        return "unknown", f"状态{iv}"

    for src in (order, nested):
        for k in status_keys:
            if k not in src:
                continue
            val = src[k]
            if val is None or val == "":
                continue
            return to_canonical_and_label(val)

    return to_canonical_and_label(None)


def normalize_mock_order_row(order: Mapping[str, Any]) -> dict[str, Any]:
    """将单条原始委托转为前端/路由使用的统一结构。"""
    nested = _nested_stock(order)

    order_id = _first(
        order,
        (
            "orderId",
            "order_id",
            "orderNo",
            "orderNO",
            "wtOrderId",
            "entrustId",
            "wth",
            "wtbh",
            "contractId",
            "id",
        ),
    )
    stock_code = _first(
        order,
        ("stockCode", "stock_code", "securityCode", "zqdm", "scode", "code", "stockcode"),
    )
    if stock_code is None:
        stock_code = _first(nested, ("stockCode", "stock_code", "securityCode", "zqdm", "code"))

    stock_name = _first(order, ("stockName", "stock_name", "name", "sname", "securityName"))
    if stock_name is None:
        stock_name = _first(nested, ("stockName", "stock_name", "name"))

    price_raw = _first(
        order,
        ("price", "wtjg", "orderPrice", "order_price", "entrustPrice", "limitPrice", "wtPrice"),
    )
    try:
        price = float(price_raw) if price_raw is not None else 0.0
    except (TypeError, ValueError):
        price = 0.0

    qty_raw = _first(
        order,
        (
            "quantity",
            "wtVolume",
            "wtVol",
            "wtvol",
            "orderQty",
            "order_qty",
            "orderVolume",
            "vol",
            "volume",
            "stockNum",
            "entrustAmount",
        ),
    )
    try:
        quantity = int(qty_raw) if qty_raw is not None else 0
    except (TypeError, ValueError):
        quantity = 0

    create_time = _first(
        order,
        (
            "createTime",
            "create_time",
            "orderTime",
            "order_time",
            "entrustTime",
            "reportTime",
            "tradeTime",
            "wtTime",
            "report_time",
        ),
    )
    if create_time is None:
        create_time = _first(nested, ("createTime", "create_time"))

    trade_type = parse_trade_type(order)
    status, status_text = parse_order_status(order)

    return {
        "order_id": str(order_id) if order_id is not None else "",
        "stock_code": str(stock_code) if stock_code is not None else "",
        "stock_name": str(stock_name) if stock_name is not None else "",
        "trade_type": trade_type,
        "price": price,
        "quantity": quantity,
        "status": status,
        "status_text": status_text,
        "create_time": str(create_time) if create_time is not None else "",
    }
