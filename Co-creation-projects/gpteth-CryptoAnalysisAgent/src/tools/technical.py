"""
技术分析工具集

提供 K 线数据获取、技术指标计算、支撑阻力位识别等能力。
数据源: Binance 公开 API (无需 API Key)，经由 market_data 共享缓存层访问，
同一轮分析中多个工具复用同一份 K 线数据，不重复请求。
"""

import requests
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from hello_agents.tools import Tool, ToolParameter

from .market_data import get_klines


def _parse_ohlcv(data: List[list]):
    """将 Binance K 线原始数据解析为 numpy 数组 (times, opens, highs, lows, closes, volumes)"""
    arr = np.asarray(data, dtype=object)
    times = arr[:, 0].astype(np.int64)
    ohlcv = arr[:, 1:6].astype(np.float64)
    return times, ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]


class KlineFetchTool(Tool):
    """K 线数据获取工具 - 从 Binance 获取历史 K 线数据"""

    def __init__(self):
        super().__init__(
            name="fetch_klines",
            description=(
                "从 Binance 获取指定交易对的 K 线数据。"
                "返回包含开盘价、最高价、最低价、收盘价、成交量的历史数据。"
                "支持多种时间周期: 1m, 5m, 15m, 1h, 4h, 1d, 1w。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTCUSDT").upper()
        interval = parameters.get("interval", "4h")
        limit = min(parameters.get("limit", 50), 100)

        try:
            # 统一按 100 根拉取再截取，使同一轮分析中的三个技术工具命中同一份缓存
            data = get_klines(symbol, interval, 100)[-limit:]
            times, opens, highs, lows, closes, volumes = _parse_ohlcv(data)

            current_price = closes[-1]
            price_change = (closes[-1] - closes[0]) / closes[0] * 100

            summary = (
                f"## {symbol} K线数据 ({interval}, 最近{limit}根)\n\n"
                f"- 当前价格: ${current_price:,.2f}\n"
                f"- 区间涨跌: {price_change:+.2f}%\n"
                f"- 最高价: ${highs.max():,.2f}\n"
                f"- 最低价: ${lows.min():,.2f}\n"
                f"- 平均成交量: {volumes.mean():,.0f}\n\n"
                f"### 最近5根K线\n"
            )

            for i in range(max(0, len(closes) - 5), len(closes)):
                change = "🟢" if closes[i] >= opens[i] else "🔴"
                ts = pd.Timestamp(times[i], unit='ms').strftime('%Y-%m-%d %H:%M')
                summary += f"- {change} {ts} | O:{opens[i]:,.2f} H:{highs[i]:,.2f} L:{lows[i]:,.2f} C:{closes[i]:,.2f} V:{volumes[i]:,.0f}\n"

            return summary

        except requests.exceptions.RequestException as e:
            return f"获取K线数据失败: {str(e)}"
        except Exception as e:
            return f"解析K线数据出错: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="交易对符号，如 BTCUSDT, ETHUSDT, SOLUSDT",
                required=True
            ),
            ToolParameter(
                name="interval",
                type="string",
                description="K线周期: 1m, 5m, 15m, 1h, 4h, 1d, 1w",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="获取K线数量，默认50，最大100",
                required=False
            ),
        ]


