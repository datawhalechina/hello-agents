"""
智能股票分析助手 — HelloAgents 模拟交易工具封装

将东方财富 mx-moni Skill 封装为符合 HelloAgents 标准 Tool 接口的工具类。
Agent可通过此工具执行模拟交易操作：持仓查询、资金查询、委托下单、撤单等。
"""

import sys
from pathlib import Path
import json

# 将HelloAgents框架和skills路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_SKILLS_PATH = _PROJECT_ROOT / "skills" / "模拟组合管理" / "mx-moni"

for p in [_HELLO_PATH, _SKILLS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# 与后端共用委托行解析（妙想返回字段名/数值枚举与前端约定不一致时做兼容）
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import requests
from hello_agents.tools import Tool, ToolParameter

from app.utils.mock_trading_normalize import normalize_mock_order_row

# API基础地址
MX_API_URL = "https://mkapi2.dfcfs.com/finskillshub"


class MXMoniTool(Tool):
    """模拟交易工具 — 封装东方财富妙想mx-moni Skill

    支持模拟交易操作：
    - 持仓查询：查看当前持仓股票及盈亏
    - 资金查询：查看账户余额和总资产
    - 委托查询：查看历史委托订单
    - 买入/卖出：模拟买卖股票（A股规则：100股整数倍）
    - 撤单：撤销未成交委托（支持单笔撤销和一键撤单）

    使用示例:
        tool = MXMoniTool(api_key="your_mx_apikey")
        result = tool.run({"action": "positions"})              # 查询持仓
        result = tool.run({"action": "balance"})                # 查询资金
        result = tool.run({"action": "orders"})                 # 查询委托
        result = tool.run({"action": "buy", "stock_code": "600519", "quantity": 100})
        result = tool.run({"action": "sell", "stock_code": "600519", "quantity": 100, "price": 1700})
        result = tool.run({"action": "cancel", "order_id": "260854300000078983"})
        result = tool.run({"action": "cancel_all"})             # 一键撤单
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="mx_moni",
            description=(
                "东方财富模拟交易工具。支持模拟账户的持仓查询、资金查询、"
                "委托记录查询、买入下单、卖出下单、撤单等操作。"
                "A股交易规则：买入/卖出数量必须为100股的整数倍。"
                "操作类型：positions(持仓)/balance(资金)/orders(委托)/buy(买入)/sell(卖出)/cancel(撤单)/cancel_all(一键撤单)。"
            ),
        )

        # 获取API密钥
        import os
        self.api_key = api_key or os.getenv("MX_APIKEY", "")

    def get_parameters(self) -> list:
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型：\n"
                    "- positions: 查询当前持仓\n"
                    "- balance: 查询账户资金\n"
                    "- orders: 查询委托记录\n"
                    "- buy: 买入股票\n"
                    "- sell: 卖出股票\n"
                    "- cancel: 撤销指定委托\n"
                    "- cancel_all: 一键撤销所有未成交委托"
                ),
                required=True,
            ),
            ToolParameter(
                name="stock_code",
                type="string",
                description="6位股票代码，buy/sell时必填",
                required=False,
            ),
            ToolParameter(
                name="price",
                type="number",
                description="委托价格（元），不填则使用市价委托",
                required=False,
            ),
            ToolParameter(
                name="quantity",
                type="integer",
                description="委托数量（股），必须为100的整数倍。buy/sell时必填",
                required=False,
            ),
            ToolParameter(
                name="order_id",
                type="string",
                description="委托编号，cancel操作时需要",
                required=False,
            ),
        ]

    def run(self, parameters: dict) -> str:
        """执行模拟交易操作

        Args:
            parameters: 操作参数

        Returns:
            格式化的操作结果文本
        """
        action = parameters.get("action", "").lower()

        if not self.api_key:
            return "错误：MX_APIKEY 未配置，无法执行模拟交易。请设置环境变量 MX_APIKEY"

        valid_actions = ("positions", "balance", "orders", "buy", "sell", "cancel", "cancel_all")
        if action not in valid_actions:
            return f"错误：不支持的操作类型 '{action}'，请使用: {', '.join(valid_actions)}"

        try:
            if action == "positions":
                return self._query_positions()
            elif action == "balance":
                return self._query_balance()
            elif action == "orders":
                return self._query_orders()
            elif action == "buy":
                return self._trade("buy", parameters)
            elif action == "sell":
                return self._trade("sell", parameters)
            elif action == "cancel":
                return self._cancel_order(parameters)
            elif action == "cancel_all":
                return self._cancel_all_orders()
        except Exception as e:
            return f"模拟交易异常: {str(e)}"

    def _make_request(self, endpoint: str, body: dict) -> dict:
        """发送API请求"""
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{MX_API_URL}{endpoint}",
            headers=headers,
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _query_positions(self) -> str:
        """查询持仓"""
        result = self._make_request("/api/claw/mockTrading/positions", {"moneyUnit": 1})
        return self._format_positions(result)

    def _query_balance(self) -> str:
        """查询资金"""
        result = self._make_request("/api/claw/mockTrading/balance", {"moneyUnit": 1})
        return self._format_balance(result)

    def _query_orders(self) -> str:
        """查询委托"""
        result = self._make_request("/api/claw/mockTrading/orders", {
            "fltOrderDrt": 0,
            "fltOrderStatus": 0,
        })
        return self._format_orders(result)

    def _trade(self, trade_type: str, params: dict) -> str:
        """执行买卖交易"""
        stock_code = params.get("stock_code", "")
        quantity = params.get("quantity", 0)
        price = params.get("price", None)

        if not stock_code or len(str(stock_code)) < 6:
            return "错误：请输入有效的6位股票代码"
        if not quantity or quantity <= 0:
            return "错误：请输入有效的委托数量"
        if quantity % 100 != 0:
            return "错误：A股交易数量必须为100股的整数倍"

        body = {
            "type": trade_type,
            "stockCode": str(stock_code),
            "quantity": int(quantity),
            "useMarketPrice": price is None,
        }
        if price is not None:
            body["price"] = float(price)

        result = self._make_request("/api/claw/mockTrading/trade", body)
        return self._format_trade_result(result, trade_type, stock_code, quantity, price)

    def _cancel_order(self, params: dict) -> str:
        """撤销指定委托"""
        order_id = params.get("order_id", "")

        if not order_id:
            return "错误：请提供委托编号 order_id"

        body = {
            "type": "order",
            "orderId": str(order_id),
        }
        stock_code = params.get("stock_code", "")
        if stock_code:
            body["stockCode"] = str(stock_code)

        result = self._make_request("/api/claw/mockTrading/cancel", body)
        return self._format_cancel_result(result, order_id)

    def _cancel_all_orders(self) -> str:
        """一键撤单"""
        result = self._make_request("/api/claw/mockTrading/cancel", {"type": "all"})
        return self._format_cancel_all_result(result)

    # ========== 格式化方法 ==========

    def _format_positions(self, result: dict) -> str:
        """格式化持仓数据"""
        lines = ["## 模拟持仓查询"]

        if not result.get("success") and str(result.get("code")) != "200":
            lines.append(f"查询失败: {result.get('message', '未知错误')}")
            return "\n".join(lines)

        data = result.get("data", {})
        positions = data.get("positions", [])

        if not positions:
            lines.append("\n当前无持仓记录")
            return "\n".join(lines)

        lines.append(f"\n共 {len(positions)} 只持仓股票:\n")
        lines.append("| 代码 | 名称 | 持仓量 | 成本价 | 现价 | 盈亏 | 盈亏率 |")
        lines.append("|------|------|--------|--------|------|------|--------|")

        for pos in positions:
            code = pos.get("stockCode", "-")
            name = pos.get("stockName", "-")
            qty = pos.get("quantity", "-")
            cost = pos.get("costPrice", "-")
            current = pos.get("currentPrice", "-")
            profit = pos.get("profitLoss", "-")
            profit_pct = pos.get("profitLossRate", "-")
            lines.append(f"| {code} | {name} | {qty} | {cost} | {current} | {profit} | {profit_pct} |")

        return "\n".join(lines)

    def _format_balance(self, result: dict) -> str:
        """格式化资金数据"""
        lines = ["## 模拟账户资金"]

        if not result.get("success") and str(result.get("code")) != "200":
            lines.append(f"查询失败: {result.get('message', '未知错误')}")
            return "\n".join(lines)

        data = result.get("data", {})

        lines.append(f"\n")
        lines.append(f"- 总资产: {data.get('totalAssets', '-')} 元")
        lines.append(f"- 可用资金: {data.get('availBalance', '-')} 元")
        lines.append(f"- 冻结资金: {data.get('frozenBalance', '-')} 元")
        lines.append(f"- 持仓市值: {data.get('marketValue', '-')} 元")
        lines.append(f"- 累计盈亏: {data.get('totalProfitLoss', '-')} 元")

        return "\n".join(lines)

    def _format_orders(self, result: dict) -> str:
        """格式化委托数据"""
        lines = ["## 模拟委托记录"]

        if not result.get("success") and str(result.get("code")) != "200":
            lines.append(f"查询失败: {result.get('message', '未知错误')}")
            return "\n".join(lines)

        data = result.get("data", {})
        orders = data.get("orders", [])

        if not orders:
            lines.append("\n无委托记录")
            return "\n".join(lines)

        lines.append(f"\n共 {len(orders)} 条委托:\n")
        lines.append("| 委托编号 | 代码 | 方向 | 价格 | 数量 | 状态 | 时间 |")
        lines.append("|----------|------|------|------|------|------|------|")

        for order in orders:
            row = normalize_mock_order_row(order)
            oid = row.get("order_id") or "-"
            code = row.get("stock_code") or "-"
            direction = {"buy": "买入", "sell": "卖出"}.get(
                row.get("trade_type", ""), row.get("trade_type") or "-"
            )
            price = row.get("price", "-")
            qty = row.get("quantity", "-")
            status = row.get("status_text") or row.get("status") or "-"
            time = row.get("create_time") or "-"
            lines.append(f"| {oid} | {code} | {direction} | {price} | {qty} | {status} | {time} |")

        return "\n".join(lines)

    def _format_trade_result(self, result: dict, trade_type, stock_code, quantity, price) -> str:
        """格式化交易结果"""
        direction_cn = {"buy": "买入", "sell": "卖出"}.get(trade_type, trade_type)

        if not result.get("success") and str(result.get("code")) != "200":
            return f"{direction_cn}失败: {result.get('message', '未知错误')}"

        data = result.get("data", {})
        order_id = data.get("orderId", "未知")

        lines = [
            f"## 模拟{direction_cn}委托",
            f"",
            f"✅ {direction_cn}委托已提交！",
            f"- 股票代码: {stock_code}",
            f"- 数量: {quantity} 股",
        ]
        if price:
            lines.append(f"- 价格: {price} 元/股")
        else:
            lines.append(f"- 价格: 市价委托")
        lines.append(f"- 委托编号: {order_id}")

        return "\n".join(lines)

    def _format_cancel_result(self, result: dict, order_id) -> str:
        """格式化撤单结果"""
        if not result.get("success") and str(result.get("code")) != "200":
            return f"撤单失败: {result.get('message', '未知错误')}"

        return f"✅ 撤单成功！委托编号: {order_id} 已撤销"

    def _format_cancel_all_result(self, result: dict) -> str:
        """格式化一键撤单结果"""
        if not result.get("success") and str(result.get("code")) != "200":
            return f"一键撤单失败: {result.get('message', '未知错误')}"

        return "✅ 一键撤单完成！所有未成交委托已撤销"
