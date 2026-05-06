"""内置工具模块

HelloAgents框架的内置工具集合，包括：
- SearchTool: 网页搜索工具
- CalculatorTool: 数学计算工具
- MemoryTool: 记忆工具
- RAGTool: 检索增强生成工具
- NoteTool: 结构化笔记工具（第9章）
- TerminalTool: 命令行工具（第9章）
- MCPTool: MCP 协议工具（第10章 - 基于 mcp v1.15.0）
- A2ATool: A2A 协议工具（第10章 - 基于 python-a2a v0.5.10）
- ANPTool: ANP 协议工具（第10章 - 基于 agent-connect v0.3.7）
- BFCLEvaluationTool: BFCL评估工具（第12章）
- GAIAEvaluationTool: GAIA评估工具（第12章）
- LLMJudgeTool: LLM Judge评估工具（第12章）
- WinRateTool: Win Rate评估工具（第12章）
"""

from .search_tool import SearchTool
from .calculator import CalculatorTool
from .memory_tool import MemoryTool
from .rag_tool import RAGTool
from .note_tool import NoteTool
from .terminal_tool import TerminalTool
from .protocol_tools import MCPTool, A2ATool, ANPTool
from .bfcl_evaluation_tool import BFCLEvaluationTool
from .gaia_evaluation_tool import GAIAEvaluationTool
from .llm_judge_tool import LLMJudgeTool
from .win_rate_tool import WinRateTool
from .task_dep_manager import TaskDepTool, TaskDepManager

__all__ = [
    "SearchTool",
    "CalculatorTool",
    "MemoryTool",
    "RAGTool",
    "NoteTool",
    "TerminalTool",
    "MCPTool",
    "A2ATool",
    "ANPTool",
    "BFCLEvaluationTool",
    "GAIAEvaluationTool",
    "LLMJudgeTool",
    "WinRateTool",
    "TaskDepTool",
    "TaskDepManager",
]
