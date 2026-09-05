# backend/agent/nodes/technical.py
from typing import Optional
from agent.state import StockAnalysisState


# ── 指标计算工具函数 ──────────────────────────────────────────────────

def _calc_ma(closes: list[float], period: int) -> Optional[float]:
    """计算移动平均线"""
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def _calc_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None

    # 用完整序列的所有差值，不只是最后 period 个
    diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    gains = [max(d, 0) for d in diffs[-period:]]
    losses = [max(-d, 0) for d in diffs[-period:]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _calc_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Optional[dict]:
    """
    计算 MACD 指标。
    返回：{"macd": float, "signal": float, "histogram": float}
    histogram > 0 多头，< 0 空头。
    """
    if len(closes) < slow + signal:
        return None

    def ema(data: list[float], n: int) -> list[float]:
        k = 2 / (n + 1)
        result = [data[0]]
        for price in data[1:]:
            result.append(price * k + result[-1] * (1 - k))
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    # DIF 线
    dif = [f - s for f, s in zip(ema_fast[slow - 1:], ema_slow[slow - 1:])]

    # DEA 信号线
    dea = ema(dif, signal)

    macd_val = round(dif[-1], 4)
    signal_val = round(dea[-1], 4)
    histogram = round((macd_val - signal_val) * 2, 4)

    return {
        "macd": macd_val,
        "signal": signal_val,
        "histogram": histogram,
    }


def _calc_volume_trend(volumes: list[int]) -> str:
    """
    判断成交量趋势。
    比较最近 5 日均量 vs 前 5~10 日均量。
    """
    if len(volumes) < 10:
        return "unknown"

    recent_avg = sum(volumes[-5:]) / 5
    prev_avg = sum(volumes[-10:-5]) / 5

    if prev_avg == 0:
        return "unknown"

    ratio = recent_avg / prev_avg
    if ratio > 1.2:
        return "volume_up"      # 放量
    elif ratio < 0.8:
        return "volume_down"    # 缩量
    return "volume_stable"      # 平稳


def _calc_technical_score(
    ma5: Optional[float],
    ma10: Optional[float],
    ma20: Optional[float],
    rsi: Optional[float],
    macd: Optional[dict],
    volume_trend: str,
    current_price: float,
) -> tuple[float, list[str]]:
    """
    综合技术面评分 0~100，同时返回信号列表。
    评分维度：均线系统(40) + RSI(30) + MACD(20) + 量能(10)
    """
    score = 50.0   # 基础分
    signals = []

    # ── 均线系统（满分 40）──────────────────
    if ma5 and ma10 and ma20:
        # 多头排列：MA5 > MA10 > MA20
        if ma5 > ma10 > ma20:
            score += 20
            signals.append("均线多头排列")
        elif ma5 < ma10 < ma20:
            score -= 20
            signals.append("均线空头排列")

        # 价格与均线关系
        if current_price > ma20:
            score += 10
            signals.append("价格站上 MA20")
        else:
            score -= 10
            signals.append("价格跌破 MA20")

        if current_price > ma5:
            score += 10
        else:
            score -= 10

    # ── RSI（满分 30）────────────────────────
    if rsi is not None:
        if 40 <= rsi <= 60:
            score += 15
            signals.append(f"RSI {rsi} 处于健康区间")
        elif rsi < 30:
            score += 25
            signals.append(f"RSI {rsi} 超卖，存在反弹机会")
        elif rsi > 70:
            score -= 15
            signals.append(f"RSI {rsi} 超买，注意回调风险")
        elif 60 < rsi <= 70:
            score += 5

    # ── MACD（满分 20）───────────────────────
    if macd:
        if macd["histogram"] > 0:
            score += 10
            signals.append("MACD 红柱，多头动能")
        else:
            score -= 10
            signals.append("MACD 绿柱，空头动能")

        if macd["macd"] > macd["signal"]:
            score += 10
            signals.append("MACD 金叉")
        else:
            score -= 5
            signals.append("MACD 死叉")

    # ── 量能（满分 10）───────────────────────
    if volume_trend == "volume_up":
        score += 10
        signals.append("成交量放大，趋势增强")
    elif volume_trend == "volume_down":
        score -= 5
        signals.append("成交量萎缩，趋势减弱")

    # 限制在 0~100
    score = max(0.0, min(100.0, score))
    return round(score, 1), signals


# ── 主节点函数 ────────────────────────────────────────────────────────

async def technical_node(state: StockAnalysisState) -> StockAnalysisState:
    """
    技术面分析节点：纯本地计算，无需网络和 API。
    基于 K 线数据计算 MA / RSI / MACD / 量能，输出技术评分。
    """
    # mock 模式
    if True:  # 先检查 settings，但 technical 是纯计算，mock 和真实逻辑一样
        pass

    kline_data = state.get("kline_data") or []
    realtime_data = state.get("realtime_data") or {}

    # K 线数据不足时跳过
    if len(kline_data) < 5:
        return {
            "technical_score": 50.0,
            "technical_signals": ["K线数据不足，无法进行技术分析"],
            "technical_indicators": {},
        }

    # 提取收盘价和成交量序列
    closes = [float(bar["close"]) for bar in kline_data]
    volumes = [int(bar["volume"]) for bar in kline_data]
    current_price = float(realtime_data.get("price") or closes[-1])

    # 计算各项指标
    ma5 = _calc_ma(closes, 5)
    ma10 = _calc_ma(closes, 10)
    ma20 = _calc_ma(closes, 20)
    rsi = _calc_rsi(closes, 14)
    macd = _calc_macd(closes)
    volume_trend = _calc_volume_trend(volumes)

    # 综合评分
    score, signals = _calc_technical_score(
        ma5, ma10, ma20, rsi, macd, volume_trend, current_price
    )

    indicators = {
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "rsi": rsi,
        "macd": macd,
        "volume_trend": volume_trend,
        "current_price": current_price,
    }

    return {
        "technical_score": score,
        "technical_signals": signals,
        "technical_indicators": indicators,
    }