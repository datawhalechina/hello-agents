# src/agent/MarketDataCollectorAgent/agents/__init__.py
"""
个股数据 Agent 包
对外暴露标准化接口，方便主 Agent 或外部直接调用。
"""

from .stock_data_agent import StockDataAgent, run_stock_data_agent
from .stock_data_tool import STOCK_DATA_TOOL
from .main_agent import build_main_agent

# 定义 __all__ 明确公共接口
__all__ = [
    "StockDataAgent",      # 核心 Agent 类（有 run 方法）
    "run_stock_data_agent", # 兼容原函数
    "STOCK_DATA_TOOL",     # LangChain Tool 实例
    "build_main_agent",    # 主 Agent 构建函数
]