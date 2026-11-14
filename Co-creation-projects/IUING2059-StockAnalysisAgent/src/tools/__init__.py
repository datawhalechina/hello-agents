# 路径: src/tools/__init__.py
"""
HelloAgents Tool 包：把原有 LangChain 子 Agent 封装为标准 Tool。
统一从 src.tools 导出，主控 Agent 只需 from src.tools import ...
"""

from .market_data_tool import MarketDataTool
from .news_sentiment_tool import NewsSentimentTool

__all__ = [
    "MarketDataTool",
    "NewsSentimentTool",
]
