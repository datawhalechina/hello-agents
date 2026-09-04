#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码示例 08: Agent工具集成
展示如何在HelloAgents框架中集成MemoryTool和RAGTool
"""

from dotenv import load_dotenv
load_dotenv()
import time
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from memory_tool import MemoryTool
from rag_tool import RAGTool

class AgentIntegrationDemo:
    """Agent工具集成演示类"""
    
    def __init__(self):
        self.setup_agent()
    
    def setup_agent(self):
        """设置Agent和工具"""
        print("🤖 Agent工具集成设置")
        print("=" * 50)
        
        # 初始化工具
        print("1. 初始化工具...")
        self.memory_tool = MemoryTool(
            user_id="agent_integration_user",
            memory_types=["working", "episodic", "semantic", "perceptual"]
        )
        
        self.rag_tool = RAGTool(
            knowledge_base_path="./agent_integration_kb",
            rag_namespace="agent_demo"
        )
        
        print("✅ MemoryTool和RAGTool初始化完成")
        
        # 注册工具
        print("\n2. 注册工具...")
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(self.memory_tool)
        self.tool_registry.register_tool(self.rag_tool)
        print("✅ 工具注册完成")

        # 创建Agent
        print("\n3. 创建Agent...")
        self.llm = HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="智能学习助手",
            llm=self.llm,
            system_prompt="集成记忆和RAG功能的智能助手",
            tool_registry=self.tool_registry
        )
        print("✅ Agent创建完成")
        
        # 显示Agent状态
        print(f"\n📊 Agent状态:")
        print(f"  名称: {self.agent.name}")
        print(f"  描述: {self.agent.system_prompt}")
        print(f"  可用工具: {list(self.tool_registry._tools.keys())}")
    
    def demonstrate_tool_registry_pattern(self):
        """演示工具注册模式"""
        print("\n🔧 工具注册模式演示")
        print("-" * 50)
        
        print("工具注册模式特点:")
        print("• 🔌 统一的工具接口")
        print("• 📋 集中的工具管理")
        print("• 🔄 动态工具加载")
        print("• 🎯 工具能力发现")
        
        # 演示工具注册过程
        print(f"\n🔧 工具注册详情:")
        
        for tool_name, tool_instance in self.tool_registry._tools.items():
            print(f"\n工具: {tool_name}")
            print(f"  类型: {type(tool_instance).__name__}")
            print(f"  描述: {tool_instance.description}")
            
            # 显示工具的主要功能
            if tool_name == "memory":
                print(f"  主要功能: 记忆管理、搜索、整合、遗忘")
                print(f"  记忆类型: {tool_instance.memory_types}")
            elif tool_name == "rag":
                print(f"  主要功能: 文档处理、智能问答、知识检索")
                print(f"  命名空间: {tool_instance.rag_namespace}")
        
        # 演示工具发现机制
        print(f"\n🔍 工具能力发现:")
        available_tools = self.tool_registry.list_tools()
        print(f"可用工具列表: {available_tools}")
        
        # 演示工具获取
        memory_tool = self.tool_registry.get_tool("memory")
        rag_tool = self.tool_registry.get_tool("rag")
        
        print(f"\n✅ 工具获取成功:")
        print(f"  Memory工具: {type(memory_tool).__name__}")
        print(f"  RAG工具: {type(rag_tool).__name__}")
    
    def demonstrate_unified_interface(self):
        """演示统一接口模式"""
        print("\n🔗 统一接口模式演示")
        print("-" * 50)
        
        print("统一接口优势:")
        print("• 🎯 一致的调用方式")
        print("• 📝 标准化的参数传递")
        print("• 🛡️ 统一的错误处理")
        print("• 🔄 简化的工具切换")
        
        # 演示统一的run接口
        print(f"\n🔗 统一run接口演示:")
        
        # Memory工具操作
        print(f"\n1. Memory工具操作:")
        memory_operations = [
            ("add", {
                "content": "学习了Agent工具集成模式",
                "memory_type": "episodic",
                "importance": 0.8,
                "topic": "agent_integration"
            }),
            ("search", {
                "query": "Agent集成",
                "limit": 2
            }),
            ("stats", {})
        ]
        
        for operation, params in memory_operations:
            print(f"  操作: memory.run('{operation}', {params})")
            result = self.memory_tool.run({"action":operation, **params})
            print(f"  结果: {str(result)[:100]}...")
        
        # RAG工具操作
        print(f"\n2. RAG工具操作:")
        
        # 先添加一些内容
        self.rag_tool.run({"action":"add_text",
                            "text":"Agent工具集成是HelloAgents框架的核心特性，允许Agent使用多种工具来完成复杂任务。",
                            "document_id":"agent_integration_guide"})
        
        rag_operations = [
            ("search", {
                "query": "Agent工具集成",
                "limit": 2
            }),
            ("ask", {
                "question": "什么是Agent工具集成？",
                "limit": 2
            }),
            ("stats", {})
        ]
        
        for operation, params in rag_operations:
            print(f"  操作: rag.run('{operation}', {params})")
            result = self.rag_tool.run({"action":operation, **params})
            print(f"  结果: {str(result)[:100]}...")
    
    def demonstrate_collaborative_workflow(self):
        """演示协同工作流程"""
        print("\n🤝 协同工作流程演示")
        print("-" * 50)
        
        print("协同工作场景:")
        print("• 📚 学习新知识 → RAG存储 + Memory记录")
        print("• 🔍 回顾学习历程 → Memory检索 + RAG补充")
        print("• 💡 知识应用 → RAG查询 + Memory更新")
        print("• 📊 学习分析 → 两工具统计整合")
        
        # 场景1：学习新知识
        print(f"\n📚 场景1：学习新知识")
        
        # 向RAG添加学习资料
        learning_content = """# 设计模式：观察者模式

