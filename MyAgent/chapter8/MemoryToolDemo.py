from MyAgent.Memory.tools.builtin.memory_tool import MemoryTool


def memory_tool_execute_demo():
    """MemoryTool execute方法演示"""
    print("🧠 MemoryTool基础操作演示")
    print("=" * 50)

    # 初始化MemoryTool
    memory_tool = MemoryTool(
        user_id="demo_user",
        memory_types=["working", "episodic", "semantic", "perceptual"]
    )

    print("✅ MemoryTool初始化完成")
    print(f"📋 支持的操作: add, search, summary, stats, update, remove, forget, consolidate, clear_all")

    return memory_tool



def add_memory_demo(memory_tool):
    """添加记忆演示 - 模拟人类记忆编码过程"""
    print("\n📝 添加记忆演示")
    print("-" * 30)

    # 添加工作记忆
    result = memory_tool.run({
        "action": "add",
        "content": "正在学习HelloAgents框架的记忆系统",
        "memory_type": "working",
        "importance": 0.7,
        "task_type": "learning"
    })
    print(f"工作记忆: {result}")


def search_memory_demo(memory_tool):
    """搜索记忆演示 - 实现语义理解的检索"""
    print("\n🔍 搜索记忆演示")
    print("-" * 30)

    # 基础搜索
    print("基础搜索 - '记忆系统':")

    # 按类型搜索
    print("\n按类型搜索 - 语义记忆中的'记忆':")
    result = memory_tool.run({
        "action": "search",
        "query": "记忆",
        "memory_type": "working",
        "limit": 2
    })
    print(result)

    # 设置重要性阈值
    print("\n高重要性记忆搜索:")
    result = memory_tool.run({
        "action": "search",
        "query": "AI Agent",
        "min_importance": 0.7,
        "limit": 3
    })
    print(result)


def main():
    """主函数"""
    print("🚀 MemoryTool基础操作完整演示")
    print("展示记忆系统的核心功能和操作方法")
    print("=" * 60)
    try:
        # 1. 初始化MemoryTool
        memory_tool = memory_tool_execute_demo()
        add_memory_demo(memory_tool)
        search_memory_demo(memory_tool)

    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()