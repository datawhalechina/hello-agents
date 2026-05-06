"""
智能股票分析助手 — 财务数据API路由

提供财务指标、公司概况、股东信息查询接口。
"""

from fastapi import APIRouter, Query
from app.services import market_service
from app.utils.mx_http import mx_result_to_http
from app.utils.response import error_response

router = APIRouter(prefix="/financial", tags=["财务数据"])


@router.get("/indicators/{code}")
async def get_financial_indicators(
    code: str,
    indicators: str = Query(default="净利润 营业收入 净资产收益率 每股收益", description="需要的财务指标"),
):
    """获取个股财务指标

    - **code**: 6位股票代码
    - **indicators**: 财务指标描述（自然语言），如 "净利润 营业收入 ROE"
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = market_service.get_stock_financial(code, indicators)
    return mx_result_to_http(result)


@router.get("/profile/{code}")
async def get_company_profile(code: str):
    """获取公司概况

    - **code**: 6位股票代码
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = market_service.get_stock_profile(code)
    return mx_result_to_http(result)


@router.get("/holders/{code}")
async def get_top_holders(code: str):
    """获取十大股东信息

    - **code**: 6位股票代码
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = market_service.get_stock_holders(code)
    return mx_result_to_http(result)
