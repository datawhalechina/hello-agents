"""
ContextBuilder 基础使用示例

展示如何使用 ContextBuilder 构建优化的上下文，包括：
1. 初始化 ContextBuilder
2. 准备对话历史
3. 添加记忆
4. 构建结构化上下文
"""
from dotenv import load_dotenv
load_dotenv()
from hello_agents.context import ContextBuilder, ContextConfig
from hello_agents.tools import MemoryTool, RAGTool
from hello_agents.core.message import Message
from datetime import datetime


def main():
    print("=" * 80)
    print("ContextBuilder 基础使用示例")
    print("=" * 80 + "\n")

    # 1. 初始化工具（Optional）
    print("1. 初始化工具...")
    memory_tool = MemoryTool(user_id="user123")
    rag_tool = RAGTool(knowledge_base_path="./knowledge_base")

    # 2. 创建 ContextBuilder
    print("2. 创建 ContextBuilder...")
    config = ContextConfig(
        max_tokens=3000,
        reserve_ratio=0.2,
        min_relevance=0,#最小相关性阈值，0代表所有历史信息会被保留,
        enable_compression=True
    )

    builder = ContextBuilder(
        memory_tool=memory_tool,
        rag_tool=rag_tool,
        config=config
    )

    # 3. 准备对话历史
    print("3. 准备对话历史...")
    conversation_history = [
        Message(content="我正在开发一个数据分析工具", role="user", timestamp=datetime.now()),
        Message(content="很好!数据分析工具通常需要处理大量数据。您计划使用什么技术栈?", role="assistant", timestamp=datetime.now()),
        Message(content="我打算使用Python和Pandas,已经完成了CSV读取模块", role="user", timestamp=datetime.now()),
        Message(content="不错的选择!Pandas在数据处理方面非常强大。接下来您可能需要考虑数据清洗和转换。", role="assistant", timestamp=datetime.now()),
    ]

    # 4. 添加一些记忆
    print("4. 添加记忆...")
    memory_tool.run({
        "action": "add",
        "content": "用户正在开发数据分析工具,使用Python和Pandas",
        "memory_type": "semantic",
        "importance": 0.8
    })

    memory_tool.run({
        "action": "add",
        "content": "已完成CSV读取模块的开发",
        "memory_type": "episodic",
        "importance": 0.7
    })

    # 5. 构建上下文
    print("5. 构建上下文...\n")
    context_str = builder.build(
        user_query="如何优化Pandas的内存占用?",
        conversation_history=conversation_history,
        system_instructions="你是一位资深的Python数据工程顾问。你的回答需要:1) 提供具体可行的建议 2) 解释技术原理 3) 给出代码示例"
    )

    print("=" * 80)
    print("构建的上下文 (结构化字符串):")
    print("=" * 80)
    print(context_str)
    print("=" * 80)
    print()

    # 6. 将上下文字符串转换为消息格式供 LLM 使用
    print("6. 将上下文传给 LLM...")
    messages = [
        {"role": "system", "content": context_str},
        {"role": "user", "content": "请回答"}

    ]

    from hello_agents.core.llm import HelloAgentsLLM
    llm = HelloAgentsLLM()
    # 注意: 实际使用时需要配置 LLM
    response = llm.invoke(messages)
    print(f"LLM 回答: {response}")

    print("✅ ContextBuilder 演示完成!")
    print("\n提示: ContextBuilder 返回的是结构化的上下文字符串,")
    print("      可以直接作为 system message 传给 LLM。")


if __name__ == "__main__":
    main()
