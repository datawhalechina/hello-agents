"""
HelloAgents - 灵活、可扩展的多智能体框架

基于OpenAI原生API构建，提供简洁高效的智能体开发体验。
"""

from .version import __version__, __author__, __email__, __description__

# 核心组件
from .core.llm import HelloAgentsLLM
from .core.config import Config
from .core.message import Message
from .core.exceptions import HelloAgentsException
from .core.stream import StreamEvent
from .core.conversation import Conversation
from .core.conversation_manager import ConversationManager
from .core.plugin import Plugin, PluginRegistry, registry

# Agent实现
from .agents.simple_agent import SimpleAgent
from .agents.function_call_agent import FunctionCallAgent
from .agents.react_agent import ReActAgent
from .agents.reflection_agent import ReflectionAgent
from .agents.plan_solve_agent import PlanAndSolveAgent
from .agents.tool_aware_agent import ToolAwareSimpleAgent
from .agents.tree_of_thought_agent import TreeOfThoughtAgent

# 工具系统
from .tools.registry import ToolRegistry, global_registry
from .tools.builtin.search_tool import SearchTool, search
from .tools.builtin.calculator import CalculatorTool, calculate
from .tools.chain import ToolChain, ToolChainManager
from .tools.async_executor import AsyncToolExecutor

# 配置第三方库的日志级别，减少噪音
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    # 核心组件
    "HelloAgentsLLM",
    "Config",
    "Message",
    "HelloAgentsException",
    "StreamEvent",
    "Conversation",
    "ConversationManager",
    "Plugin",
    "PluginRegistry",
    "registry",
    # Agent范式
    "SimpleAgent",
    "FunctionCallAgent",
    "ReActAgent",
    "ReflectionAgent",
    "PlanAndSolveAgent",
    "ToolAwareSimpleAgent",
    "TreeOfThoughtAgent",
    # 工具系统
    "ToolRegistry",
    "global_registry",
    "SearchTool",
    "search",
    "CalculatorTool",
    "calculate",
    "ToolChain",
    "ToolChainManager",
    "AsyncToolExecutor",
]

# 自动扫描已安装的插件
registry.scan_entry_points()
