#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码示例 07: RAGTool智能问答系统
展示完整的检索→上下文构建→答案生成流程
"""

import time
from rag_tool import RAGTool
from dotenv import load_dotenv
load_dotenv()

class IntelligentQADemo:
    """智能问答演示类"""
    
    def __init__(self):
        self.rag_tool = RAGTool(
            knowledge_base_path="./qa_demo_kb",
            rag_namespace="intelligent_qa_demo"
        )
        self._setup_knowledge_base()
    
    def _setup_knowledge_base(self):
        """设置知识库"""
        print("📚 设置智能问答知识库")
        print("=" * 50)
        
        # 添加技术知识文档
        knowledge_documents = [
            {
                "id": "ai_fundamentals",
                "content": """# 人工智能基础

## 定义和历史
人工智能（Artificial Intelligence, AI）是计算机科学的一个分支，旨在创造能够执行通常需要人类智能的任务的机器。AI的概念最早由Alan Turing在1950年提出。

## 主要分支
### 机器学习（Machine Learning）
机器学习是AI的核心分支，使计算机能够从数据中学习而无需明确编程。

#### 监督学习
- 分类：预测离散标签
- 回归：预测连续数值
- 常用算法：线性回归、决策树、随机森林、SVM

#### 无监督学习
- 聚类：发现数据中的群组
- 降维：减少数据维度
- 常用算法：K-means、PCA、t-SNE

#### 强化学习
通过与环境交互学习最优策略，应用于游戏AI、机器人控制等。

### 深度学习（Deep Learning）
基于人工神经网络的机器学习方法，在图像识别、自然语言处理等领域取得突破。

#### 神经网络架构
- 前馈神经网络：最基础的网络结构
- 卷积神经网络（CNN）：专门处理图像数据
- 循环神经网络（RNN）：处理序列数据
- Transformer：基于注意力机制的架构

### 自然语言处理（NLP）
使计算机能够理解、解释和生成人类语言。

#### 核心任务
- 文本分类：判断文本类别
- 命名实体识别：提取人名、地名等
- 情感分析：判断文本情感倾向
- 机器翻译：语言间的自动翻译
- 问答系统：理解问题并生成答案
"""
            },
            {
                "id": "programming_best_practices",
                "content": """# 编程最佳实践

## 代码质量
高质量的代码应该具备可读性、可维护性和可扩展性。

### 命名规范
- 使用有意义的变量名和函数名
- 遵循一致的命名约定
- 避免使用缩写和模糊的名称

### 函数设计
- 单一职责原则：每个函数只做一件事
- 函数长度适中：通常不超过20-30行
- 参数数量合理：避免过多参数

### 代码组织
- 模块化设计：将相关功能组织在一起
- 层次化结构：清晰的目录和文件组织
- 接口设计：定义清晰的模块接口

## 测试策略
### 单元测试
- 测试单个函数或方法
- 使用断言验证预期结果
- 覆盖边界条件和异常情况

### 集成测试
- 测试模块间的交互
- 验证系统的整体功能
- 模拟真实使用场景

### 性能测试
- 测量执行时间和内存使用
- 识别性能瓶颈
- 优化关键路径

## 版本控制
### Git最佳实践
- 频繁提交，小步快跑
- 编写清晰的提交信息
- 使用分支管理功能开发
- 代码审查确保质量

### 协作开发
- 制定编码规范
- 使用Issue跟踪问题
- 文档化API和架构
- 持续集成和部署
"""
            },
            {
                "id": "system_design",
                "content": """# 系统设计原则

## 设计模式
设计模式是软件设计中常见问题的典型解决方案。

### 创建型模式
- 单例模式：确保类只有一个实例
- 工厂模式：创建对象的接口
- 建造者模式：构建复杂对象

### 结构型模式
- 适配器模式：接口适配和转换
- 装饰器模式：动态添加功能
- 组合模式：树形结构的统一处理

### 行为型模式
- 观察者模式：对象间的一对多依赖
- 策略模式：算法的封装和切换
- 命令模式：请求的封装和参数化

## 架构原则
### SOLID原则
- 单一职责原则（SRP）
- 开闭原则（OCP）
- 里氏替换原则（LSP）
- 接口隔离原则（ISP）
- 依赖倒置原则（DIP）

### 高内聚低耦合
- 模块内部元素紧密相关
- 模块间依赖关系最小化
- 提高代码的可维护性

## 性能优化
### 算法优化
- 选择合适的数据结构
- 优化算法复杂度
- 避免不必要的计算

