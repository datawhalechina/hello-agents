"""MCPTool 本地实现 - 基于 subprocess 直接通信"""

import json
import os
import subprocess
from typing import Dict, Any, List, Optional

from hello_agents.tools.base import Tool, ToolParameter


class MCPTool(Tool):
    """MCP (Model Context Protocol) 工具 - subprocess 实现"""

    def __init__(self,
                 name: str = "mcp",
                 description: Optional[str] = None,
                 server_command: Optional[List[str]] = None,
                 env: Optional[Dict[str, str]] = None,
                 auto_expand: bool = True):
        self.server_command = server_command
        self.server_env = env
        self.auto_expand = auto_expand
        self.prefix = f"{name}_" if auto_expand else ""
        self._available_tools = []
        self._request_id = 0

        if description is None:
            description = f"MCP工具服务器: {name}"

        super().__init__(name=name, description=description, expandable=auto_expand)

        if server_command:
            self._discover_tools()

    def _make_env(self) -> dict:
        env = os.environ.copy()
        if self.server_env:
            env.update(self.server_env)
        return env

    def _batch_requests(self, requests: List[dict]) -> List[dict]:
        """在同一个子进程中逐个发送 JSON-RPC 请求"""
        from queue import Queue, Empty
        import threading

        proc = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=self._make_env()
        )

        out_queue = Queue()
        def reader():
            for line in iter(proc.stdout.readline, b""):
                out_queue.put(line)
            out_queue.put(None)
        t = threading.Thread(target=reader, daemon=True)
        t.start()

        results = []
        try:
            for req in requests:
                self._request_id += 1
                req["id"] = self._request_id

                proc.stdin.write((json.dumps(req) + "\n").encode())
                proc.stdin.flush()

                line = out_queue.get(timeout=30)
                if line is None:
                    raise RuntimeError("MCP连接提前关闭")

                line_str = line.decode(errors="replace").strip()
                response = json.loads(line_str)
                if "error" in response:
                    raise RuntimeError(f"MCP错误: {response['error']}")
                results.append(response.get("result", {}))

                # MCP 协议: initialize 后需发送 initialized 通知
                if req.get("method") == "initialize":
                    notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
                    proc.stdin.write((json.dumps(notif) + "\n").encode())
                    proc.stdin.flush()
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait(timeout=10)

        return results

    def _discover_tools(self):
        """发现 MCP 服务器的工具"""
        try:
            results = self._batch_requests([
                {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "helloagents-trip-planner", "version": "1.0"}
                    }
                },
                {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {}
                }
            ])

            if len(results) >= 2:
                tool_list = results[1]
                self._available_tools = [
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("inputSchema", {})
                    }
                    for tool in tool_list.get("tools", [])
                ]
        except Exception as e:
            print(f"  ⚠️ MCP工具发现失败: {e}")

    def get_expanded_tools(self) -> List[Tool]:
        if not self.auto_expand or not self._available_tools:
            return []
        return [MCPWrappedTool(self, info, self.prefix) for info in self._available_tools]

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action", "").lower()
        if not action and "tool_name" in parameters:
            action = "call_tool"

        try:
            if action == "call_tool":
                tool_name = parameters.get("tool_name")
                arguments = parameters.get("arguments", {})
                results = self._batch_requests([
                    {
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "helloagents-trip-planner", "version": "1.0"}
                        }
                    },
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments}
                    }
                ])
                if len(results) < 2:
                    return "MCP调用无返回"
                content = results[1].get("content", [])
                text_parts = []
                for c in content:
                    if c.get("type") == "text":
                        text_parts.append(c["text"])
                    else:
                        text_parts.append(str(c))
                return "\n".join(text_parts) if text_parts else str(results[1])
            elif action == "list_tools":
                return f"找到 {len(self._available_tools)} 个工具:\n" + "\n".join(
                    f"- {t['name']}: {t['description']}" for t in self._available_tools
                )
            else:
                return f"不支持的操作: {action}"
        except Exception as e:
            return f"MCP 操作失败: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string",
                          description="操作类型: list_tools, call_tool", required=True),
            ToolParameter(name="tool_name", type="string",
                          description="工具名称", required=False),
            ToolParameter(name="arguments", type="object",
                          description="工具参数", required=False),
        ]


class MCPWrappedTool(Tool):
    """MCP 工具包装器 - 单个 MCP 工具"""

    def __init__(self, mcp_tool: MCPTool, tool_info: Dict[str, Any], prefix: str = ""):
        self.mcp_tool = mcp_tool
        self.tool_info = tool_info
        self.mcp_tool_name = tool_info.get("name", "unknown")
        tool_name = f"{prefix}{self.mcp_tool_name}" if prefix else self.mcp_tool_name
        description = tool_info.get("description", f"MCP工具: {self.mcp_tool_name}")
        self._parameters = self._parse_input_schema(tool_info.get("input_schema", {}))
        super().__init__(name=tool_name, description=description)

    def _parse_input_schema(self, input_schema: Dict[str, Any]) -> List[ToolParameter]:
        params = []
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])
        for name, info in properties.items():
            params.append(ToolParameter(
                name=name,
                type=info.get("type", "string"),
                description=info.get("description", ""),
                required=name in required_fields
            ))
        return params

    def get_parameters(self) -> List[ToolParameter]:
        return self._parameters

    def run(self, params: Dict[str, Any]) -> str:
        return self.mcp_tool.run({
            "action": "call_tool",
            "tool_name": self.mcp_tool_name,
            "arguments": params
        })
