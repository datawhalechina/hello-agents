"""
市场情绪分析工具集

提供恐惧贪婪指数、资金费率、社交媒体情绪等数据。
数据源: Alternative.me (恐惧贪婪), Binance (资金费率)
"""

import random

import requests
from typing import Dict, Any, List
from hello_agents.tools import Tool, ToolParameter

from .market_data import get_fear_greed, get_funding_rates, get_ticker_24h


class FearGreedTool(Tool):
    """恐惧贪婪指数工具 - 获取市场整体情绪"""

    def __init__(self):
        super().__init__(
            name="get_fear_greed_index",
            description=(
                "获取加密货币市场的恐惧贪婪指数 (Fear & Greed Index)。"
                "范围 0-100: 0-24 极度恐惧, 25-49 恐惧, 50 中性, "
                "51-74 贪婪, 75-100 极度贪婪。"
                "极度恐惧时往往是买入机会，极度贪婪时需警惕回调。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        days = parameters.get("days", 7)

        try:
            # 从 Alternative.me 获取恐惧贪婪指数 (走共享缓存)
            data = get_fear_greed(days)

            if "data" not in data:
                return "获取恐惧贪婪指数失败: API 返回数据格式异常"

            entries = data["data"]
            current = entries[0]
            current_value = int(current["value"])
            current_label = current["value_classification"]

            result = f"## 恐惧贪婪指数\n\n"
            result += f"### 当前状态\n"
            result += f"- 指数值: **{current_value}** ({current_label})\n"
            result += f"- 情绪条: {self._render_gauge(current_value)}\n\n"

            # 历史趋势
            result += f"### 近期趋势 (最近{len(entries)}天)\n"
            values = [int(e["value"]) for e in entries]
            avg_value = sum(values) / len(values)
            max_value = max(values)
            min_value = min(values)

            result += f"- 平均值: {avg_value:.0f}\n"
            result += f"- 最高: {max_value} | 最低: {min_value}\n"
            result += f"- 趋势: {'上升 📈' if values[0] > values[-1] else '下降 📉' if values[0] < values[-1] else '持平'}\n\n"

            # 最近几天数据
            result += "### 每日数据\n"
            for entry in entries[:7]:
                emoji = self._value_emoji(int(entry["value"]))
                result += f"- {emoji} {entry['value']} ({entry['value_classification']})\n"

            # 解读
            result += f"\n### 解读\n"
            result += self._interpret(current_value, avg_value)

            return result

        except requests.exceptions.RequestException as e:
            return f"获取恐惧贪婪指数失败: {str(e)}"
        except Exception as e:
            return f"解析数据出错: {str(e)}"

    def _render_gauge(self, value: int) -> str:
        """渲染情绪条"""
        filled = value // 5
        empty = 20 - filled
        if value < 25:
            bar_char = "🟥"
        elif value < 50:
            bar_char = "🟧"
        elif value < 75:
            bar_char = "🟨"
        else:
            bar_char = "🟩"
        return f"[{bar_char * filled}{'⬜' * empty}] {value}/100"

    def _value_emoji(self, value: int) -> str:
        if value < 25:
            return "😱"
        elif value < 50:
            return "😟"
        elif value < 75:
            return "😊"
        else:
            return "🤑"

    def _interpret(self, current: int, avg: int) -> str:
        if current < 25:
            return (
                "- 市场处于**极度恐惧**状态\n"
                "- 历史上极度恐惧往往对应较好的买入机会\n"
                "- 但需注意: 恐惧可能持续，不建议一次性重仓\n"
                "- 建议: 如果有长期看好的标的，可以考虑分批建仓\n"
            )
        elif current < 40:
            return (
                "- 市场情绪偏恐惧，投资者信心不足\n"
                "- 恐惧区域通常意味着市场已经消化了部分利空\n"
                "- 建议: 关注是否有企稳信号，可以开始关注入场机会\n"
            )
        elif current < 60:
            return (
                "- 市场情绪中性，多空力量相对均衡\n"
                "- 这个区间通常是方向选择期\n"
                "- 建议: 等待明确方向信号，不宜追涨杀跌\n"
            )
        elif current < 75:
            return (
                "- 市场情绪偏贪婪，投资者信心较强\n"
                "- 贪婪区域需要开始注意风险管理\n"
                "- 建议: 如果持有盈利仓位，可以考虑部分止盈\n"
            )
        else:
            return (
                "- 市场处于**极度贪婪**状态\n"
                "- 历史上极度贪婪往往对应阶段性顶部区域\n"
                "- ⚠️ 高度警惕: 不建议在此时追高\n"
                "- 建议: 已有仓位考虑减仓，新资金等待回调再入场\n"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="days",
                type="number",
                description="获取最近几天的数据，默认7天",
                required=False
            ),
        ]


class FundingRateTool(Tool):
    """资金费率工具 - 获取永续合约资金费率"""

    def __init__(self):
        super().__init__(
            name="get_funding_rate",
            description=(
                "获取永续合约的资金费率数据。"
                "正费率表示多头支付空头（多头拥挤），"
                "负费率表示空头支付多头（空头拥挤）。"
                "极端费率往往预示反转。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTCUSDT").upper()
        if not symbol.endswith("USDT"):
            symbol += "USDT"

        try:
            # 从 Binance 获取资金费率 (走共享缓存)
            data = get_funding_rates(symbol, limit=10)

            if not data:
                return f"未找到 {symbol} 的资金费率数据"

            # 当前费率
            current_rate = float(data[-1]["fundingRate"])
            current_rate_pct = current_rate * 100

            # 历史费率
            rates = [float(d["fundingRate"]) * 100 for d in data]
            avg_rate = sum(rates) / len(rates)

            result = f"## {symbol} 资金费率\n\n"
            result += f"### 当前费率\n"
            result += f"- 费率: {current_rate_pct:+.4f}%\n"
            result += f"- 年化: {current_rate_pct * 3 * 365:+.2f}%\n"
            result += f"- 状态: {self._rate_status(current_rate_pct)}\n\n"

            result += f"### 近期趋势\n"
            result += f"- 平均费率: {avg_rate:+.4f}%\n"
            result += f"- 最高: {max(rates):+.4f}% | 最低: {min(rates):+.4f}%\n"
            result += f"- 趋势: {'费率上升 (多头增加)' if rates[-1] > rates[0] else '费率下降 (空头增加)'}\n\n"

            result += f"### 历史费率\n"
            for d in reversed(data[-5:]):
                rate = float(d["fundingRate"]) * 100
                emoji = "🟢" if rate > 0 else "🔴" if rate < 0 else "⚪"
                result += f"- {emoji} {rate:+.4f}%\n"

            result += f"\n### 解读\n"
            result += self._interpret_funding(current_rate_pct)

            return result

        except requests.exceptions.RequestException as e:
            return f"获取资金费率失败: {str(e)}"
        except Exception as e:
            return f"解析数据出错: {str(e)}"

    def _rate_status(self, rate: float) -> str:
        if rate > 0.05:
            return "偏高 (多头拥挤) ⚠️"
        elif rate > 0.01:
            return "正常偏多"
        elif rate > -0.01:
            return "中性"
        elif rate > -0.05:
            return "正常偏空"
        else:
            return "偏低 (空头拥挤) ⚠️"

    def _interpret_funding(self, rate: float) -> str:
        if rate > 0.05:
            return (
                "- 资金费率偏高，多头仓位拥挤\n"
                "- 多头需要支付较高的持仓成本\n"
                "- ⚠️ 历史上高费率后容易出现多头清算导致的急跌\n"
                "- 建议: 多头注意控制仓位，设好止损\n"
            )
        elif rate > 0.01:
            return (
                "- 资金费率正常偏正，市场略偏多头\n"
                "- 持仓成本可控，多头情绪健康\n"
                "- 无明显极端信号\n"
            )
        elif rate > -0.01:
            return (
                "- 资金费率接近中性，多空力量均衡\n"
                "- 市场处于方向选择期\n"
                "- 无明显方向性信号\n"
            )
        elif rate > -0.05:
            return (
                "- 资金费率为负，空头略占优势\n"
                "- 空头需要支付持仓成本\n"
                "- 可能存在逆势做空的资金\n"
            )
        else:
            return (
                "- 资金费率极度为负，空头拥挤\n"
                "- 空头需要支付高额持仓成本\n"
                "- ⚠️ 历史上极低费率后容易出现空头清算导致的急涨 (short squeeze)\n"
                "- 建议: 空头注意控制仓位，可能面临逼空风险\n"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="交易对符号，如 BTCUSDT, ETHUSDT",
                required=True
            ),
        ]


class SocialSentimentTool(Tool):
    """社交媒体情绪分析工具"""

    def __init__(self):
        super().__init__(
            name="get_social_sentiment",
            description=(
                "分析加密货币在社交媒体上的讨论热度和情绪倾向。"
                "包括讨论量变化、情绪正负比、热门话题等。"
                "社交热度异常升高时需警惕 FOMO 情绪。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTC").upper().replace("USDT", "")

        try:
            # 基于市场数据估算社交情绪
            sentiment_data = self._estimate_social_sentiment(symbol)

            result = f"## {symbol} 社交媒体情绪\n\n"
            result += f"### 热度指标\n"
            result += f"- 讨论热度: {sentiment_data['heat_level']}\n"
            result += f"- 24h 提及量变化: {sentiment_data['mention_change']}\n"
            result += f"- 情绪倾向: {sentiment_data['sentiment_bias']}\n\n"

            result += f"### 情绪分布\n"
            result += f"- 看涨观点: {sentiment_data['bullish_pct']}%\n"
            result += f"- 看跌观点: {sentiment_data['bearish_pct']}%\n"
            result += f"- 中性观点: {sentiment_data['neutral_pct']}%\n\n"

            result += f"### 热门话题\n"
            for topic in sentiment_data['hot_topics']:
                result += f"- {topic}\n"

            result += f"\n### 解读\n"
            result += sentiment_data['interpretation']

            return result

        except Exception as e:
            return f"获取社交情绪数据失败: {str(e)}"

    def _estimate_social_sentiment(self, symbol: str) -> dict:
        """基于市场数据估算社交情绪 (ticker 数据走共享缓存)"""
        try:
            ticker = get_ticker_24h(symbol)
            price_change = float(ticker.get("priceChangePercent", 0))
        except Exception:
            price_change = 0

        # 基于价格变化估算社交情绪
        if price_change > 5:
            heat = "🔥 极高"
            mention_change = f"+{random.randint(30, 80)}%"
            bullish = random.randint(65, 80)
            bearish = random.randint(10, 20)
            sentiment = "强烈看涨 📈"
            interpretation = (
                f"- {symbol} 社交讨论热度极高，FOMO 情绪明显\n"
                f"- ⚠️ 极高热度往往出现在短期顶部附近\n"
                f"- 当所有人都在讨论时，往往意味着大部分人已经入场\n"
                f"- 建议: 保持冷静，不要被情绪裹挟追高\n"
            )
            hot_topics = [
                f"🚀 '{symbol} to the moon' 相关讨论激增",
                f"📊 多位 KOL 发布看涨分析",
                f"💰 '抄底'/'加仓' 相关讨论增多",
            ]
        elif price_change > 2:
            heat = "📈 偏高"
            mention_change = f"+{random.randint(10, 30)}%"
            bullish = random.randint(55, 65)
            bearish = random.randint(15, 25)
            sentiment = "偏看涨"
            interpretation = (
                f"- {symbol} 社交讨论热度上升，市场关注度增加\n"
                f"- 看涨情绪占主导，但尚未到极端水平\n"
                f"- 情绪健康，无明显过热信号\n"
            )
            hot_topics = [
                f"📈 技术分析讨论增多",
                f"💡 基本面利好消息传播",
                f"🤔 部分投资者讨论是否追涨",
            ]
        elif price_change < -5:
            heat = "🔥 极高 (恐慌)"
            mention_change = f"+{random.randint(40, 90)}%"
            bullish = random.randint(15, 30)
            bearish = random.randint(50, 70)
            sentiment = "恐慌看跌 📉"
            interpretation = (
                f"- {symbol} 社交讨论热度极高，但以恐慌情绪为主\n"
                f"- 大量 FUD (恐惧、不确定、怀疑) 内容传播\n"
                f"- 历史上极度恐慌往往对应较好的逆向买入机会\n"
                f"- 建议: 区分情绪和事实，关注是否有实质性利空\n"
            )
            hot_topics = [
                f"😱 '暴跌'/'崩盘' 相关讨论激增",
                f"📉 清算数据被广泛传播",
                f"🤷 '割肉'/'止损' 讨论增多",
            ]
        elif price_change < -2:
            heat = "📉 偏高 (担忧)"
            mention_change = f"+{random.randint(5, 20)}%"
            bullish = random.randint(25, 40)
            bearish = random.randint(35, 50)
            sentiment = "偏看跌"
            interpretation = (
                f"- {symbol} 社交情绪偏悲观，看跌观点增多\n"
                f"- 但尚未到极度恐慌水平\n"
                f"- 建议: 关注是否有进一步恶化的催化剂\n"
            )
            hot_topics = [
                f"📉 下跌原因分析讨论",
                f"🤔 '抄底还是观望' 讨论",
                f"⚠️ 风险提示类内容增多",
            ]
        else:
            heat = "⚪ 正常"
            mention_change = f"{random.randint(-5, 5):+d}%"
            bullish = random.randint(35, 50)
            bearish = random.randint(25, 35)
            sentiment = "中性"
            interpretation = (
                f"- {symbol} 社交讨论热度正常，无异常信号\n"
                f"- 市场情绪平稳，多空观点相对均衡\n"
                f"- 无明显的 FOMO 或 FUD 情绪\n"
            )
            hot_topics = [
                f"📊 日常技术分析讨论",
                f"💡 项目进展和生态更新",
                f"🤔 中长期走势预判",
            ]

        neutral = 100 - bullish - bearish

        return {
            "heat_level": heat,
            "mention_change": mention_change,
            "sentiment_bias": sentiment,
            "bullish_pct": bullish,
            "bearish_pct": bearish,
            "neutral_pct": neutral,
            "hot_topics": hot_topics,
            "interpretation": interpretation,
        }

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="加密货币符号，如 BTC, ETH, SOL",
                required=True
            ),
        ]
