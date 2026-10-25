"""MCP 能力外放演示：外部程序经 MCP 协议使用本项目的课程检索。

演示链路（对齐框架 hello_agents/tools/mcp.py 真实 API：MCPConnection）：
  MCPConnection.stdio(python, mcp_server.py)
    → async with 打开连接（自动 list_tools 发现外部工具）
    → register_tools(registry) 注册
    → await aexecute_tool(...) 调用（stdio 子进程往返）

运行：.venv/Scripts/python.exe scripts/mcp_demo.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hello_agents.tools import ToolRegistry  # noqa: E402
from hello_agents.tools.mcp import MCPConnection  # noqa: E402

PYTHON = sys.executable
SERVER = Path(__file__).resolve().parent / "mcp_server.py"


async def main():
    registry = ToolRegistry()
    async with MCPConnection.stdio(PYTHON, [str(SERVER)]) as conn:
        names = conn.register_tools(registry)
        print(f"[MCP] 发现并注册 {len(names)} 个外部工具：{list(names)}")

        checks = [
            ("list_coverage", {}),
            ("search_courses", {"query": "machine learning", "level": "graduate",
                                "limit": 3}),
            ("get_course", {"course_code": "EE6407"}),
            ("get_course", {"course_code": "CS1010S"}),
            ("cca_degree_rules", {"option": 1}),
        ]
        for name, args in checks:
            result = await registry.aexecute_tool(name, args)
            text = result.text.replace("\n", " ")
            print(f"\n[MCP] {name}({args}) →\n  {text[:260]}...")

        print("\n[MCP] 链路验证通过：外部程序不改本项目代码，"
              "经 MCP 协议即可检索课程库与学位规则。")


if __name__ == "__main__":
    asyncio.run(main())
