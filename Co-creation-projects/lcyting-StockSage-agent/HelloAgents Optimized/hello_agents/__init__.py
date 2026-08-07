"""
HelloAgents - 轻量级多智能体框架（StockSage 精简版）

仅保留 StockSage 项目实际使用的核心组件与 Agent 范式。
"""

from .version import __version__, __author__, __email__, __description__

from .core.llm import HelloAgentsLLM
from .core.config import Config
from .core.message import Message
from .core.exceptions import HelloAgentsException
from .core.stream import StreamEvent

from .agents.react_agent import ReActAgent
from .agents.reflection_agent import ReflectionAgent

from .tools.registry import ToolRegistry, global_registry
from .tools.base import Tool, ToolParameter

import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "HelloAgentsLLM",
    "Config",
    "Message",
    "HelloAgentsException",
    "StreamEvent",
    "ReActAgent",
    "ReflectionAgent",
    "ToolRegistry",
    "global_registry",
    "Tool",
    "ToolParameter",
]
