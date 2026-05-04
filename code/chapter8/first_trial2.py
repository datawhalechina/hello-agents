from dotenv import load_dotenv

load_dotenv()

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import MemoryTool

# 创建具有记忆能力的 Agent
llm = HelloAgentsLLM()
agent = SimpleAgent(name="记忆助手", llm=llm)

# 新版 MemoryTool 无 execute()，统一用 run({"action": ...})。
# 语义记忆依赖 Neo4j Aura；若出现路由/SSL/连接被重置，可先仅用情景记忆（仍用 Qdrant）。
_demo_memory_type = "semantic"
try:
    memory_tool = MemoryTool(user_id="user123")
except Exception as e:
    err = str(e).lower()
    if "neo4j" in err or "routing" in err or "connection" in err:
        print(f"⚠️ 语义记忆（Neo4j）不可用，改为 working + episodic：{e}\n")
        memory_tool = MemoryTool(
            user_id="user123",
            memory_types=["working", "episodic"],
        )
        _demo_memory_type = "episodic"
    else:
        raise

tool_registry = ToolRegistry()
tool_registry.register_tool(memory_tool)
agent.tool_registry = tool_registry

print("=== 添加多个记忆 ===")

result1 = memory_tool.run(
    {
        "action": "add",
        "content": "用户张三是一名Python开发者，专注于机器学习和数据分析",
        "memory_type": _demo_memory_type,
        "importance": 0.8,
    }
)
print(f"记忆1: {result1}")

result2 = memory_tool.run(
    {
        "action": "add",
        "content": "李四是前端工程师，擅长React和Vue.js开发",
        "memory_type": _demo_memory_type,
        "importance": 0.7,
    }
)
print(f"记忆2: {result2}")

result3 = memory_tool.run(
    {
        "action": "add",
        "content": "王五是产品经理，负责用户体验设计和需求分析",
        "memory_type": _demo_memory_type,
        "importance": 0.6,
    }
)
print(f"记忆3: {result3}")

print("\n=== 搜索特定记忆 ===")
print("🔍 搜索 '前端工程师':")
print(
    memory_tool.run(
        {"action": "search", "query": "前端工程师", "limit": 3}
    )
)

print("\n=== 记忆摘要 ===")
print(memory_tool.run({"action": "summary"}))
