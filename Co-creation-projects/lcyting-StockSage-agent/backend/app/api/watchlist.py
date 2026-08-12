"""
智能股票分析助手 — 自选股管理API路由

提供自选股查询、添加、删除接口。
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from app.services import watchlist_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/watchlist", tags=["自选股管理"])


class WatchlistAddRequest(BaseModel):
    """添加自选股请求"""
    stock: str = Field(..., description="股票名称或代码，如'贵州茅台'或'600519'", min_length=1)


class WatchlistDeleteRequest(BaseModel):
    """删除自选股请求"""
    stock: str = Field(..., description="股票名称或代码，如'贵州茅台'或'600519'", min_length=1)


@router.get("/")
async def get_watchlist():
    """查询自选股列表

    返回当前账户下的所有自选股及其行情数据。
    """
    result = watchlist_service.get_watchlist()
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询自选股失败"))

    return success_response(
        data={
            "stocks": result["stocks"],
            "total": result["total"],
        },
        message=f"共 {result['total']} 只自选股",
    )


@router.post("/")
async def add_watchlist(body: WatchlistAddRequest):
    """添加自选股

    将指定股票添加到自选股列表。

    - **stock**: 股票名称或6位代码，如'贵州茅台'、'600519'
    """
    if not body.stock or not body.stock.strip():
        return error_response(code=400, message="请输入股票名称或代码")

    result = watchlist_service.add_to_watchlist(body.stock.strip())
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "添加自选股失败"))

    return success_response(data=result, message=result["message"])


@router.delete("/{stock}")
async def delete_watchlist(stock: str):
    """删除自选股

    将指定股票从自选股列表中移除。

    - **stock**: 股票名称或6位代码，如'贵州茅台'、'600519'
    """
    if not stock or not stock.strip():
        return error_response(code=400, message="请输入股票名称或代码")

    result = watchlist_service.delete_from_watchlist(stock.strip())
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "删除自选股失败"))

    return success_response(data=result, message=result["message"])
