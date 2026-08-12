from hello_agents.tools import MCPTool

web_search_tool = MCPTool(name="web research", server_command=["npx", "-y", "@mzxrai/mcp-webresearch@latest"])

result = web_search_tool.run({"action": "list_tools"})
print(result)

result = web_search_tool.run({
    "action": "call_tool",
    "tool_name": "visit_page",
    "arguments": {
        "url": "https://www.xiangha.com/so/?q=caipu&s=五花肉"
    }
})

print(result)

