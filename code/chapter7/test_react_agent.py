# test_react_agent.py
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ToolRegistry
from my_react_agent import MyReActAgent

# 加载环境变量
load_dotenv()

def test_react_agent():
    """测试MyReActAgent的功能"""
    
    # 创建LLM实例
    llm = HelloAgentsLLM()
    
    # 创建工具注册表
    tool_registry = ToolRegistry()
    
    # 注册一些基础工具用于测试
    print("🔧 注册测试工具...")
    
    # 注册计算器工具
    try:
        from hello_agents import calculate
        tool_registry.register_function("calculate", "执行数学计算，支持基本的四则运算", calculate)
        print("✅ 计算器工具注册成功")
    except ImportError:
        print("⚠️ 计算器工具未找到，跳过注册")

    # 注册搜索工具（如果可用）
    try:
        from hello_agents import search
        tool_registry.register_function("search", "搜索互联网信息", search)
        print("✅ 搜索工具注册成功")
    except ImportError:
        print("⚠️ 搜索工具未找到，跳过注册")
    
    # 创建自定义ReActAgent
    agent = MyReActAgent(
        name="我的推理行动助手",
        llm=llm,
        tool_registry=tool_registry,
        max_steps=5
    )
    
    print("\n" + "="*60)
    print("开始测试 MyReActAgent")
    print("="*60)
    
    # 测试1：数学计算问题
    print("\n📊 测试1：数学计算问题")
    math_question = "请帮我计算：(25 + 15) * 3 - 8 的结果是多少？"
    
    try:
        result1 = agent.run(math_question)
        print(f"\n🎯 测试1结果: {result1}")
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
    
    # 测试2：需要搜索的问题
    print("\n🔍 测试2：信息搜索问题")
    search_question = "Python编程语言是什么时候发布的？请告诉我具体的年份。"
    
    try:
        result2 = agent.run(search_question)
        print(f"\n🎯 测试2结果: {result2}")
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
    
    # 测试3：复合问题（需要多步推理）
    print("\n🧠 测试3：复合推理问题")
    complex_question = "如果一个班级有30个学生，其中60%是女生，那么男生有多少人？请先计算女生人数，再计算男生人数。"
    
    try:
        result3 = agent.run(complex_question)
        print(f"\n🎯 测试3结果: {result3}")
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
    
    # 查看对话历史
    print(f"\n📝 对话历史记录: {len(agent.get_history())} 条消息")
    
    # 显示工具使用统计
    print(f"\n🛠️ 可用工具数量: {len(tool_registry._tools)}")
    print("已注册的工具:")
    for tool_name in tool_registry._tools.keys():
        print(f"  - {tool_name}")
    
    print("\n🎉 测试完成！")

def test_custom_prompt():
    """测试自定义提示词的ReActAgent"""
    
    print("\n" + "="*60)
    print("测试自定义提示词的 MyReActAgent")
    print("="*60)
    
    # 创建LLM和工具注册表
    llm = HelloAgentsLLM()
    tool_registry = ToolRegistry()
    
    # 注册计算器工具
    try:
        from hello_agents import calculate
        tool_registry.register_function("calculate", "数学计算工具", calculate)
    except ImportError:
        pass
    
    # 自定义提示词（更简洁的版本）
    custom_prompt = """你是一个数学专家AI助手。

可用工具：{tools}

请按以下格式回应：
Thought: [你的思考]
Action: [tool_name[input] 或 Finish[答案]]

问题：{question}
历史：{history}

开始："""
    
    # 创建使用自定义提示词的Agent
    custom_agent = MyReActAgent(
        name="数学专家助手",
        llm=llm,
        tool_registry=tool_registry,
        max_steps=3,
        custom_prompt=custom_prompt
    )
    
    # 测试数学问题
    math_question = "计算 15 × 8 + 32 ÷ 4 的结果"
    
    try:
        result = custom_agent.run(math_question)
        print(f"\n🎯 自定义提示词测试结果: {result}")
    except Exception as e:
        print(f"❌ 自定义提示词测试失败: {e}")

if __name__ == "__main__":
    # 运行基础测试
    test_react_agent()
    
    # 运行自定义提示词测试
    test_custom_prompt()
    
    print("\n✨ 所有测试完成！")
