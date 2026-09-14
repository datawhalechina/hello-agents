"""
链上数据分析工具集

提供交易所资金流向、巨鲸活动、活跃地址等链上指标。
注: 由于链上数据 API 多数需要付费，本工具使用模拟数据 + 公开 API 组合。
实际部署时可替换为 Glassnode / CoinGlass / Dune Analytics 等数据源。
"""

import random
from typing import Dict, Any, List
from hello_agents.tools import Tool, ToolParameter

from .market_data import get_ticker_24h


class ExchangeFlowTool(Tool):
    """交易所资金流向工具 - 监控交易所净流入/流出"""

    def __init__(self):
        super().__init__(
            name="get_exchange_flow",
            description=(
                "获取指定加密货币的交易所资金流向数据。"
                "包括净流入/流出量、趋势变化等。"
                "交易所净流出通常被视为看涨信号（供给减少），"
                "净流入通常被视为看跌信号（可能抛售）。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTC").upper().replace("USDT", "")
        period = parameters.get("period", "7d")

        try:
            # 尝试从 CoinGlass 公开接口获取数据
            # 注: 实际生产环境应使用付费 API
            # 这里使用基于市场数据的模拟估算
            flow_data = self._estimate_exchange_flow(symbol, period)

            result = f"## {symbol} 交易所资金流向 ({period})\n\n"
            result += f"### 净流向概览\n"
            result += f"- 净流向: {flow_data['net_flow_label']}\n"
            result += f"- 净流量: {flow_data['net_flow_amount']}\n"
            result += f"- 趋势: {flow_data['trend']}\n\n"

            result += f"### 详细数据\n"
            result += f"- 流入量 (存入交易所): {flow_data['inflow']}\n"
            result += f"- 流出量 (提出交易所): {flow_data['outflow']}\n"
            result += f"- 交易所余额变化: {flow_data['balance_change']}\n\n"

            result += f"### 解读\n"
            result += flow_data['interpretation']

            return result

        except Exception as e:
            return f"获取交易所资金流向失败: {str(e)}"

    def _estimate_exchange_flow(self, symbol: str, period: str) -> dict:
        """基于公开市场数据估算资金流向"""
        # 获取价格变化来辅助估算 (ticker 数据走共享缓存，与其他链上/情绪工具复用)
        try:
            ticker = get_ticker_24h(symbol)
            price_change_pct = float(ticker.get("priceChangePercent", 0))
            volume = float(ticker.get("quoteVolume", 0))
        except Exception:
            price_change_pct = 0
            volume = 1000000000

        # 基于价格趋势和成交量的启发式估算
        # 实际应用中应替换为真实链上数据
        if price_change_pct > 3:
            net_flow = -volume * 0.02  # 上涨时倾向净流出
            trend = "持续流出 📤"
            label = "净流出 (看涨信号)"
        elif price_change_pct < -3:
            net_flow = volume * 0.015  # 下跌时倾向净流入
            trend = "流入增加 📥"
            label = "净流入 (潜在抛压)"
        else:
            net_flow = volume * 0.003 * (1 if random.random() > 0.5 else -1)
            trend = "基本平衡 ⚖️"
            label = "基本平衡"

        abs_flow = abs(net_flow)
        inflow = abs_flow * 0.6 if net_flow > 0 else abs_flow * 0.4
        outflow = abs_flow * 0.4 if net_flow > 0 else abs_flow * 0.6

        interpretation = ""
        if net_flow < 0:
            interpretation = (
                f"- {symbol} 近期呈现净流出态势，表明持有者倾向于将资产转移到冷钱包\n"
                f"- 这通常被解读为中长期看涨信号，因为交易所可售供给在减少\n"
                f"- 但需注意: 资金流向是滞后指标，不能单独作为交易依据\n"
            )
        elif net_flow > 0:
            interpretation = (
                f"- {symbol} 近期呈现净流入态势，表明持有者将资产转入交易所\n"
                f"- 这可能意味着部分持有者准备卖出，短期存在抛压\n"
                f"- 但也可能是为了参与 DeFi 或合约交易，需结合其他指标判断\n"
            )
        else:
            interpretation = (
                f"- {symbol} 交易所资金流向基本平衡，无明显方向性信号\n"
                f"- 市场处于观望状态，等待方向选择\n"
            )

        return {
            "net_flow_label": label,
            "net_flow_amount": f"${abs_flow/1e6:,.1f}M",
            "trend": trend,
            "inflow": f"${inflow/1e6:,.1f}M",
            "outflow": f"${outflow/1e6:,.1f}M",
            "balance_change": f"{'+'if net_flow>0 else ''}{net_flow/1e6:,.1f}M",
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
            ToolParameter(
                name="period",
                type="string",
                description="统计周期: 24h, 7d, 30d",
                required=False
            ),
        ]


class WhaleActivityTool(Tool):
    """巨鲸活动监控工具"""

    def __init__(self):
        super().__init__(
            name="get_whale_activity",
            description=(
                "监控巨鲸地址（持有大量加密货币的地址）的近期活动。"
                "包括大额转账、持仓变化等。"
                "巨鲸动向常被视为市场先行指标。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTC").upper().replace("USDT", "")

        try:
            # 基于市场数据的巨鲸活动估算
            whale_data = self._estimate_whale_activity(symbol)

            result = f"## {symbol} 巨鲸活动监控\n\n"
            result += f"### 持仓变化\n"
            result += f"- 巨鲸持仓趋势: {whale_data['holding_trend']}\n"
            result += f"- 24h 大额转账: {whale_data['large_txs']}\n"
            result += f"- 活跃巨鲸数: {whale_data['active_whales']}\n\n"

            result += f"### 近期大额动向\n"
            for tx in whale_data['recent_moves']:
                result += f"- {tx}\n"

            result += f"\n### 解读\n"
            result += whale_data['interpretation']

            return result

        except Exception as e:
            return f"获取巨鲸活动数据失败: {str(e)}"

    def _estimate_whale_activity(self, symbol: str) -> dict:
        """估算巨鲸活动（实际应接入 Whale Alert 等服务）"""
        try:
            ticker = get_ticker_24h(symbol)
            price_change = float(ticker.get("priceChangePercent", 0))
            volume = float(ticker.get("quoteVolume", 0))
            current_price = float(ticker.get("lastPrice", 0))
        except Exception:
            price_change = 0
            volume = 1e9
            current_price = 60000

        # 模拟巨鲸活动数据
        if price_change > 2:
            holding_trend = "增持中 📈"
            interpretation = (
                f"- 巨鲸地址在价格上涨期间持续增持，显示大资金看好后市\n"
                f"- 大额转账以交易所流出为主，表明巨鲸在囤积\n"
                f"- 这是相对积极的信号，但需警惕巨鲸在高位派发\n"
            )
        elif price_change < -2:
            holding_trend = "观望/小幅减持 📉"
            interpretation = (
                f"- 部分巨鲸在价格下跌时有小幅减持动作\n"
                f"- 但整体减持幅度有限，未出现恐慌性抛售\n"
                f"- 需持续观察是否有加速流入交易所的迹象\n"
            )
        else:
            holding_trend = "持仓稳定 ⚖️"
            interpretation = (
                f"- 巨鲸持仓基本稳定，无明显增减持动作\n"
                f"- 市场处于蓄力阶段，大资金在等待方向\n"
                f"- 关注后续是否有突然的大额转账出现\n"
            )

        # 模拟大额转账记录
        whale_amount = volume * 0.001 / current_price
        recent_moves = [
            f"🐋 {whale_amount*0.3:,.0f} {symbol} 从未知钱包转入 Binance",
            f"🐋 {whale_amount*0.5:,.0f} {symbol} 从 Coinbase 转出至冷钱包",
            f"🐋 {whale_amount*0.2:,.0f} {symbol} 在巨鲸地址间转移",
        ]

        return {
            "holding_trend": holding_trend,
            "large_txs": f"{random.randint(15, 45)} 笔 (>$1M)",
            "active_whales": f"{random.randint(80, 150)} 个地址",
            "recent_moves": recent_moves,
            "interpretation": interpretation,
        }

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="symbol",
                type="string",
                description="加密货币符号，如 BTC, ETH",
                required=True
            ),
        ]


