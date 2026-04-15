from hello_agents.tools import MCPTool

# 1. Memory Transport - 内存传输（用于测试）
# 不指定任何参数，使用内置演示服务器
#mcp_tool = MCPTool()

# 2. Stdio Transport - 标准输入输出传输（本地开发）
# 使用命令列表启动本地服务器
#mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py"])

# 3. Stdio Transport with Args - 带参数的命令传输
# 可以传递额外参数
#mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py", "--debug"])

# 4. Stdio Transport - 社区服务器（npx方式）
# 使用npx启动社区MCP服务器
#mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# 5. HTTP/SSE/StreamableHTTP Transport
# 注意：MCPTool主要用于Stdio和Memory传输
# 对于HTTP/SSE等远程传输，建议直接使用MCPClient

from hello_agents.tools import MCPTool

# 使用内置演示服务器（Memory传输）
mcp_tool = MCPTool()

# 列出可用工具
result = mcp_tool.run({"action": "list_tools"})
print(result)

# 调用工具
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(result)

# from hello_agents.tools import MCPTool
#
# # 方式1：使用自定义Python服务器
# mcp_tool = MCPTool(server_command=["python", "my_mcp_server.py"])
#
# 方式2：使用社区服务器（文件系统）
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# 列出工具
result = mcp_tool.run({"action": "list_tools"})
print(result)

# 调用工具
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "read_file",
    "arguments": {"path": "my_README.md"}
})
print(result)

#
# # 注意：MCPTool 主要用于 Stdio 和 Memory 传输
# # 对于 HTTP/SSE 等远程传输，建议使用底层的 MCPClient
#
# import asyncio
# from hello_agents.protocols.mcp.client import MCPClient
#
# async def test_http_transport():
#     # 连接到远程 HTTP MCP 服务器
#     client = MCPClient("http://api.example.com/mcp")
#
#     async with client:
#         # 获取服务器信息
#         tools = await client.list_tools()
#         print(f"远程服务器工具: {len(tools)} 个")
#
#         # 调用远程工具
#         result = await client.call_tool("process_data", {
#             "data": "Hello, World!",
#             "operation": "uppercase"
#         })
#         print(f"远程处理结果: {result}")
#
# # 注意：需要实际的 HTTP MCP 服务器
# asyncio.run(test_http_transport())