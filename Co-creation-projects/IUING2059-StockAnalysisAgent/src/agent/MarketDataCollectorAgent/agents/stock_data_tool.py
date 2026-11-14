# agents/stock_data_tool.py
import json
from langchain_core.tools import tool
from .stock_data_agent import StockDataAgent

# 实例化 Agent（单例，避免重复初始化）
_agent = StockDataAgent()


@tool
def stock_data_agent(stock_code: str, dims: list[str]) -> str:
    """个股数据子 agent：获取单只 A 股的行情/基本面/估值/技术面数据。
    dims 可选：quote（行情）、valuation（估值）、technical（技术面）、
    fundamental（基本面，较慢）。
    示例：stock_data_agent("600519", ["quote", "technical"])"""
    # 调用标准化接口 run()，逻辑完全由 Agent 类内部处理
    result = _agent.run(stock_code, dims)
    return json.dumps(result, ensure_ascii=False)


STOCK_DATA_TOOL = stock_data_agent