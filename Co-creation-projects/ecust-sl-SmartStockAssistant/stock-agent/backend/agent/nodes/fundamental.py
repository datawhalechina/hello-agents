# backend/agent/nodes/fundamental.py
from typing import Optional
from agent.state import StockAnalysisState


# ── 评分工具函数 ──────────────────────────────────────────────────────

def _score_pe(pe: float, market: str) -> tuple[float, str]:
    """
    PE 市盈率评分（满分 30）。
    A股和美股估值中枢不同，分开处理。
    """
    if pe <= 0:
        return 10.0, "PE 为负（亏损企业）"

    if market == "A股":
        if pe < 15:
            return 30.0, f"PE {pe} 低估值"
        elif pe < 25:
            return 25.0, f"PE {pe} 合理估值"
        elif pe < 40:
            return 15.0, f"PE {pe} 偏高估值"
        else:
            return 5.0, f"PE {pe} 高估值风险"
    else:
        # 美股整体估值中枢更高
        if pe < 20:
            return 30.0, f"PE {pe} 低估值"
        elif pe < 35:
            return 25.0, f"PE {pe} 合理估值"
        elif pe < 55:
            return 15.0, f"PE {pe} 偏高估值"
        else:
            return 5.0, f"PE {pe} 高估值风险"


def _score_pb(pb: float) -> tuple[float, str]:
    """PB 市净率评分（满分 20）"""
    if pb <= 0:
        return 5.0, "PB 数据异常"

    if pb < 1:
        return 20.0, f"PB {pb} 破净，资产价值凸显"
    elif pb < 3:
        return 18.0, f"PB {pb} 合理"
    elif pb < 6:
        return 12.0, f"PB {pb} 偏高"
    else:
        return 5.0, f"PB {pb} 较高"


def _score_growth(
    revenue_growth: float,
    profit_growth: float,
) -> tuple[float, str]:
    """
    成长性评分（满分 30）。
    取营收和利润增速的加权平均。
    """
    # 加权：利润增速权重更高
    weighted = revenue_growth * 0.4 + profit_growth * 0.6

    if weighted >= 30:
        return 30.0, f"营收 +{revenue_growth:.1f}% 利润 +{profit_growth:.1f}%，高速成长"
    elif weighted >= 15:
        return 22.0, f"营收 +{revenue_growth:.1f}% 利润 +{profit_growth:.1f}%，稳健成长"
    elif weighted >= 5:
        return 15.0, f"营收 +{revenue_growth:.1f}% 利润 +{profit_growth:.1f}%，缓慢成长"
    elif weighted >= 0:
        return 8.0, f"营收 +{revenue_growth:.1f}% 利润 +{profit_growth:.1f}%，增速放缓"
    else:
        return 3.0, f"营收 {revenue_growth:.1f}% 利润 {profit_growth:.1f}%，业绩下滑"


def _score_market_cap(market_cap: float, market: str) -> tuple[float, str]:
    """
    市值评分（满分 20）。
    大市值企业稳定性更高。
    """
    if market == "A股":
        if market_cap >= 3000:
            return 20.0, f"市值 {market_cap:.0f} 亿，超大盘龙头"
        elif market_cap >= 500:
            return 16.0, f"市值 {market_cap:.0f} 亿，大盘股"
        elif market_cap >= 100:
            return 12.0, f"市值 {market_cap:.0f} 亿，中盘股"
        else:
            return 6.0, f"市值 {market_cap:.0f} 亿，小盘股"
    else:
        # 美股市值单位也是亿（已换算）
        if market_cap >= 10000:
            return 20.0, f"市值 {market_cap:.0f} 亿，超大盘"
        elif market_cap >= 2000:
            return 16.0, f"市值 {market_cap:.0f} 亿，大盘"
        elif market_cap >= 500:
            return 12.0, f"市值 {market_cap:.0f} 亿，中盘"
        else:
            return 6.0, f"市值 {market_cap:.0f} 亿，小盘"


def calc_fundamental_score(
    pe_ratio: float,
    pb_ratio: float,
    revenue_growth: float,
    profit_growth: float,
    market_cap: float,
    market: str,
) -> tuple[float, list[str]]:
    """
    基本面综合评分 0~100。
    维度：PE(30) + PB(20) + 成长性(30) + 市值(20)
    """
    pe_score, pe_signal = _score_pe(pe_ratio, market)
    pb_score, pb_signal = _score_pb(pb_ratio)
    growth_score, growth_signal = _score_growth(revenue_growth, profit_growth)
    cap_score, cap_signal = _score_market_cap(market_cap, market)

    total = pe_score + pb_score + growth_score + cap_score
    total = max(0.0, min(100.0, total))

    signals = [pe_signal, pb_signal, growth_signal, cap_signal]

    return round(total, 1), signals


# ── 主节点函数 ────────────────────────────────────────────────────────

async def fundamental_node(state: StockAnalysisState) -> StockAnalysisState:
    """
    基本面评分节点：纯本地计算，无需网络和 API。
    基于财务数据输出基本面综合评分。
    """
    fundamental_data = state.get("fundamental_data") or {}

    # 无基本面数据时返回默认分
    if not fundamental_data:
        return {
            "fundamental_score": 50.0,
            "fundamental_signals": ["暂无基本面数据，默认评分 50"],
        }

    pe_ratio = float(fundamental_data.get("pe_ratio") or 0)
    pb_ratio = float(fundamental_data.get("pb_ratio") or 0)
    revenue_growth = float(fundamental_data.get("revenue_growth") or 0)
    profit_growth = float(fundamental_data.get("profit_growth") or 0)
    market_cap = float(fundamental_data.get("market_cap") or 0)

    score, signals = calc_fundamental_score(
        pe_ratio=pe_ratio,
        pb_ratio=pb_ratio,
        revenue_growth=revenue_growth,
        profit_growth=profit_growth,
        market_cap=market_cap,
        market=state["market"],
    )

    return {
        "fundamental_score": score,
        "fundamental_signals": signals,
    }