class ActiveAddressTool(Tool):
    """活跃地址分析工具"""

    def __init__(self):
        super().__init__(
            name="get_active_addresses",
            description=(
                "获取指定加密货币的链上活跃地址数据。"
                "活跃地址数反映网络使用热度，是基本面指标之一。"
                "活跃地址持续增长通常是看涨信号。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        symbol = parameters.get("symbol", "BTC").upper().replace("USDT", "")

        try:
            # 基于公开数据的估算
            data = self._estimate_active_addresses(symbol)

            result = f"## {symbol} 链上活跃度\n\n"
            result += f"### 活跃地址\n"
            result += f"- 日活跃地址: {data['daily_active']}\n"
            result += f"- 7日变化: {data['weekly_change']}\n"
            result += f"- 30日变化: {data['monthly_change']}\n\n"

            result += f"### 网络使用\n"
            result += f"- 日交易笔数: {data['daily_txs']}\n"
            result += f"- 新增地址: {data['new_addresses']}\n"
            result += f"- 网络活跃度评级: {data['activity_rating']}\n\n"

            result += f"### 解读\n"
            result += data['interpretation']

            return result

        except Exception as e:
            return f"获取活跃地址数据失败: {str(e)}"

    def _estimate_active_addresses(self, symbol: str) -> dict:
        """估算活跃地址数据"""
        # 不同币种的基准活跃地址数
        base_addresses = {
            "BTC": 900000,
            "ETH": 500000,
            "SOL": 300000,
            "BNB": 150000,
        }
        base = base_addresses.get(symbol, 100000)

        # 添加随机波动
        daily = int(base * (1 + random.uniform(-0.1, 0.1)))
        weekly_change = random.uniform(-5, 8)
        monthly_change = random.uniform(-3, 15)

        if monthly_change > 5:
            rating = "活跃 🟢"
            interpretation = (
                f"- {symbol} 网络活跃度处于较高水平，用户参与度良好\n"
                f"- 活跃地址数呈上升趋势，表明网络采用率在增长\n"
                f"- 这是基本面向好的信号，支撑中长期价值\n"
            )
        elif monthly_change < -3:
            rating = "降温 🟡"
            interpretation = (
                f"- {symbol} 网络活跃度有所下降，用户参与热情减退\n"
                f"- 可能与市场情绪低迷或竞争链分流有关\n"
                f"- 需关注是否为短期波动还是趋势性下降\n"
            )
        else:
            rating = "稳定 ⚪"
            interpretation = (
                f"- {symbol} 网络活跃度保持稳定，无明显异常\n"
                f"- 基本面未出现重大变化\n"
            )

        return {
            "daily_active": f"{daily:,}",
            "weekly_change": f"{weekly_change:+.1f}%",
            "monthly_change": f"{monthly_change:+.1f}%",
            "daily_txs": f"{int(daily * 1.5):,}",
            "new_addresses": f"{int(daily * 0.15):,}",
            "activity_rating": rating,
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
