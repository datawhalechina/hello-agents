"""MCP (Model Context Protocol) 协议实现

基于 fastmcp 和 mcp 库的封装，提供简洁的 API 用于：
- 创建 MCP 服务器（需要 fastmcp）
- 连接 MCP 服务器（需要 mcp，可选）
- 管理模型上下文
"""

from .utils import create_context, parse_context

# 服务器需要 fastmcp
try:
    from .server import MCPServer

    MCP_SERVER_AVAILABLE = True
except ImportError:
    MCP_SERVER_AVAILABLE = False

    class MCPServer:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "MCP server requires the 'fastmcp' library. "
                "Install it with: pip install fastmcp"
            )


# 客户端需要 mcp
try:
    from .client import MCPClient

    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False

    class MCPClient:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "MCP client requires the 'mcp' library. "
                "Install it with: pip install mcp"
            )


__all__ = [
    "MCPClient",
    "MCPServer",
    "create_context",
    "parse_context",
]
