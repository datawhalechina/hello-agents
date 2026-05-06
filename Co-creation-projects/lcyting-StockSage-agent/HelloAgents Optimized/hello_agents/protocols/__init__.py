"""智能体通信协议模块

本模块提供三种主要的智能体通信协议：
- MCP (Model Context Protocol): 模型上下文协议
- A2A (Agent-to-Agent Protocol): 智能体间通信协议
- ANP (Agent Network Protocol): 智能体网络协议

简洁导入示例：
    >>> from hello_agents.protocols import MCPClient, MCPServer
    >>> from hello_agents.protocols import A2AServer, A2AClient, AgentNetwork
    >>> from hello_agents.protocols import ANPDiscovery, ANPNetwork

完整导入示例（向后兼容）：
    >>> from hello_agents.protocols.mcp import MCPClient, MCPServer
    >>> from hello_agents.protocols.a2a import A2AServer, A2AClient
    >>> from hello_agents.protocols.anp import ANPDiscovery, ANPNetwork
"""

from .base import Protocol

# MCP 协议 - 导出所有常用类（可选，需要 fastmcp）
try:
    from .mcp import (
        MCPClient,
        MCPServer,
        create_context,
        parse_context,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

    # 提供占位符
    class MCPClient:
        def __init__(self, *args, **kwargs):
            raise ImportError("MCP requires fastmcp: pip install fastmcp")

    class MCPServer:
        def __init__(self, *args, **kwargs):
            raise ImportError("MCP requires fastmcp: pip install fastmcp")

    def create_context(*args, **kwargs):
        raise ImportError("MCP requires fastmcp: pip install fastmcp")

    def parse_context(*args, **kwargs):
        raise ImportError("MCP requires fastmcp: pip install fastmcp")


# A2A 协议 - 导出所有常用类
from .a2a import (
    A2AAgent,
    A2AServer,
    A2AClient,
    AgentNetwork,
    AgentRegistry,
    A2AMessage,
    MessageType,
    create_message,
    parse_message,
)

# ANP 协议 - 导出所有常用类
from .anp import (
    ANPDiscovery,
    ANPNetwork,
    ServiceInfo,
    register_service,
    discover_service,
)

__all__ = [
    # 基础协议
    "Protocol",
    # MCP 协议（可选）
    "MCPClient",
    "MCPServer",
    "create_context",
    "parse_context",
    # A2A 协议（可选）
    "A2AAgent",
    "A2AServer",
    "A2AClient",
    "AgentNetwork",
    "AgentRegistry",
    "A2AMessage",
    "MessageType",
    "create_message",
    "parse_message",
    # ANP 协议
    "ANPDiscovery",
    "ANPNetwork",
    "ServiceInfo",
    "register_service",
    "discover_service",
]
