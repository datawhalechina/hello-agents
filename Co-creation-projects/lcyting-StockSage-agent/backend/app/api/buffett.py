"""
智能股票分析助手 — 巴菲特投资评估API路由

提供巴菲特价值投资框架查询、投资评估接口。
"""

import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import buffett_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/buffett", tags=["巴菲特投资评估"])


class BuffettEvaluateRequest(BaseModel):
    """巴菲特投资评估请求"""
    stock_code: str = Field(..., description="6位股票代码", min_length=4, max_length=10)
    stock_name: str = Field(default="", description="股票名称（可选）")
    include_market: bool = Field(default=True, description="是否包含行情数据")
    include_financial: bool = Field(default=True, description="是否包含财务数据")


@router.get("/framework")
async def get_buffett_framework():
    """获取巴菲特投资评估框架

    返回完整的巴菲特价值投资思维体系，包括：
    - 8问快速筛选清单
    - 护城河分析五类型
    - 管理层评估三维度
    - 财务指标模板（ROIC、所有者收益、现金转化率）
    - 估值方法与安全边际
    - 风险评估分类
    - 卖出四条标准
    """
    result = buffett_service.get_buffett_framework()
    return success_response(
        data={
            "framework": result["framework"],
            "description": result["description"],
        },
        message="巴菲特投资评估框架已就绪",
    )


@router.post("/evaluate")
async def evaluate_stock(body: BuffettEvaluateRequest):
    """使用巴菲特投资框架评估股票

    构建巴菲特风格的价值投资评估上下文，返回结构化评估模板和参考框架。

    - **stock_code**: 6位股票代码，如 600519（贵州茅台）
    - **stock_name**: 股票名称（可选，用于报告标题）
    - **include_market**: 是否尝试获取行情数据
    - **include_financial**: 是否尝试获取财务数据
    """
    if not body.stock_code or len(body.stock_code.strip()) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    # 构建数据上下文（尝试收集数据，不因单个数据失败而中断）
    data_context = {}
    errors = []

    if body.include_market:
        try:
            from app.services import market_service
            market_result = market_service.get_stock_quote(body.stock_code.strip())
            if market_result.get("success"):
                data_context["market"] = market_result
        except Exception as e:
            errors.append(f"行情数据获取失败: {e}")

    if body.include_financial:
        try:
            from app.services import market_service
            financial_result = market_service.get_stock_financial(body.stock_code.strip())
            if financial_result.get("success"):
                data_context["financial"] = financial_result
        except Exception as e:
            errors.append(f"财务数据获取失败: {e}")

    # 执行巴菲特评估
    result = buffett_service.evaluate_with_buffett(
        stock_code=body.stock_code.strip(),
        stock_name=body.stock_name.strip() or "",
        data_context=data_context,
    )

    if not result["success"]:
        return error_response(code=500, message=result.get("error", "评估失败"))

    data_warnings = ""
    if errors:
        data_warnings = "; ".join(errors)

    slim_ctx = buffett_service.slim_evaluation_context_for_api(result["evaluation_context"])

    return success_response(
        data={
            "stock_code": result["stock_code"],
            "stock_name": result["stock_name"],
            "evaluation_context": slim_ctx,
            "report_template": result["report_template"],
            "data_warnings": data_warnings or None,
        },
        message=f"已构建 {result['stock_name'] or result['stock_code']} 的巴菲特评估上下文",
    )


@router.post("/report/generate-ai")
async def generate_ai_buffett_report(body: BuffettEvaluateRequest):
    """一键生成巴菲特价值投资评估报告（LLM，同步 JSON）"""
    if not body.stock_code or len(body.stock_code.strip()) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    result = await asyncio.to_thread(
        buffett_service.generate_buffett_ai_report,
        body.stock_code.strip(),
        (body.stock_name or "").strip(),
    )

    if not result.get("success"):
        return error_response(
            code=503,
            message=result.get("error") or "AI 评估报告生成失败",
            data={"stock_code": body.stock_code.strip()},
        )

    return success_response(
        data={
            "stock_code": body.stock_code.strip(),
            "stock_name": (body.stock_name or "").strip(),
            "report_markdown": result["report_markdown"],
        },
        message="巴菲特 AI 评估报告已生成",
    )


def _buffett_ai_report_ndjson_bytes(stock_code: str, stock_name: str):
    for evt in buffett_service.iter_buffett_ai_report_events(stock_code, stock_name):
        line = json.dumps(evt, ensure_ascii=False) + "\n"
        yield line.encode("utf-8")


@router.post("/report/generate-ai/stream")
async def stream_ai_buffett_report(body: BuffettEvaluateRequest):
    """流式生成巴菲特 AI 评估报告（NDJSON：meta → delta → … → done）"""
    if not body.stock_code or len(body.stock_code.strip()) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    return StreamingResponse(
        _buffett_ai_report_ndjson_bytes(
            body.stock_code.strip(),
            (body.stock_name or "").strip(),
        ),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/evaluate/stream")
async def stream_buffett_evaluate(body: BuffettEvaluateRequest):
    """实现方案约定路径 POST /api/v1/buffett/evaluate/stream，等价于 report/generate-ai/stream"""
    if not body.stock_code or len(body.stock_code.strip()) < 4:
        return error_response(code=400, message="请输入有效的股票代码")

    return StreamingResponse(
        _buffett_ai_report_ndjson_bytes(
            body.stock_code.strip(),
            (body.stock_name or "").strip(),
        ),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/report/template")
async def get_report_template(
    code: str = Query(..., description="股票代码", min_length=4),
    name: str = Query(default="", description="股票名称"),
):
    """获取巴菲特风格评估报告模板

    返回包含所有必填章节的Markdown格式报告模板，可直接用于填写分析结果。

    - **code**: 6位股票代码
    - **name**: 股票名称（可选）
    """
    template = buffett_service._build_buffett_report_template(code, name)
    return success_response(
        data={"template": template, "stock_code": code, "stock_name": name},
        message="报告模板已生成",
    )


@router.get("/reference/{ref_name}")
async def get_reference_file(
    ref_name: str,
):
    """获取巴菲特投资思维参考文件内容

    可获取的参考文件：
    - 01-thinking-frameworks (思维框架)
    - 02-investment-philosophy (投资哲学)
    - 03-business-moat (企业护城河)
    - 04-management-governance (管理层治理)
    - 05-financial-metrics (财务指标)
    - 06-valuation-capital (估值与资本)
    - 07-risk-behavior (风险与行为)
    - 08-industry-playbooks (行业手册)

    - **ref_name**: 参考文件名，如 "03-business-moat"
    """
    content = buffett_service.load_buffett_reference(ref_name)
    if content is None:
        return error_response(code=404, message=f"参考文件 '{ref_name}' 不存在或无法读取")

    # 截取前5000字符返回
    preview = content[:5000]
    is_truncated = len(content) > 5000

    return success_response(
        data={
            "ref_name": ref_name,
            "content": preview,
            "full_length": len(content),
            "truncated": is_truncated,
        },
        message=f"参考文件 {ref_name}（{'预览前5000字符' if is_truncated else '完整内容'}）",
    )
