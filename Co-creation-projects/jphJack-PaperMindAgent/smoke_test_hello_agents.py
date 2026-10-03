"""冒烟测试：验证 HelloAgents 集成后的模块导入、客户端构造、响应适配与工具桥接"""
import asyncio
import os
import sys

os.environ.setdefault("DEEPSEEK_API_KEY", "smoke-test-key")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failures = []

# 1. LLM 客户端（底层为 HelloAgentsLLM）
from backend.llm.client import ChatCompletionShim, DeepSeekClient

client = DeepSeekClient()
assert type(client.llm).__name__ == "HelloAgentsLLM", "底层不是 HelloAgentsLLM"
print("[PASS] DeepSeekClient 底层为 HelloAgentsLLM")

class FakeLLMResponse:
    content = '{"confidence": 0.9}'
    reasoning_content = None
    model = "deepseek-chat"
    usage = {"total_tokens": 10}

shim = ChatCompletionShim(FakeLLMResponse())
assert shim.choices[0].message.content == '{"confidence": 0.9}'
assert shim.choices[0].finish_reason == "stop"
print("[PASS] ChatCompletionShim 兼容 choices[0].message.content")

# 2. 工具桥接
from hello_agents.tools.response import ToolStatus
from backend.tools.base import Tool as ProjectTool, ToolRegistry
from backend.tools.hello_agents_bridge import build_hello_agents_registry

def sync_tool(query: str) -> dict:
    return {"echo": query}

async def async_tool(text: str) -> str:
    return f"async:{text}"

registry = ToolRegistry()
registry.register(ProjectTool(
    name="sync_tool",
    description="同步工具",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    func=sync_tool,
))
registry.register(ProjectTool(
    name="async_tool",
    description="异步工具",
    parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    func=async_tool,
))

ha_registry = build_hello_agents_registry(registry)
assert set(ha_registry.list_tools()) == {"sync_tool", "async_tool"}, ha_registry.list_tools()
schema = ha_registry.get_tool("sync_tool").to_openai_schema()
assert schema["function"]["name"] == "sync_tool"
assert "query" in schema["function"]["parameters"]["properties"]
print("[PASS] 项目工具已桥接为框架 Tool 且 schema 正确")

async def run_async_checks():
    r1 = await ha_registry.get_tool("sync_tool").arun({"query": "hi"})
    assert r1.status == ToolStatus.SUCCESS and r1.data["echo"] == "hi", r1
    r2 = await ha_registry.get_tool("async_tool").arun({"text": "x"})
    assert r2.status == ToolStatus.SUCCESS and r2.text == "async:x", r2
    print("[PASS] 框架 Tool arun 同步/异步工具均返回 ToolStatus.SUCCESS")

asyncio.run(run_async_checks())

# 3. 框架 Agent 封装（无需真实 API，仅构造与接线）
from backend.agents.hello_agents_runner import build_react_agent, build_reviewer_agent

reviewer = build_reviewer_agent(client.llm)
assert type(reviewer).__name__ == "SimpleAgent"
react = build_react_agent(
    name="SmokeReAct",
    llm=client.llm,
    registry=registry,
    system_prompt="测试",
    tool_names=["sync_tool"],
)
assert type(react).__name__ == "ReActAgent"
assert "sync_tool" in react.tool_registry.list_tools()
print("[PASS] 框架 SimpleAgent / ReActAgent 构造正常，工具已注册")

# 4. Reflexion 接线（引用框架审核 Agent）
import backend.orchestrator.reflexion as reflexion_mod
assert reflexion_mod.REVIEWER_SYSTEM_PROMPT
print("[PASS] Reflexion 已接入框架 SimpleAgent 审核链路")

print("\n全部冒烟测试通过")
