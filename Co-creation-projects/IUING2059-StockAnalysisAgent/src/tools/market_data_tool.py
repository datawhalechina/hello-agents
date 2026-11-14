# 路径: src/tools/market_data_tool.py
"""
行情数据采集 Tool：封装原有 MarketDataCollectorAgent 目录下的 StockDataAgent。
"""

import json

from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

# 【修正】根据你的实际目录和 __init__.py 导出，导入 StockDataAgent
from src.agent.MarketDataCollectorAgent.agents import StockDataAgent


def _to_plain(obj):
    """兼容 Pydantic v2 / v1 与普通 dict。"""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


class MarketDataTool(Tool):
    """行情数据采集工具"""

    def __init__(self):
        super().__init__(
            name="market_data_collector",
            description=(
                "获取指定 A 股股票的 K 线、基本面、估值、技术面等行情数据。"
                "输入为股票代码，如 600519。"
            ),
        )
        self._agent = StockDataAgent()

    def get_parameters(self):
        return [
            ToolParameter(
                name="stock_code",
                type="string",
                description="A 股股票代码，例如 600519",
                required=True,
            )
        ]

    def run(self, parameters):
        stock_code = (parameters or {}).get("stock_code", "").strip()
        if not stock_code:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'stock_code' 不能为空",
            )

        try:
            if hasattr(self._agent, "run"):
                # 补上缺失的 dims 参数
                # 你的原签名是 dims: list[str]。
                dims_to_fetch = ["quote", "valuation", "technical", "fundamental"]
                data = self._agent.run(stock_code, dims=dims_to_fetch)
            else:
                # 兜底：如果有 collect 方法
                data = self._agent.collect(stock_code)

            data = _to_plain(data)
            return ToolResponse.success(
                text=json.dumps(data, ensure_ascii=False, indent=2, default=str),
                data=data,
            )
        except Exception as exc:
            # 如果上面指定的 dims 字符串不对导致报错，这里的 exc 会捕获到原因
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"行情数据采集失败: {exc}",
            )