class TechnicalIndicatorTool(Tool):
    """技术指标计算工具 - 计算常用技术指标"""

    def __init__(self):
        super().__init__(
            name="calculate_indicators",
            description=(
                "基于 K 线数据计算技术指标。"
                "支持: EMA(指数移动平均), RSI(相对强弱), MACD, "
                "Bollinger Bands(布林带), ATR(真实波幅)。"
                "会自动从 Binance 获取数据并计算。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTCUSDT").upper()
        interval = parameters.get("interval", "4h")
        indicators = parameters.get("indicators", ["ema", "rsi", "macd", "boll"])

        try:
            # 获取足够的 K 线数据用于计算 (与其他工具共享缓存)
            data = get_klines(symbol, interval, 100)
            _, _, highs, lows, closes, _ = _parse_ohlcv(data)
            current_price = closes[-1]

            result = f"## {symbol} 技术指标 ({interval})\n\n"
            result += f"当前价格: ${current_price:,.2f}\n\n"

            # EMA
            if "ema" in indicators:
                ema20 = self._ema(closes, 20)[-1]
                ema50 = self._ema(closes, 50)[-1]
                ema_trend = "多头排列 📈" if ema20 > ema50 else "空头排列 📉"
                result += f"### EMA\n"
                result += f"- EMA(20): ${ema20:,.2f}\n"
                result += f"- EMA(50): ${ema50:,.2f}\n"
                result += f"- 排列: {ema_trend}\n"
                result += f"- 价格 vs EMA20: {'上方' if current_price > ema20 else '下方'}\n\n"

            # RSI
            if "rsi" in indicators:
                rsi14 = self._rsi(closes, 14)
                rsi_status = "超买 ⚠️" if rsi14 > 70 else ("超卖 ⚠️" if rsi14 < 30 else "中性")
                result += f"### RSI\n"
                result += f"- RSI(14): {rsi14:.1f} ({rsi_status})\n\n"

            # MACD (一次计算完整序列，当前值与前一根直接比较，避免重复全量计算)
            if "macd" in indicators:
                macd_series, signal_series, hist_series = self._macd(closes)
                macd_line, signal_line, histogram = macd_series[-1], signal_series[-1], hist_series[-1]
                macd_cross = "金叉 🟢" if macd_line > signal_line else "死叉 🔴"
                hist_trend = "动能增强" if abs(histogram) > abs(hist_series[-2]) else "动能减弱"
                result += f"### MACD\n"
                result += f"- MACD线: {macd_line:.2f}\n"
                result += f"- 信号线: {signal_line:.2f}\n"
                result += f"- 柱状图: {histogram:.2f}\n"
                result += f"- 状态: {macd_cross}, {hist_trend}\n\n"

            # Bollinger Bands
            if "boll" in indicators:
                upper, middle, lower = self._bollinger(closes, 20)
                boll_pos = (current_price - lower) / (upper - lower) * 100
                result += f"### 布林带\n"
                result += f"- 上轨: ${upper:,.2f}\n"
                result += f"- 中轨: ${middle:,.2f}\n"
                result += f"- 下轨: ${lower:,.2f}\n"
                result += f"- 价格位置: {boll_pos:.0f}% (0%=下轨, 100%=上轨)\n"
                result += f"- 带宽: {(upper-lower)/middle*100:.2f}%\n\n"

            # ATR
            if "atr" in indicators:
                atr = self._atr(highs, lows, closes, 14)
                atr_pct = atr / current_price * 100
                result += f"### ATR (波动率)\n"
                result += f"- ATR(14): ${atr:,.2f} ({atr_pct:.2f}%)\n"
                result += f"- 含义: 平均每根K线波动 ${atr:,.2f}\n\n"

            return result

        except requests.exceptions.RequestException as e:
            return f"获取数据失败: {str(e)}"
        except Exception as e:
            return f"计算指标出错: {str(e)}"

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均 (向量化实现，与逐元素递推等价)"""
        alpha = 2 / (period + 1)
        return pd.Series(data).ewm(alpha=alpha, adjust=False).mean().to_numpy()

    def _rsi(self, data: np.ndarray, period: int = 14) -> float:
        """计算 RSI"""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _macd(self, data: np.ndarray):
        """计算 MACD，返回 (macd_line, signal_line, histogram) 三个完整序列"""
        macd_line = self._ema(data, 12) - self._ema(data, 26)
        signal_line = self._ema(macd_line, 9)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _bollinger(self, data: np.ndarray, period: int = 20):
        """计算布林带"""
        middle = np.mean(data[-period:])
        std = np.std(data[-period:])
        upper = middle + 2 * std
        lower = middle - 2 * std
        return upper, middle, lower

    def _atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """计算 ATR"""
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        return np.mean(tr[-period:])

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="交易对符号，如 BTCUSDT",
                required=True
            ),
            ToolParameter(
                name="interval",
                type="string",
                description="K线周期: 1h, 4h, 1d",
                required=False
            ),
            ToolParameter(
                name="indicators",
                type="array",
                description="要计算的指标列表: ema, rsi, macd, boll, atr",
                required=False
            ),
        ]


class SupportResistanceTool(Tool):
    """支撑阻力位识别工具"""

    def __init__(self):
        super().__init__(
            name="find_support_resistance",
            description=(
                "识别指定交易对的关键支撑位和阻力位。"
                "基于近期价格的高低点聚类分析，找出市场关注的关键价位。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTCUSDT").upper()
        interval = parameters.get("interval", "4h")

        try:
            data = get_klines(symbol, interval, 100)
            _, _, highs, lows, closes, _ = _parse_ohlcv(data)
            current_price = closes[-1]

            # 找局部高点和低点 (向量化: 比较中心点与前后各2根K线)
            h = highs[2:-2]
            is_peak = (h > highs[1:-3]) & (h > highs[:-4]) & (h > highs[3:-1]) & (h > highs[4:])
            resistance_levels = h[is_peak].tolist()

            l = lows[2:-2]
            is_trough = (l < lows[1:-3]) & (l < lows[:-4]) & (l < lows[3:-1]) & (l < lows[4:])
            support_levels = l[is_trough].tolist()

            # 聚类合并相近的价位 (差距小于 1%)
            resistance_levels = self._cluster_levels(resistance_levels, current_price)
            support_levels = self._cluster_levels(support_levels, current_price)

            # 筛选当前价格上方的阻力和下方的支撑
            resistances = sorted([r for r in resistance_levels if r > current_price])[:3]
            supports = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]

            result = f"## {symbol} 支撑阻力位 ({interval})\n\n"
            result += f"当前价格: ${current_price:,.2f}\n\n"

            result += "### 阻力位 (上方)\n"
            for i, r in enumerate(resistances, 1):
                dist = (r - current_price) / current_price * 100
                result += f"- R{i}: ${r:,.2f} (距当前 +{dist:.2f}%)\n"

            result += "\n### 支撑位 (下方)\n"
            for i, s in enumerate(supports, 1):
                dist = (current_price - s) / current_price * 100
                result += f"- S{i}: ${s:,.2f} (距当前 -{dist:.2f}%)\n"

            # 风险收益比参考
            if resistances and supports:
                potential_gain = resistances[0] - current_price
                potential_loss = current_price - supports[0]
                if potential_loss > 0:
                    rr_ratio = potential_gain / potential_loss
                    result += f"\n### 风险收益参考\n"
                    result += f"- 最近阻力距离: ${potential_gain:,.2f}\n"
                    result += f"- 最近支撑距离: ${potential_loss:,.2f}\n"
                    result += f"- 风险收益比: 1:{rr_ratio:.2f}\n"

            return result

        except Exception as e:
            return f"识别支撑阻力位失败: {str(e)}"

    def _cluster_levels(self, levels: list, reference_price: float, threshold: float = 0.01) -> list:
        """将相近的价位聚类合并"""
        if not levels:
            return []
        levels = sorted(levels)
        clustered = [levels[0]]
        for level in levels[1:]:
            if abs(level - clustered[-1]) / reference_price > threshold:
                clustered.append(level)
            else:
                clustered[-1] = (clustered[-1] + level) / 2
        return clustered

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="交易对符号，如 BTCUSDT",
                required=True
            ),
            ToolParameter(
                name="interval",
                type="string",
                description="K线周期，推荐 4h 或 1d",
                required=False
            ),
        ]