## 定义
观察者模式定义了对象间的一对多依赖关系，当一个对象的状态发生改变时，所有依赖它的对象都会得到通知并自动更新。

## 结构
- Subject（主题）：维护观察者列表，提供注册和删除观察者的方法
- Observer（观察者）：定义更新接口
- ConcreteSubject（具体主题）：实现主题接口
- ConcreteObserver（具体观察者）：实现观察者接口

## 应用场景
- GUI事件处理
- 模型-视图架构
- 发布-订阅系统
"""
        
        rag_result = self.rag_tool.run({"action":"add_text",
                                         "text":learning_content,
                                         "document_id":"observer_pattern"})
        print(f"RAG添加结果: {rag_result}")
        
        # 记录学习活动到记忆系统
        memory_result = self.memory_tool.run({"action":"add",
                                                "content":"学习了观察者设计模式的定义、结构和应用场景",
                                                "memory_type":"episodic",
                                                "importance":0.8,
                                                "topic":"design_patterns",
                                                "pattern_type":"observer"})
        print(f"Memory记录结果: {memory_result}")
        
        # 场景2：回顾学习历程
        print(f"\n🔍 场景2：回顾学习历程")
        
        # 从记忆系统检索学习历史
        memory_search = self.memory_tool.run({"action":"search",
                                                "query":"设计模式学习",
                                                "limit":3})
        print(f"学习历史回顾: {memory_search}")
        
        # 从RAG获取相关知识补充
        rag_search = self.rag_tool.run({"action":"search",
                                         "query":"观察者模式",
                                         "limit":2})
        print(f"知识内容补充: {rag_search}")
        
        # 场景3：知识应用
        print(f"\n💡 场景3：知识应用")
        
        # 通过RAG查询应用方法
        application_query = self.rag_tool.run({"action":"ask",
                                                "question":"观察者模式适用于什么场景？",
                                                "limit":2})
        print(f"应用场景查询: {application_query}")
        
        # 记录应用实践到记忆
        application_memory = self.memory_tool.run({"action":"add",
                                                     "content":"查询了观察者模式的应用场景，准备在GUI项目中使用",
                                                     "memory_type":"working",
                                                     "importance":0.7,
                                                     "application_context":"gui_project"})
        print(f"应用记录: {application_memory}")
        
        # 场景4：学习分析
        print(f"\n📊 场景4：学习分析")
        
        # 获取记忆系统统计
        memory_stats = self.memory_tool.run({"action":"stats"})
        print(f"记忆统计: {memory_stats}")
        
        # 获取RAG系统统计
        rag_stats = self.rag_tool.run({"action":"stats"})
        print(f"知识库统计: {rag_stats}")
        
        # 生成学习摘要
        learning_summary = self.memory_tool.run({"action":"summary", "limit":5})
        print(f"学习摘要: {learning_summary}")
    
    def demonstrate_agent_orchestration(self):
        """演示Agent编排能力"""
        print("\n🎭 Agent编排能力演示")
        print("-" * 50)
        
        print("Agent编排特点:")
        print("• 🧠 智能工具选择")
        print("• 🔄 工具链式调用")
        print("• 📊 结果整合分析")
        print("• 🎯 目标导向执行")
        
        # 模拟复杂任务的工具编排
        print(f"\n🎭 复杂任务编排示例:")
        print(f"任务: 创建一个关于机器学习的学习计划")
        
        # 步骤1：从RAG获取机器学习知识结构
        print(f"\n步骤1: 获取知识结构")
        
        # 添加机器学习知识
        ml_content = """# 机器学习学习路径

