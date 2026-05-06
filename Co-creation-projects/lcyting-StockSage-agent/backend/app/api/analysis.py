"""
智能股票分析助手 — 分析报告API路由

提供个股深度分析报告生成、查询、历史列表接口。
"""

from fastapi import APIRouter, Query
from app.services import analysis_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/analysis", tags=["分析报告"])


@router.post("/report/{code}")
async def generate_report(
    code: str,
    user_id: str = Query(default="default", description="用户标识"),
    report_type: str = Query(default="full", description="报告类型: full/quick"),
):
    """生成个股深度分析报告

    收集行情数据、财务数据、公司概况、舆情信息，生成综合分析报告并持久化。

    - **code**: 6位股票代码，如 600519（贵州茅台）、000001（平安银行）
    - **user_id**: 用户标识，默认"default"
    - **report_type**: 报告类型，full=完整分析, quick=快速概览
    """
    if not code or len(code) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = await analysis_service.generate_analysis_report(code, user_id, report_type)
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "报告生成失败"))

    return success_response(
        data={
            "report": result["report"],
            "data_collected": result["data_collected"],
        },
        message="分析报告生成成功",
    )


@router.get("/report/{report_id}")
async def get_report(report_id: int):
    """获取指定分析报告

    - **report_id**: 报告ID（由生成报告接口返回）
    """
    if report_id <= 0:
        return error_response(code=400, message="无效的报告ID")

    result = await analysis_service.get_report(report_id)
    if not result["success"]:
        return error_response(code=404, message=result.get("error", "报告不存在"))

    return success_response(data=result["report"])


@router.get("/reports")
async def list_reports(
    user_id: str = Query(default="default", description="用户标识"),
    limit: int = Query(default=20, ge=1, le=100, description="最大返回数量"),
):
    """获取分析报告历史列表

    - **user_id**: 用户标识，默认"default"
    - **limit**: 最大返回数量，1-100，默认20
    """
    result = await analysis_service.get_user_reports(user_id, limit)
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询失败"))

    return success_response(
        data={
            "reports": result["reports"],
            "total": result["total"],
        },
        message=f"共 {result['total']} 份报告"
    )