### 系统优化
- 缓存策略：减少重复计算
- 并发处理：提高系统吞吐量
- 资源管理：合理使用内存和CPU
"""
            }
        ]
        
        # 批量添加知识文档
        for doc in knowledge_documents:
            result = self.rag_tool.run({"action":"add_text",
                                         "text":doc["content"],
                                         "document_id":doc["id"]})
            print(f"✅ 添加知识文档: {doc['id']}")
        
        print(f"📊 知识库设置完成")
    
    def demonstrate_question_understanding(self):
        """演示问题理解和分类"""
        print("\n🧠 问题理解和分类演示")
        print("-" * 50)
        
        print("问题类型分析:")
        print("• 📖 概念定义类 - '什么是...？'")
        print("• 🔍 方法询问类 - '如何...？'")
        print("• ⚖️ 对比分析类 - '...和...的区别？'")
        print("• 💡 应用场景类 - '...用于什么？'")
        print("• 🔧 实现细节类 - '...是怎么实现的？'")
        
        question_categories = [
            {
                "category": "概念定义",
                "questions": [
                    "什么是人工智能？",
                    "什么是深度学习？",
                    "什么是Transformer架构？"
                ]
            },
            {
                "category": "方法询问",
                "questions": [
                    "如何提高代码质量？",
                    "如何进行系统设计？",
                    "如何优化算法性能？"
                ]
            },
            {
                "category": "对比分析",
                "questions": [
                    "监督学习和无监督学习的区别是什么？",
                    "CNN和RNN有什么不同？",
                    "单元测试和集成测试的区别？"
                ]
            },
            {
                "category": "应用场景",
                "questions": [
                    "强化学习主要用于什么场景？",
                    "设计模式在什么情况下使用？",
                    "缓存策略适用于哪些场景？"
                ]
            }
        ]
        
        # 测试不同类型问题的处理效果
        for category_info in question_categories:
            category = category_info["category"]
            questions = category_info["questions"]
            
            print(f"\n📋 {category}问题测试:")
            
            for question in questions[:2]:  # 每类测试2个问题
                print(f"\n❓ 问题: {question}")
                
                start_time = time.time()
                answer = self.rag_tool.run({"action":"ask",
                                             "question":question,
                                             "limit":3,
                                             "include_citations":True})
                qa_time = time.time() - start_time
                
                print(f"⏱️ 响应时间: {qa_time:.3f}秒")
                print(f"🤖 回答: {answer[:300]}...")
                print("-" * 40)
    
    def demonstrate_context_construction(self):
        """演示上下文构建过程"""
        print("\n🏗️ 上下文构建过程演示")
        print("-" * 50)
        
        print("上下文构建步骤:")
        print("1. 🔍 检索相关文档片段")
        print("2. 📊 按相关性排序")
        print("3. 🧹 清理和格式化内容")
        print("4. ✂️ 智能截断保持完整性")
        print("5. 🔗 添加引用信息")
        
        # 使用复杂问题演示上下文构建
        complex_question = "如何设计一个高质量的机器学习系统？"
        
        print(f"\n❓ 复杂问题: {complex_question}")
        print("这个问题需要整合多个文档的信息...")
        
        # 先进行搜索，查看检索到的片段
        print(f"\n🔍 第一步：检索相关片段")
        search_result = self.rag_tool.run({"action":"search",
                                            "query":complex_question,
                                            "limit":4,
                                            "enable_advanced_search":True})
        print(f"检索片段: {search_result}")
        
        # 然后进行智能问答，查看完整的上下文构建
        print(f"\n🤖 第二步：构建上下文并生成答案")
        start_time = time.time()
        qa_result = self.rag_tool.run({"action":"ask",
                                        "question":complex_question,
                                        "limit":4,
                                        "enable_advanced_search":True,
                                        "include_citations":True,
                                        "max_chars":1500})
        qa_time = time.time() - start_time
        
        print(f"问答耗时: {qa_time:.3f}秒")
        print(f"完整回答: {qa_result}")
    
    def demonstrate_answer_quality_analysis(self):
        """演示答案质量分析"""
        print("\n📊 答案质量分析演示")
        print("-" * 50)
        
        print("质量评估指标:")
        print("• 🎯 相关性得分 - 检索内容与问题的匹配度")
        print("• 📚 引用完整性 - 答案来源的可追溯性")
        print("• 💡 答案完整性 - 回答的全面性和准确性")
        print("• ⚡ 响应速度 - 系统的响应时间")
        
        # 质量测试问题集
        quality_test_questions = [
            {
                "question": "什么是机器学习？",
                "expected_aspects": ["定义", "分类", "应用"],
                "difficulty": "简单"
            },
            {
                "question": "如何选择合适的机器学习算法？",
                "expected_aspects": ["数据特点", "问题类型", "性能要求"],
                "difficulty": "中等"
            },
            {
                "question": "在设计大规模系统时如何平衡性能和可维护性？",
                "expected_aspects": ["架构设计", "性能优化", "代码质量"],
                "difficulty": "复杂"
            }
        ]
        
        print(f"\n📊 答案质量测试:")
        
        quality_results = []
        
        for test_case in quality_test_questions:
            question = test_case["question"]
            difficulty = test_case["difficulty"]
            expected_aspects = test_case["expected_aspects"]
            
            print(f"\n❓ 问题: {question}")
            print(f"🎯 难度: {difficulty}")
            print(f"📋 期望涵盖: {', '.join(expected_aspects)}")
            
            # 执行问答
            start_time = time.time()
            answer = self.rag_tool.run({"action":"ask",
                                         "question":question,
                                         "limit":4,
                                         "enable_advanced_search":True,
                                         "include_citations":True})
            qa_time = time.time() - start_time
            
            # 分析答案质量
            answer_length = len(answer)
            has_citations = "参考来源" in answer
            response_time = qa_time
            
            quality_score = self._calculate_quality_score(
                answer, expected_aspects, response_time
            )
            
            quality_results.append({
                "question": question,
                "difficulty": difficulty,
                "answer_length": answer_length,
                "has_citations": has_citations,
                "response_time": response_time,
                "quality_score": quality_score
            })
            
            print(f"⏱️ 响应时间: {response_time:.3f}秒")
            print(f"📏 答案长度: {answer_length}字符")
            print(f"📚 包含引用: {'是' if has_citations else '否'}")
            print(f"⭐ 质量评分: {quality_score:.2f}/10")
            print(f"🤖 答案预览: {answer[:200]}...")
            print("-" * 50)
        
        # 质量分析总结
        self._analyze_quality_results(quality_results)
    
    def _calculate_quality_score(self, answer: str, expected_aspects: list, response_time: float) -> float:
        """计算答案质量评分"""
        score = 0.0
        
        # 内容完整性评分 (40%)
        content_score = 0
        for aspect in expected_aspects:
            if aspect.lower() in answer.lower():
                content_score += 1
        content_score = (content_score / len(expected_aspects)) * 4.0
        
        # 答案长度评分 (30%)
        length_score = min(len(answer) / 500, 1.0) * 3.0
        
        # 引用完整性评分 (20%)
        citation_score = 2.0 if "参考来源" in answer else 0.0
        
        # 响应速度评分 (10%)
        speed_score = max(0, 1.0 - (response_time - 1.0) / 5.0) * 1.0
        
        total_score = content_score + length_score + citation_score + speed_score
        return min(total_score, 10.0)
    
    def _analyze_quality_results(self, results: list):
        """分析质量测试结果"""
        print(f"\n📈 质量分析总结:")
        
        avg_score = sum(r["quality_score"] for r in results) / len(results)
        avg_time = sum(r["response_time"] for r in results) / len(results)
        citation_rate = sum(1 for r in results if r["has_citations"]) / len(results)
        
        print(f"平均质量评分: {avg_score:.2f}/10")
        print(f"平均响应时间: {avg_time:.3f}秒")
        print(f"引用完整率: {citation_rate:.1%}")
        
        # 按难度分析
        difficulty_analysis = {}
        for result in results:
            difficulty = result["difficulty"]
            if difficulty not in difficulty_analysis:
                difficulty_analysis[difficulty] = []
            difficulty_analysis[difficulty].append(result["quality_score"])
        
        print(f"\n📊 按难度分析:")
        for difficulty, scores in difficulty_analysis.items():
            avg_difficulty_score = sum(scores) / len(scores)
            print(f"  {difficulty}: {avg_difficulty_score:.2f}/10")
    
    def demonstrate_prompt_engineering(self):
        """演示提示词工程"""
        print("\n🎨 提示词工程演示")
        print("-" * 50)
        
        print("提示词设计要素:")
        print("• 🎯 系统角色定义")
        print("• 📋 任务明确描述")
        print("• 🔍 上下文信息注入")
        print("• 📝 输出格式要求")
        print("• 🚫 限制和约束条件")
        
        # 演示不同的提示词策略
        prompt_strategies = [
            {
                "name": "基础提示",
                "system_prompt": "你是一个AI助手，请回答用户的问题。",
                "description": "简单直接的角色定义"
            },
            {
                "name": "专业提示",
                "system_prompt": """你是一个专业的技术顾问，具备以下能力：
