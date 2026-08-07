"""
智能股票分析助手 — 智能选股API路由

提供条件选股、可用选股条件查询接口。
"""

from fastapi import APIRouter, Query
from app.services import screener_service
from app.utils.mx_http import mx_result_to_http
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/screener", tags=["智能选股"])


@router.get("/conditions")
async def get_screener_conditions():
    """获取可用的选股条件参考

    返回选股维度分类和示例条件，供前端展示和用户参考。
    """
    result = screener_service.get_available_conditions()
    if not result.get("success"):
        return error_response(code=500, message=result.get("error", "获取条件失败"))
    return success_response(data=result)


@router.post("/search")
async def screen_stocks(
    query: str = Query(..., description="自然语言选股条件"),
):
    """条件选股

    根据自然语言描述的选股条件，筛选符合条件的股票。

    - **query**: 自然语言选股条件，如：
      - "市盈率小于20且ROE大于15%的A股"
      - "新能源板块涨幅大于1%的股票"
      - "沪深300成分股中分红率最高的10只"
      - "价格小于20元 市盈率小于20 涨幅大于1%"
    """
    if not query or not query.strip():
        return error_response(code=400, message="请输入选股条件")

    result = screener_service.screen_stocks(query.strip())
    return mx_result_to_http(result)
