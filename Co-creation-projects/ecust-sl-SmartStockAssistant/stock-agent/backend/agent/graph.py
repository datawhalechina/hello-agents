# backend/agent/graph.py
from langgraph.graph import StateGraph, END

from agent.state import StockAnalysisState, make_initial_state
from agent.nodes.data_collector import data_collector_node
from agent.nodes.sentiment import sentiment_node
from agent.nodes.technical import technical_node
from agent.nodes.fundamental import fundamental_node
from agent.nodes.report_generator import report_generator_node


# ── 路由函数 ──────────────────────────────────────────────────────────

def _route_after_collection(state: StockAnalysisState) -> str:
    if (
        state["realtime_data"] is None
        and state["kline_data"] is None
        and state["fundamental_data"] is None
    ):
        return "end"
    return "analyze"


def _route_after_analysis(state: StockAnalysisState) -> str:
    sentiment = state.get("sentiment_score") or 0.0
    technical = state.get("technical_score") or 50.0

    if sentiment < -0.7 and technical < 25:
        return "risk_warning"
    return "report"


async def aggregator_node(state: StockAnalysisState) -> StockAnalysisState:
    """汇聚节点：等三路并行（sentiment/technical/fundamental）完成后再走 report。"""
    return state


async def dispatcher_node(state: StockAnalysisState) -> StockAnalysisState:
    """分发节点：data_collector 之后用，触发三路并行分析。本身是 no-op。"""
    return state


# ── 风险预警节点 ──────────────────────────────────────────────────────

def risk_warning_node(state: StockAnalysisState) -> StockAnalysisState:
    symbol = state["symbol"]
    sentiment = state.get("sentiment_score") or 0.0
    technical = state.get("technical_score") or 0.0
    fundamental = state.get("fundamental_score") or 50.0

    report = (
        f"## ⚠️ {symbol} 风险预警报告\n\n"
        f"**当前评分**：情感 {sentiment:.2f} | 技术面 {technical:.1f} | 基本面 {fundamental:.1f}\n\n"
        "**预警原因**：市场情绪极度悲观，技术面处于弱势区间，"
        "短期风险较高，建议暂时回避或严格控制仓位。\n\n"
        "**主要风险点**：\n"
        f"- 情感评分 {sentiment:.2f}（阈值 -0.7），市场恐慌情绪蔓延\n"
        f"- 技术评分 {technical:.1f}（阈值 25），技术形态持续走弱\n\n"
        "> 本报告仅供参考，不构成投资建议。"
    )

    return {**state, "final_report": report, "risk_level": "high"}


# ── 构建图 ────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(StockAnalysisState)

    # 注册节点
    builder.add_node("data_collector",   data_collector_node)
    builder.add_node("dispatcher",       dispatcher_node)
    builder.add_node("sentiment",        sentiment_node)
    builder.add_node("technical",        technical_node)
    builder.add_node("fundamental",      fundamental_node)
    builder.add_node("aggregator",       aggregator_node)
    builder.add_node("risk_warning",     risk_warning_node)
    builder.add_node("report_generator", report_generator_node)

    # 入口
    builder.set_entry_point("data_collector")

    # 数据采集 → 数据齐全则进入 dispatcher；否则直接结束
    builder.add_conditional_edges(
        "data_collector",
        _route_after_collection,
        {"analyze": "dispatcher", "end": END},
    )

    # dispatcher → 三路并行（LangGraph 把同一 super-step 内的多条 edge 并发执行）
    builder.add_edge("dispatcher", "sentiment")
    builder.add_edge("dispatcher", "technical")
    builder.add_edge("dispatcher", "fundamental")

    # 三路 → aggregator（LangGraph 等三个全部完成才触发 aggregator）
    builder.add_edge("sentiment", "aggregator")
    builder.add_edge("technical", "aggregator")
    builder.add_edge("fundamental", "aggregator")

    # aggregator 之后路由
    builder.add_conditional_edges(
        "aggregator",
        _route_after_analysis,
        {
            "report": "report_generator",
            "risk_warning": "risk_warning",
        },
    )

    builder.add_edge("report_generator", END)
    builder.add_edge("risk_warning", END)

    return builder.compile()


graph = build_graph()


async def run_analysis(symbol: str, market: str) -> StockAnalysisState:
    initial_state = make_initial_state(symbol, market)
    result = await graph.ainvoke(initial_state)
    return result