# backend/agent/nodes/report_generator.py
import json
from openai import AsyncOpenAI

from agent.state import StockAnalysisState
from app.config import settings


def _build_prompt(state: StockAnalysisState) -> str:
    realtime = state.get("realtime_data") or {}
    kline = state.get("kline_data") or []
    fundamental = state.get("fundamental_data") or {}
    error_info = state.get("error")

    kline_summary = kline[-3:] if kline else []
    error_section = f"## 数据缺失说明\n{error_info}" if error_info else ""

    # 三维分析结果
    sentiment_score = state.get("sentiment_score") or 0.0
    sentiment_label = state.get("sentiment_label") or "neutral"
    sentiment_reason = state.get("sentiment_reason") or "暂无"
    technical_score = state.get("technical_score") or 50.0
    technical_signals = state.get("technical_signals") or []
    fundamental_score = state.get("fundamental_score") or 50.0
    fundamental_signals = state.get("fundamental_signals") or []

    prompt = f"""
你是一位专业的股票投资分析师，请根据以下数据对股票 {state['symbol']}（{state['market']}）进行综合分析。

## 实时行情
{json.dumps(realtime, ensure_ascii=False, indent=2)}

## 近期 K 线（最近 5 日）
{json.dumps(kline_summary, ensure_ascii=False, indent=2)}

## 基本面数据
{json.dumps(fundamental, ensure_ascii=False, indent=2)}

## 三维分析评分
- 情感评分：{sentiment_score:.2f}（{sentiment_label}）| {sentiment_reason}
- 技术面评分：{technical_score:.1f}/100 | 信号：{', '.join(technical_signals[:3])}
- 基本面评分：{fundamental_score:.1f}/100 | {', '.join(fundamental_signals[:2])}

{error_section}

请按以下结构输出分析报告：

1. **行情概述**：当前价格、涨跌幅、成交量分析
2. **技术面分析**：基于评分和信号的趋势判断
3. **基本面分析**：估值水平和成长性评估
4. **情感面分析**：市场情绪对股价的影响
5. **综合评分**：三维加权综合评分（0-100）及风险等级（low/medium/high）
6. **投资建议**：具体建议及主要风险点

注意：本报告仅供参考，不构成投资建议。
""".strip()

    return prompt


async def report_generator_node(state: StockAnalysisState) -> StockAnalysisState:
    """
    调用 Qwen API 生成投资分析报告。
    mock 模式下返回固定报告，无需真实 API key。
    """
    if settings.use_mock_data:
        return {
            **state,
            "final_report": (
                f"## {state['symbol']} 模拟分析报告\n\n"
                "1. **行情概述**：当前价格 1800.0，涨幅 1.5%，成交量正常。\n"
                "2. **技术面分析**：近期呈震荡上行趋势，短期支撑位 1775。\n"
                "3. **基本面分析**：PE 28.5，PB 9.2，估值处于合理区间。\n"
                "4. **综合评分**：技术面 72，基本面 78，风险等级 low。\n"
                "5. **投资建议**：基本面稳健，可关注回调买入机会，注意仓位控制。\n\n"
                "> 本报告仅供参考，不构成投资建议。"
            ),
            "risk_level": "low",
        }

    client = AsyncOpenAI(
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.qwen_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的股票投资分析师，擅长 A 股和美股的多维度综合分析。回答简洁专业，重点突出。",
                },
                {
                    "role": "user",
                    "content": _build_prompt(state),
                },
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        report = response.choices[0].message.content

        # 简单判断风险等级（Phase 2 会做更精细的评分）
        risk_level = "medium"
        if "低风险" in report or "risk_level: low" in report:
            risk_level = "low"
        elif "高风险" in report or "risk_level: high" in report:
            risk_level = "high"

        return {**state, "final_report": report, "risk_level": risk_level}

    except Exception as e:
        return {
            **state,
            "final_report": f"报告生成失败：{e}",
            "risk_level": "medium",
            "error": str(e),
        }