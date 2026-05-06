"""
智能股票分析助手 — 模拟交易服务层

封装模拟交易操作（持仓查询、资金查询、委托下单、撤单等），供API路由层调用。
"""

import sys
from pathlib import Path
from typing import Optional

# 确保skills路径可导入
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # backend/app/services -> project root
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_MONI = _PROJECT_ROOT / "skills" / "模拟组合管理" / "mx-moni"

for p in [_AGENTS_DIR, _SKILLS_MONI, str(_PROJECT_ROOT)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import requests
from app.config import settings
from app.utils.mock_trading_normalize import extract_orders_dicts, normalize_mock_order_row

# API基础地址
MX_API_URL = "https://mkapi2.dfcfs.com/finskillshub"


def _make_request(endpoint: str, body: dict) -> dict:
    """发送模拟交易API请求

    Args:
        endpoint: API端点路径
        body: 请求体

    Returns:
        API响应JSON
    """
    headers = {
        "apikey": settings.MX_APIKEY,
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{MX_API_URL}{endpoint}",
        headers=headers,
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _check_api_ready() -> Optional[dict]:
    """检查API是否就绪，未就绪返回错误字典"""
    if not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here":
        return {"error": "MX_APIKEY 未配置"}
    return None


def get_positions() -> dict:
    """查询模拟持仓

    Returns:
        {
            "success": True/False,
            "positions": [{"code": str, "name": str, "quantity": int, ...}, ...],
            "total": int,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "positions": [],
        "total": 0,
        "error": None,
    }

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        raw = _make_request("/api/claw/mockTrading/positions", {"moneyUnit": 1})

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "查询持仓失败")
            return result

        data = raw.get("data", {})
        positions = data.get("positions", [])

        parsed = []
        for pos in (positions or []):
            parsed.append({
                "stock_code": pos.get("stockCode", ""),
                "stock_name": pos.get("stockName", ""),
                "quantity": pos.get("quantity", 0),
                "cost_price": pos.get("costPrice", 0),
                "current_price": pos.get("currentPrice", 0),
                "profit_loss": pos.get("profitLoss", 0),
                "profit_loss_rate": pos.get("profitLossRate", 0),
                "market_value": pos.get("marketValue", 0),
            })

        result["success"] = True
        result["positions"] = parsed
        result["total"] = len(parsed)
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def get_balance() -> dict:
    """查询模拟账户资金

    Returns:
        {
            "success": True/False,
            "balance": {...},
            "error": str or None
        }
    """
    result = {
        "success": False,
        "balance": {},
        "error": None,
    }

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        raw = _make_request("/api/claw/mockTrading/balance", {"moneyUnit": 1})

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "查询资金失败")
            return result

        data = raw.get("data", {})
        result["success"] = True
        result["balance"] = {
            "total_assets": data.get("totalAssets", 0),
            "available_balance": data.get("availBalance", 0),
            "frozen_balance": data.get("frozenBalance", 0),
            "market_value": data.get("marketValue", 0),
            "total_profit_loss": data.get("totalProfitLoss", 0),
        }
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def get_orders() -> dict:
    """查询委托记录

    Returns:
        {
            "success": True/False,
            "orders": [...],
            "total": int,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "orders": [],
        "total": 0,
        "error": None,
    }

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        raw = _make_request("/api/claw/mockTrading/orders", {
            "fltOrderDrt": 0,
            "fltOrderStatus": 0,
        })

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "查询委托失败")
            return result

        data = raw.get("data", {}) or {}
        # 妙想可能返回 list，或 { rows: [] }，或当日/历史分段字段
        orders = extract_orders_dicts(data)

        parsed = []
        for order in orders:
            if not isinstance(order, dict):
                continue
            # 统一解析字段名与枚举（数值买卖方向、委托状态等）
            parsed.append(normalize_mock_order_row(order))

        result["success"] = True
        result["orders"] = parsed
        result["total"] = len(parsed)
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def place_order(
    trade_type: str,
    stock_code: str,
    quantity: int,
    price: Optional[float] = None,
) -> dict:
    """模拟下单（买入/卖出）

    Args:
        trade_type: 交易类型 "buy" 或 "sell"
        stock_code: 6位股票代码
        quantity: 委托数量（必须为100的整数倍）
        price: 委托价格（None表示市价委托）

    Returns:
        {
            "success": True/False,
            "order_id": str,
            "message": str,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "order_id": "",
        "message": "",
        "error": None,
    }

    # 参数校验
    if trade_type not in ("buy", "sell"):
        result["error"] = "交易类型无效，请使用 buy 或 sell"
        return result

    if not stock_code or len(str(stock_code)) < 6:
        result["error"] = "请输入有效的6位股票代码"
        return result

    if quantity <= 0:
        result["error"] = "委托数量必须大于0"
        return result

    if quantity % 100 != 0:
        result["error"] = "A股交易数量必须为100股的整数倍"
        return result

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        body = {
            "type": trade_type,
            "stockCode": str(stock_code),
            "quantity": int(quantity),
            "useMarketPrice": price is None,
        }
        if price is not None:
            body["price"] = float(price)

        raw = _make_request("/api/claw/mockTrading/trade", body)

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "下单失败")
            return result

        data = raw.get("data", {})
        order_id = data.get("orderId", "")

        result["success"] = True
        result["order_id"] = order_id
        direction_cn = "买入" if trade_type == "buy" else "卖出"
        price_info = f"@{price}元" if price else "市价"
        result["message"] = f"{direction_cn}委托已提交: {stock_code} {quantity}股 {price_info}"
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def cancel_order(order_id: str, stock_code: str = "") -> dict:
    """撤单

    Args:
        order_id: 委托编号
        stock_code: 股票代码（可选）

    Returns:
        {
            "success": True/False,
            "message": str,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    if not order_id:
        result["error"] = "请提供委托编号"
        return result

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        body = {
            "type": "order",
            "orderId": str(order_id),
        }
        if stock_code:
            body["stockCode"] = str(stock_code)

        raw = _make_request("/api/claw/mockTrading/cancel", body)

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "撤单失败")
            return result

        result["success"] = True
        result["message"] = f"委托 {order_id} 已撤销"
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def cancel_all_orders() -> dict:
    """一键撤单（撤销所有未成交委托）

    Returns:
        {
            "success": True/False,
            "message": str,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    api_error = _check_api_ready()
    if api_error:
        result["error"] = api_error["error"]
        return result

    try:
        raw = _make_request("/api/claw/mockTrading/cancel", {"type": "all"})

        if not raw.get("success") and str(raw.get("code")) != "200":
            result["error"] = raw.get("message", "一键撤单失败")
            return result

        result["success"] = True
        result["message"] = "所有未成交委托已撤销"
        return result

    except Exception as e:
        result["error"] = str(e)
        return result
