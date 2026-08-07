"""
智能股票分析助手 — 模拟交易API路由

提供模拟持仓查询、资金查询、委托下单、撤单等接口。
"""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from app.services import simulation_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/simulation", tags=["模拟交易"])


class PlaceOrderRequest(BaseModel):
    """下单请求"""
    trade_type: str = Field(..., description="交易类型: buy(买入) / sell(卖出)", pattern="^(buy|sell)$")
    stock_code: str = Field(..., description="6位股票代码", min_length=6, max_length=6)
    quantity: int = Field(..., description="委托数量（100的整数倍）", gt=0)
    price: Optional[float] = Field(default=None, description="委托价格（不填则为市价委托）")


class CancelOrderRequest(BaseModel):
    """撤单请求"""
    order_id: str = Field(..., description="委托编号", min_length=1)
    stock_code: str = Field(default="", description="股票代码（可选）")


@router.get("/portfolio")
async def get_portfolio():
    """查询模拟持仓

    返回当前模拟账户下所有持仓股票及其盈亏信息。
    """
    result = simulation_service.get_positions()
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询持仓失败"))

    return success_response(
        data={
            "positions": result["positions"],
            "total": result["total"],
        },
        message=f"共 {result['total']} 只持仓股票",
    )


@router.get("/funds")
async def get_funds():
    """查询模拟账户资金

    返回总资产、可用资金、冻结资金、持仓市值、累计盈亏等信息。
    """
    result = simulation_service.get_balance()
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询资金失败"))

    return success_response(
        data=result["balance"],
        message="资金查询成功",
    )


@router.get("/orders")
async def get_orders():
    """查询委托记录

    返回历史委托订单列表（包含已成交、未成交、已撤销等状态）。
    """
    result = simulation_service.get_orders()
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询委托失败"))

    return success_response(
        data={
            "orders": result["orders"],
            "total": result["total"],
        },
        message=f"共 {result['total']} 条委托记录",
    )


@router.post("/order")
async def place_order(body: PlaceOrderRequest):
    """模拟下单（买入/卖出）

    提交模拟交易委托，支持限价委托和市价委托。

    - **trade_type**: buy=买入, sell=卖出
    - **stock_code**: 6位股票代码，如 600519
    - **quantity**: 委托数量，必须为100的整数倍
    - **price**: 委托价格（不填=市价委托）
    """
    result = simulation_service.place_order(
        trade_type=body.trade_type,
        stock_code=body.stock_code,
        quantity=body.quantity,
        price=body.price,
    )
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "下单失败"))

    return success_response(
        data={
            "order_id": result["order_id"],
            "trade_type": body.trade_type,
            "stock_code": body.stock_code,
            "quantity": body.quantity,
            "price": body.price,
        },
        message=result["message"],
    )


@router.delete("/order/{order_id}")
async def cancel_order(
    order_id: str,
    stock_code: str = Query(default="", description="股票代码（可选）"),
):
    """撤销指定委托

    根据委托编号撤销未成交的委托订单。

    - **order_id**: 委托编号（如 260854300000078983）
    - **stock_code**: 股票代码（可选）
    """
    result = simulation_service.cancel_order(order_id, stock_code)
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "撤单失败"))

    return success_response(data={"order_id": order_id}, message=result["message"])


@router.post("/cancel-all")
async def cancel_all_orders():
    """一键撤单

    撤销当前账户下所有未成交的委托订单。
    """
    result = simulation_service.cancel_all_orders()
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "一键撤单失败"))

    return success_response(data={}, message=result["message"])
