import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# 创建 MCP Server
mcp = FastMCP("hello_mcp")


@mcp.tool()
def hello_mcp() -> str:
    """测试 MCP 服务是否正常"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = f"HELLO MCP - {current_time}"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return result


if __name__ == "__main__":
    mcp.run()