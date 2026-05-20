# backend/agent/state.py
from typing import TypedDict, Optional


class StockAnalysisState(TypedDict):
    # ── 输入 ──────────────────────────────
    symbol: str
    market: str

    # ── 数据采集层输出 ─────────────────────
    realtime_data: Optional[dict]
    kline_data: Optional[list]
    news_data: Optional[list]
    fundamental_data: Optional[dict]

    # ── 情感分析输出 ───────────────────────
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    sentiment_reason: Optional[str]
    sentiment_factors: Optional[list]

    # ── 技术面分析输出 ─────────────────────
    technical_score: Optional[float]
    technical_signals: Optional[list]
    technical_indicators: Optional[dict]

    # ── 基本面评分输出 ─────────────────────
    fundamental_score: Optional[float]
    fundamental_signals: Optional[list]   # 新增

    # ── 最终输出 ───────────────────────────
    final_report: Optional[str]
    risk_level: Optional[str]

    # ── 异常处理 ───────────────────────────
    error: Optional[str]


def make_initial_state(symbol: str, market: str) -> StockAnalysisState:
    return StockAnalysisState(
        symbol=symbol,
        market=market,
        realtime_data=None,
        kline_data=None,
        news_data=None,
        fundamental_data=None,
        sentiment_score=None,
        sentiment_label=None,
        sentiment_reason=None,
        sentiment_factors=None,
        technical_score=None,
        technical_signals=None,
        technical_indicators=None,
        fundamental_score=None,
        fundamental_signals=None,
        final_report=None,
        risk_level=None,
        error=None,
    )