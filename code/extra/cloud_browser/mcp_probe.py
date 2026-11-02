"""用真实 MCP 客户端核对发现和两项只读调用，不创建云浏览器。"""

import asyncio
from datetime import timedelta
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ENDPOINT = "https://capybrowser.app.baizhi.cloud/mcp"
READ_ONLY_TOOLS = ("browser_auth_check", "browser_pricing")


async def probe(endpoint: str, key: str) -> dict:
    """只允许固定的只读工具；不返回账户资料或原始工具内容。"""
    if not key or key == "YOUR_API_KEY":
        raise ValueError("missing_key")
    async with streamablehttp_client(
        endpoint,
        headers={"Authorization": f"Bearer {key}"},
        timeout=timedelta(seconds=10),
        sse_read_timeout=timedelta(seconds=15),
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            discovered = {tool.name for tool in (await session.list_tools()).tools}
            if not set(READ_ONLY_TOOLS).issubset(discovered):
                raise RuntimeError("required_tools_missing")
            for name in READ_ONLY_TOOLS:
                result = await session.call_tool(name, {})
                if result.isError:
                    raise RuntimeError("tool_error")
                # HTTP/MCP success does not override an application error envelope.
                for block in result.content:
                    if block.type == "text":
                        try:
                            value = json.loads(block.text)
                        except (ValueError, TypeError):
                            continue
                        if isinstance(value, dict) and "code" in value and value["code"] != "ok":
                            raise RuntimeError("application_error")
    return {"discovery": "passed", "read_only_calls": list(READ_ONLY_TOOLS),
            "page_task": "not_run", "cloud_release": "not_applicable"}


def main() -> int:
    try:
        result = asyncio.run(asyncio.wait_for(
            probe(ENDPOINT, os.environ.get("CAPYBROWSER_API_KEY", "")), 40
        ))
    except (Exception, KeyboardInterrupt):
        # SDK errors may contain credential-bearing URLs or headers.
        print(json.dumps({"status": "failed", "detail": "Check configuration locally; no browser was requested."}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
