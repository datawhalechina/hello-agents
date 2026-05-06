"""
智能股票分析助手 — 行情数据API路由

提供个股行情、指数行情、板块行情查询接口。
"""

from fastapi import APIRouter, Query
from app.services import market_service
from app.utils.mx_http import mx_result_to_http
from app.utils.response import error_response

router = APIRouter(prefix="/market", tags=["行情数据"])


@router.get("/quote/{code}")
async def get_stock_quote(code: str):
    """获取个股实时行情

    - **code**: 6位股票代码，如 600519（贵州茅台）、000001（平安银行）
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = market_service.get_stock_quote(code)
    return mx_result_to_http(result)


@router.get("/index")
async def get_index_quote(name: str = Query(default="沪深300", description="指数名称")):
    """获取指数行情

    - **name**: 指数名称，如 沪深300、上证指数、创业板指
    """
    result = market_service.get_index_quote(name)
    return mx_result_to_http(result)


@router.get("/sector/{name}")
async def get_sector_quote(name: str):
    """获取板块行情

    - **name**: 板块名称，如 白酒、新能源、半导体
    """
    if not name:
        return error_response(code=400, message="请输入板块名称")

    result = market_service.get_sector_quote(name)
    return mx_result_to_http(result)