## 基础阶段
1. 数学基础：线性代数、概率统计、微积分
2. 编程基础：Python、NumPy、Pandas
3. 机器学习概念：监督学习、无监督学习、强化学习

## 进阶阶段
1. 算法实现：从零实现经典算法
2. 深度学习：神经网络、CNN、RNN、Transformer
3. 实践项目：端到端机器学习项目

## 高级阶段
1. 模型优化：超参数调优、模型压缩
2. 部署运维：模型部署、监控、更新
3. 前沿技术：最新论文、开源项目
"""
        
        self.rag_tool.run({"action":"add_text",
                            "text":ml_content,
                            "document_id":"ml_learning_path"})
        
        knowledge_structure = self.rag_tool.run({"action":"ask",
                                                  "question":"机器学习的学习路径是什么？",
                                                  "limit":3})
        print(f"知识结构: {knowledge_structure[:200]}...")
        
        # 步骤2：记录学习计划到记忆系统
        print(f"\n步骤2: 记录学习计划")
        
        plan_memory = self.memory_tool.run({"action":"add",
                                             "content":"制定了机器学习学习计划，包括基础、进阶、高级三个阶段",
                                             "memory_type":"episodic",
                                             "importance":0.9,
                                             "plan_type":"learning",
                                             "subject":"machine_learning"})
        print(f"计划记录: {plan_memory}")
        
        # 步骤3：检索相关学习经验
        print(f"\n步骤3: 检索学习经验")
        
        experience_search = self.memory_tool.run({"action":"search",
                                                    "query":"学习计划 学习经验",
                                                    "limit":3})
        print(f"相关经验: {experience_search}")
        
        # 步骤4：整合生成最终建议
        print(f"\n步骤4: 生成最终建议")
        
        final_advice = self.rag_tool.run({"action":"ask",
                                            "question":"如何制定有效的机器学习学习计划？",
                                            "limit":4})
        print(f"最终建议: {final_advice[:300]}...")
        
        # 记录编排过程
        orchestration_memory = self.memory_tool.run({"action":"add",
                                                       "content":"完成了复杂的学习计划制定任务，使用了RAG和Memory的协同编排",
                                                       "memory_type":"working",
                                                       "importance":0.8,
                                                       "task_type":"orchestration"})
        print(f"\n编排记录: {orchestration_memory}")
    
    def demonstrate_performance_analysis(self):
        """演示性能分析"""
        print("\n📊 性能分析演示")
        print("-" * 50)
        
        print("性能分析指标:")
        print("• ⏱️ 工具响应时间")
        print("• 🔄 工具切换开销")
        print("• 💾 内存使用情况")
        print("• 🎯 任务完成效率")
        
        # 性能测试
        print(f"\n📊 性能测试:")
        
        # 单工具性能测试
        print(f"\n1. 单工具性能:")
        
        # Memory工具性能
        start_time = time.time()
        for i in range(5):
            self.memory_tool.run({"action":"add",
                                   "content":f"性能测试记忆 {i+1}",
                                   "memory_type":"working",
                                   "importance":0.5})
        memory_time = time.time() - start_time
        print(f"Memory工具 - 5次添加操作: {memory_time:.3f}秒")
        
        # RAG工具性能
        start_time = time.time()
        for i in range(3):
            self.rag_tool.run({"action":"search",
                                "query":f"测试查询 {i+1}",
                                "limit":2})
        rag_time = time.time() - start_time
        print(f"RAG工具 - 3次搜索操作: {rag_time:.3f}秒")
        
        # 协同工作性能测试
        print(f"\n2. 协同工作性能:")
        
        start_time = time.time()
        
        # 模拟协同工作流程
        self.rag_tool.run({"action":"add_text",
                            "text":"这是一个性能测试文档",
                            "document_id":"perf_test"})
        
        self.memory_tool.run({"action":"add",
                                "content":"执行了性能测试",
                                "memory_type":"working",
                                "importance":0.6})
        
        rag_result = self.rag_tool.run({"action":"search",
                                         "query":"性能测试",
                                         "limit":1})
        
        memory_result = self.memory_tool.run({"action":"search",
                                                "query":"性能测试",
                                                "limit":1})
        
        collaborative_time = time.time() - start_time
        print(f"协同工作流程: {collaborative_time:.3f}秒")
        
        # 性能分析总结
        print(f"\n📈 性能分析总结:")
        print(f"Memory工具平均响应: {memory_time/5:.3f}秒/操作")
        print(f"RAG工具平均响应: {rag_time/3:.3f}秒/操作")
        print(f"协同工作效率: {collaborative_time:.3f}秒/流程")
        
        # 获取最终统计
        final_memory_stats = self.memory_tool.run({"action":"stats"})
        final_rag_stats = self.rag_tool.run({"action":"stats"})
        
        print(f"\n📊 最终系统状态:")
        print(f"Memory系统: {final_memory_stats}")
        print(f"RAG系统: {final_rag_stats}")

def main():
    """主函数"""
    print("🤖 Agent工具集成演示")
    print("展示如何在HelloAgents框架中集成MemoryTool和RAGTool")
    print("=" * 70)
    
    try:
        demo = AgentIntegrationDemo()
        
        # 1. 工具注册模式演示
        demo.demonstrate_tool_registry_pattern()
        
        # 2. 统一接口模式演示
        demo.demonstrate_unified_interface()
        
        # 3. 协同工作流程演示
        demo.demonstrate_collaborative_workflow()
        
        # 4. Agent编排能力演示
        demo.demonstrate_agent_orchestration()
        
        # 5. 性能分析演示
        demo.demonstrate_performance_analysis()
        
        print("\n" + "=" * 70)
        print("🎉 Agent工具集成演示完成！")
        print("=" * 70)
        
        print("\n✨ Agent集成核心特性:")
        print("1. 🔧 工具注册模式 - 统一的工具管理和发现")
        print("2. 🔗 统一接口设计 - 一致的工具调用方式")
        print("3. 🤝 协同工作流程 - 工具间的智能协作")
        print("4. 🎭 智能编排能力 - 复杂任务的自动分解")
        print("5. 📊 性能监控分析 - 全面的性能评估")
        
        print("\n🎯 设计优势:")
        print("• 模块化 - 工具独立开发，灵活组合")
        print("• 可扩展 - 支持动态添加新工具")
        print("• 高内聚 - 每个工具专注特定功能")
        print("• 低耦合 - 工具间依赖关系最小")
        
        print("\n💡 应用价值:")
        print("• 智能助手 - 构建多功能智能助手")
        print("• 知识管理 - 企业级知识管理系统")
        print("• 学习平台 - 个性化学习支持系统")
        print("• 决策支持 - 基于知识和经验的决策")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