1. 深入理解技术概念和原理
2. 提供准确可靠的技术建议
3. 用清晰简洁的语言解释复杂概念
4. 基于提供的上下文信息回答问题""",
                "description": "详细的能力描述和要求"
            },
            {
                "name": "结构化提示",
                "system_prompt": """你是一个专业的知识助手，请按以下要求回答：
【理解】仔细分析问题的核心意图
【检索】基于提供的上下文信息
【整合】从多个片段提取关键信息
【回答】用结构化格式清晰表达
【引用】标注信息来源和依据""",
                "description": "结构化的处理流程"
            }
        ]
        
        test_question = "什么是深度学习，它有哪些主要应用？"
        
        print(f"\n🧪 提示词策略对比测试:")
        print(f"测试问题: {test_question}")
        
        for strategy in prompt_strategies:
            print(f"\n📝 {strategy['name']} ({strategy['description']}):")
            
            # 这里简化演示，实际的提示词工程在RAGTool内部实现
            start_time = time.time()
            answer = self.rag_tool.run({"action":"ask",
                                         "question":test_question,
                                         "limit":3})
            response_time = time.time() - start_time
            
            print(f"⏱️ 响应时间: {response_time:.3f}秒")
            print(f"🤖 回答长度: {len(answer)}字符")
            print(f"📄 回答预览: {answer[:250]}...")
    
    def demonstrate_citation_system(self):
        """演示引用系统"""
        print("\n📚 引用系统演示")
        print("-" * 50)
        
        print("引用系统特点:")
        print("• 🔗 自动标注信息来源")
        print("• 📊 显示相似度得分")
        print("• 📄 提供文档定位")
        print("• ✅ 确保答案可追溯性")
        
        citation_test_questions = [
            "机器学习有哪些主要类型？",
            "如何进行代码质量管理？",
            "系统设计中的SOLID原则是什么？"
        ]
        
        print(f"\n📚 引用系统测试:")
        
        for question in citation_test_questions:
            print(f"\n❓ 问题: {question}")
            
            # 启用引用的问答
            answer_with_citations = self.rag_tool.run({"action":"ask",
                                                        "question":question,
                                                        "limit":3,
                                                        "include_citations":True})
            
            # 禁用引用的问答对比
            answer_without_citations = self.rag_tool.run({"action":"ask",
                                                           "question":question,
                                                           "limit":3,
                                                           "include_citations":False})
            
            print(f"🔗 带引用回答: {answer_with_citations[:400]}...")
            print(f"📝 无引用回答: {answer_without_citations[:200]}...")
            
            # 分析引用信息
            citation_count = answer_with_citations.count("参考来源")
            print(f"📊 引用分析: 包含 {citation_count} 个引用来源")

def main():
    """主函数"""
    print("🤖 RAGTool智能问答系统演示")
    print("展示完整的检索→上下文构建→答案生成流程")
    print("=" * 70)
    
    try:
        demo = IntelligentQADemo()
        
        # 1. 问题理解和分类演示
        demo.demonstrate_question_understanding()
        
        # 2. 上下文构建过程演示
        demo.demonstrate_context_construction()
        
        # 3. 答案质量分析演示
        demo.demonstrate_answer_quality_analysis()
        
        # 4. 提示词工程演示
        demo.demonstrate_prompt_engineering()
        
        # 5. 引用系统演示
        demo.demonstrate_citation_system()
        
        print("\n" + "=" * 70)
        print("🎉 智能问答系统演示完成！")
        print("=" * 70)
        
        print("\n✨ 智能问答核心能力:")
        print("1. 🧠 问题理解 - 准确识别问题类型和意图")
        print("2. 🔍 智能检索 - 多策略检索相关内容")
        print("3. 🏗️ 上下文构建 - 智能整合检索结果")
        print("4. 🤖 答案生成 - 基于上下文的准确回答")
        print("5. 📚 引用标注 - 完整的来源追溯")
        
        print("\n🎯 技术优势:")
        print("• 语义理解 - 深度理解问题语义和意图")
        print("• 上下文感知 - 充分利用检索上下文")
        print("• 质量保证 - 多层次的质量控制机制")
        print("• 可追溯性 - 完整的答案来源追溯")
        
        print("\n💡 应用场景:")
        print("• 技术支持 - 自动回答技术问题")
        print("• 知识问答 - 企业内部知识查询")
        print("• 学习辅导 - 个性化学习问答")
        print("• 文档助手 - 快速理解复杂文档")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()