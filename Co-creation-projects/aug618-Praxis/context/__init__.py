"""上下文工程模块

为HelloAgents框架提供上下文工程能力：
- ContextBuilder: GSSC流水线（Gather-Select-Structure-Compress）
"""

from .builder import ContextBuilder, ContextConfig, ContextPacket

__all__ = ["ContextBuilder", "ContextConfig", "ContextPacket"]

