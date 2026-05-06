"""A2A (Agent-to-Agent Protocol) 协议实现

基于官方 a2a 库的封装，提供简洁的 API 用于：
- Agent 间消息传递
- 任务委托与协商
- 多 Agent 协作

注意: A2A 功能需要安装官方 SDK: pip install a2a
详见文档: docs/chapter10/A2A_GUIDE.md
"""

# A2A 是可选的，需要安装官方 SDK
try:
    from .implementation import A2AServer, A2AClient, AgentNetwork, AgentRegistry
    from .conflict_resolution import (
        NegotiationMessage,
        VotingMessage,
        NegotiationManager,
        VotingManager,
        ConflictResolver,
        ConflictStrategy,
        A2AExtendedServer,
        MessageType,
    )

    __all__ = [
        "A2AServer",
        "A2AClient",
        "AgentNetwork",
        "AgentRegistry",
        "NegotiationMessage",
        "VotingMessage",
        "NegotiationManager",
        "VotingManager",
        "ConflictResolver",
        "ConflictStrategy",
        "A2AExtendedServer",
        "MessageType",
    ]
except ImportError:
    # 如果没有安装依赖，提供占位符
    __all__ = []

    class _A2ANotAvailable:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "A2A protocol requires the official 'a2a' library. "
                "Install it with: pip install a2a\n"
                "See docs/chapter10/A2A_GUIDE.md for more information."
            )

    A2AServer = _A2ANotAvailable
    A2AClient = _A2ANotAvailable
    AgentNetwork = _A2ANotAvailable
    AgentRegistry = _A2ANotAvailable

# 为了向后兼容，提供别名
A2AAgent = A2AServer
A2AMessage = dict  # 简化的消息类型
MessageType = str


def create_message(*args, **kwargs):
    """创建 A2A 消息（占位符）"""
    raise ImportError("Please install a2a library: pip install a2a")


def parse_message(*args, **kwargs):
    """解析 A2A 消息（占位符）"""
    raise ImportError("Please install a2a library: pip install a2a")
