"""核心框架模块

说明：本仓库的核心模块包含可选依赖（如 pydantic）。为便于在最小环境下
复用部分能力（例如仅使用 LLM 客户端），这里对可选依赖做惰性/容错导入。
"""

from .exceptions import HelloAgentsException
from .llm import HelloAgentsLLM

try:
    from .agent import Agent
    from .config import Config
    from .message import Message
except Exception:  # optional deps may be missing in minimal environments
    Agent = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]
    Message = None  # type: ignore[assignment]

__all__ = ["HelloAgentsLLM", "HelloAgentsException", "Agent", "Config", "Message"]
