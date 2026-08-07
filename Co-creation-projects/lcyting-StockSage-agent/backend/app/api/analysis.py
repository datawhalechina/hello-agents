"""
智能股票分析助手 — 分析报告API路由（兼容层）

旧版 POST 生成报告已移除；列表与详情优先走分析历史表，其次兼容旧版 AnalysisReport 表。
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services import analysis_service, history_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/analysis", tags=["分析报告"])


@router.post("/report/{code}")
async def generate_report_removed(
    code: str,
    user_id: str = Query(default="default", description="用户标识"),
    report_type: str = Query(default="full", description="报告类型: full/quick"),
):
    """已废弃：请使用 AI 对话助手或个股页 AI 分析 Tab。"""
    return JSONResponse(
        status_code=410,
        content=error_response(
            code=410,
            message=(
                "该接口已移除。请使用 POST /api/v1/chat/stream（AI 对话助手），"
                "或个股分析页的舆情 / 数据 / 巴菲特流式分析。"
            ),
            data={"replacement_chat": "/api/v1/chat/stream", "stock_code": code},
        ),
    )


@router.get("/report/{report_id}")
async def get_report(report_id: int):
    """获取指定记录：优先 analysis_history，其次旧版 analysis_reports 表。"""
    if report_id <= 0:
        return error_response(code=400, message="无效的报告ID")

    hist = await history_service.get_history_detail(report_id)
    if hist.get("success"):
        rec = hist["record"]
        return success_response(
            data={
                "report": rec,
                "source": "history",
            },
            message="查询成功",
        )

    legacy = await analysis_service.get_report(report_id)
    if legacy.get("success"):
        return success_response(
            data={
                "report": legacy["report"],
                "source": "legacy_analysis_report",
            },
            message="查询成功（旧版报告表）",
        )

    return error_response(code=404, message=hist.get("error") or legacy.get("error") or "记录不存在")


@router.get("/reports")
async def list_reports(
    user_id: str = Query(default="default", description="用户标识"),
    limit: int = Query(default=20, ge=1, le=100, description="最大返回数量"),
):
    """分析报告历史列表 — 对应 analysis_history（各 AI 分析类型）。"""
    result = await history_service.get_history_list(
        analysis_type=None, user_id=user_id, limit=limit
    )
    if not result["success"]:
        return error_response(code=500, message=result.get("error", "查询失败"))

    items = result["items"]
    return success_response(
        data={
            "reports": items,
            "items": items,
            "total": result["total"],
        },
        message=f"共 {result['total']} 条记录",
    )
