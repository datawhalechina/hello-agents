# 路径: src/tools/registry_builder.py
"""
集中构建 ToolRegistry，方便主控 Agent 一步拿到注册好的工具集合。
"""

from hello_agents import ToolRegistry

from .market_data_tool import MarketDataTool
from .news_sentiment_tool import NewsSentimentTool


def build_default_registry(news_default_limit: int = 2) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tool(MarketDataTool())
    registry.register_tool(NewsSentimentTool(default_limit=news_default_limit))
    return registry