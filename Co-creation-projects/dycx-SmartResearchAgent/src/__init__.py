# SmartResearchAgent - 智能研究助手
# 基于HelloAgents框架的多智能体研究工具

from .tools import WebSearchTool, TextSummarizerTool, ReportGeneratorTool
from .agent import SmartResearchAgent

__all__ = [
    "WebSearchTool",
    "TextSummarizerTool", 
    "ReportGeneratorTool",
    "SmartResearchAgent",
]
