from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool
import dotenv

dotenv.load_dotenv()
print("=" * 70)
print("方式1：使用内置演示服务器")
print("=" * 70)

agent = SimpleAgent(name="助手", llm=HelloAgentsLLM())

# 无需任何配置，自动使用内置演示服务器
# 内置服务器提供：add, subtract, multiply, divide, greet, get_system_info
mcp_tool = MCPTool()  # 默认name="mcp"
agent.add_tool(mcp_tool)

# 智能体可以使用内置工具
response = agent.run("计算 123 + 456")
print(response)  # 智能体会自动调用add工具

print("\n" + "=" * 70)
print("方式2：连接外部MCP服务器（使用多个服务器）")
print("=" * 70)

# 重要：为每个MCP服务器指定不同的name，避免工具名称冲突

# 示例1：连接到社区提供的文件系统服务器
fs_tool = MCPTool(
    name="filesystem",  # 指定唯一名称
    description="访问本地文件系统",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
agent.add_tool(fs_tool)

# 示例2：连接到自定义的 Python MCP 服务器
# 关于如何编写自定义MCP服务器，请参考10.5章节
custom_tool = MCPTool(
    name="custom_server",  # 使用不同的名称
    description="自定义业务逻辑服务器",
    server_command=["python", "my_mcp_server.py"]
)
agent.add_tool(custom_tool)

print("\n当前Agent拥有的工具：")
print(f"- {mcp_tool.name}: {mcp_tool.description}")
print(f"- {fs_tool.name}: {fs_tool.description}")
print(f"- {custom_tool.name}: {custom_tool.description}")

# Agent现在可以自动使用这些工具！
response = agent.run("请读取my_README.md文件，并总结其中的主要内容")
print(response)