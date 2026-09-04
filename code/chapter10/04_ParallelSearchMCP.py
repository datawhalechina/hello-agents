"""通过 Streamable HTTP 体验无需 API Key 的远程搜索和网页提取。"""

import asyncio
from uuid import uuid4

from hello_agents.protocols import MCPClient


async def main():
    # 同一次任务中的搜索和提取共用一个标识，不包含个人信息。
    session_id = str(uuid4())
    client = MCPClient(
        "https://search.parallel.ai/mcp",
        transport_type="streamable_http",
    )

    # 运行时会将下面的查询、URL 和目标发送给 Parallel。
    async with client:
        tools = await client.list_tools()
        print(f"可用工具: {[tool['name'] for tool in tools]}")

        search_result = await client.call_tool("web_search", {
            "objective": "Find the official Python SDK for Model Context Protocol",
            "search_queries": ["Model Context Protocol official Python SDK"],
            "session_id": session_id,
        })
        print(f"搜索结果:\n{search_result}")

        fetch_result = await client.call_tool("web_fetch", {
            "urls": ["https://github.com/modelcontextprotocol/python-sdk"],
            "objective": "Find installation instructions and a basic client example",
            "full_content": False,
            "session_id": session_id,
        })
        print(f"网页提取结果:\n{fetch_result}")


if __name__ == "__main__":
    asyncio.run(main())
