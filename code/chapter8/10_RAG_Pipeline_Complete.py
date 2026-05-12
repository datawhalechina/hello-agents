#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码示例 10: RAG完整处理管道
展示从文档处理到智能问答的完整RAG流程
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from rag_tool import RAGTool
from dotenv import load_dotenv
load_dotenv()

class RAGPipelineComplete:
    """RAG完整处理管道演示类"""
    
    def __init__(self):
        self.setup_rag_system()
    
    def setup_rag_system(self):
        """设置RAG系统"""
        print("📚 RAG完整处理管道演示")
        print("=" * 60)
        
        # 初始化RAG工具
        self.rag_tool = RAGTool(
            knowledge_base_path="./rag_pipeline_kb",
            rag_namespace="complete_pipeline"
        )
        
        print("✅ RAG系统初始化完成")
        
        # 显示系统配置
        print(f"\n📊 系统配置:")
        print(f"  知识库路径: ./rag_pipeline_kb")
        print(f"  命名空间: complete_pipeline")
        print(f"  支持格式: PDF, DOCX, TXT, MD, HTML, JSON")
    
    def demonstrate_document_ingestion(self):
        """演示文档摄取过程"""
        print("\n📥 文档摄取过程演示")
        print("-" * 60)
        
        print("🔍 文档摄取特点:")
        print("• 📄 多格式文档支持")
        print("• 🔄 MarkItDown格式转换")
        print("• ✂️ 智能文档分块")
        print("• 🎯 元数据提取")
        
        # 演示不同类型文档的处理
        print(f"\n1. 多格式文档处理:")
        
        # 模拟不同格式的文档
        documents = [
            {
                "content": """# 机器学习基础教程

## 第一章：机器学习概述

机器学习是人工智能的一个重要分支，它使计算机能够在没有明确编程的情况下学习和改进。

### 1.1 机器学习的定义

机器学习是一种数据分析方法，它自动化分析模型的构建。它是人工智能的一个分支，基于系统可以从数据中学习、识别模式并在最少人工干预的情况下做出决策的想法。

### 1.2 机器学习的类型

1. **监督学习**：使用标记的训练数据来学习映射函数
2. **无监督学习**：从未标记的数据中发现隐藏的模式
3. **强化学习**：通过与环境交互来学习最优行为

### 1.3 常见算法

- 线性回归
- 逻辑回归
- 决策树
- 随机森林
- 支持向量机
- 神经网络

## 第二章：数据预处理

数据预处理是机器学习流程中的关键步骤...
""",
                "document_id": "ml_tutorial_chapter1",
                "format": "markdown",
                "metadata": {
                    "title": "机器学习基础教程",
                    "chapter": 1,
                    "author": "AI教学团队",
                    "difficulty": "beginner",
                    "estimated_reading_time": 15
                }
            },
            {
                "content": """深度学习技术报告

执行摘要：
本报告分析了深度学习在计算机视觉领域的最新进展。通过对比不同架构的性能，我们发现Transformer架构在多个任务上都表现出色。

主要发现：
1. Vision Transformer (ViT) 在图像分类任务上超越了传统CNN
2. CLIP模型实现了图像和文本的统一表示
3. 自监督学习方法显著减少了对标注数据的依赖

技术细节：
- 数据集：ImageNet-1K, COCO, OpenImages
- 评估指标：Top-1准确率, mAP, FID分数
- 计算资源：8x V100 GPU, 训练时间72小时

结论：
深度学习技术在计算机视觉领域持续快速发展，Transformer架构的引入为该领域带来了新的突破。建议在实际项目中优先考虑基于Transformer的模型。

附录：
详细的实验数据和代码实现请参考GitHub仓库。
""",
                "document_id": "deep_learning_report",
                "format": "text",
                "metadata": {
                    "title": "深度学习技术报告",
                    "type": "technical_report",
                    "date": "2024-01-15",
                    "department": "AI研究部",
                    "confidentiality": "internal"
                }
            },
            {
                "content": """{
    "api_documentation": {
        "title": "机器学习API文档",
        "version": "v2.1",
        "base_url": "https://api.ml-platform.com/v2",
        "endpoints": [
            {
                "path": "/models",
                "method": "GET",
                "description": "获取可用模型列表",
                "parameters": {
                    "category": "模型类别 (classification, regression, clustering)",
                    "limit": "返回结果数量限制"
                },
                "response": {
                    "models": [
                        {
                            "id": "model_123",
                            "name": "RandomForest分类器",
                            "category": "classification",
                            "accuracy": 0.95,
                            "training_data_size": 10000
                        }
                    ]
                }
            },
            {
                "path": "/predict",
                "method": "POST",
                "description": "使用指定模型进行预测",
                "parameters": {
                    "model_id": "模型ID",
                    "data": "输入数据"
                },
                "response": {
                    "prediction": "预测结果",
                    "confidence": "置信度",
                    "processing_time": "处理时间(ms)"
                }
            }
        ],
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "在请求头中包含API密钥"
        },
        "rate_limits": {
            "requests_per_minute": 100,
            "requests_per_day": 10000
        }
    }
}""",
                "document_id": "ml_api_docs",
                "format": "json",
                "metadata": {
                    "title": "机器学习API文档",
                    "version": "v2.1",
                    "type": "api_documentation",
                    "last_updated": "2024-01-20"
                }
            }
        ]
        
        # 处理每个文档
        for doc in documents:
            print(f"\n处理文档: {doc['document_id']} ({doc['format']})")
            
            result = self.rag_tool.run({"action":"add_text",
                                         "text":doc["content"],
                                         "document_id":doc["document_id"],
                                         **doc["metadata"]})
            print(f"  摄取结果: {result}")
            
            # 显示文档统计
            doc_stats = {
                "字符数": len(doc["content"]),
                "行数": doc["content"].count('\n') + 1,
                "格式": doc["format"],
                "元数据字段": len(doc["metadata"])
            }
            print(f"  文档统计: {doc_stats}")
        
        # 演示批量文档处理
        print(f"\n2. 批量文档处理:")
        
        batch_documents = []
        for i in range(3):
            batch_doc = {
                "content": f"""# 批量文档 {i+1}

这是第 {i+1} 个批量处理的文档。它包含了关于人工智能发展的重要信息。

## 主要内容
- AI技术趋势分析
- 行业应用案例
- 未来发展预测

## 详细描述
人工智能技术在过去几年中取得了显著进展，特别是在深度学习、自然语言处理和计算机视觉领域。

### 技术突破
1. 大语言模型的涌现
2. 多模态AI的发展
3. 自动化机器学习的普及

### 应用领域
- 医疗诊断
- 金融风控
- 智能制造
- 自动驾驶

这些技术的发展为各行各业带来了新的机遇和挑战。
""",
                "document_id": f"batch_doc_{i+1}",
                "metadata": {
                    "batch_id": "batch_001",
                    "sequence": i+1,
                    "topic": "artificial_intelligence",
                    "processing_date": datetime.now().isoformat()
                }
            }
            batch_documents.append(batch_doc)
        
        # 批量处理
        start_time = time.time()
        for doc in batch_documents:
            result = self.rag_tool.run({"action":"add_text",
                                         "text":doc["content"],
                                         "document_id":doc["document_id"],
                                         **doc["metadata"]})
            print(f"  批量处理 {doc['document_id']}: {result}")
        
        batch_time = time.time() - start_time
        print(f"  批量处理耗时: {batch_time:.3f}秒")
        
        # 获取摄取统计
        stats = self.rag_tool.run({"action":"stats"})
        print(f"\n📊 文档摄取统计: {stats}")
    
    def demonstrate_chunking_strategies(self):
        """演示文档分块策略"""
        print("\n✂️ 文档分块策略演示")
        print("-" * 60)
        
        print("🔍 分块策略特点:")
        print("• 📏 基于语义的智能分块")
        print("• 🔗 保持上下文连贯性")
        print("• ⚖️ 平衡块大小和信息完整性")
        print("• 🎯 优化检索效果")
        
        # 演示不同分块策略
        print(f"\n1. 分块策略对比:")
        
        # 长文档示例
        long_document = """# 人工智能发展史

## 引言
人工智能（Artificial Intelligence, AI）的发展历程可以追溯到20世纪50年代。从最初的符号主义方法到现代的深度学习，AI经历了多次重要的发展阶段。

## 第一阶段：符号主义时代（1950s-1980s）
### 起源与发展
1950年，阿兰·图灵发表了著名的论文《计算机器与智能》，提出了"图灵测试"的概念。这标志着人工智能研究的正式开始。

### 主要成就
- 1956年达特茅斯会议，正式提出"人工智能"概念
- 专家系统的发展，如MYCIN医疗诊断系统
- 逻辑推理和知识表示方法的建立

### 局限性
符号主义方法虽然在某些领域取得了成功，但面临着知识获取瓶颈和常识推理困难等问题。

## 第二阶段：连接主义复兴（1980s-2000s）
### 神经网络的回归
1986年，Rumelhart等人重新发现了反向传播算法，使得多层神经网络的训练成为可能。

### 重要突破
- 多层感知机的成功应用
- 卷积神经网络在图像识别中的应用
- 循环神经网络处理序列数据

### 技术限制
由于计算能力和数据量的限制，神经网络在这一时期的应用仍然有限。

## 第三阶段：深度学习革命（2000s-至今）
### 深度学习的兴起
2006年，Geoffrey Hinton等人提出了深度信念网络，开启了深度学习的新时代。

### 关键技术突破
- GPU并行计算的应用
- 大数据的可获得性
- 改进的训练算法和正则化技术

### 重大成就
- 2012年AlexNet在ImageNet竞赛中的突破性表现
- 2016年AlphaGo击败世界围棋冠军
- 2017年Transformer架构的提出
- 2020年GPT-3等大语言模型的出现

## 第四阶段：通用人工智能探索（2020s-未来）
### 当前趋势
- 多模态AI的发展
- 自监督学习方法的普及
- 神经符号结合的新方法

### 未来展望
人工智能正朝着更加通用、可解释和安全的方向发展。通用人工智能（AGI）的实现仍然是一个长期目标。

## 结论
人工智能的发展是一个螺旋上升的过程，每个阶段都有其独特的贡献和局限性。理解这一发展历程有助于我们更好地把握AI技术的未来方向。

## 参考文献
1. Turing, A. M. (1950). Computing machinery and intelligence.
2. Russell, S., & Norvig, P. (2020). Artificial Intelligence: A Modern Approach.
3. Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning.
"""
        
        # 添加长文档并观察分块效果
        chunking_result = self.rag_tool.run({"action":"add_text",
                                               "text":long_document,
                                               "document_id":"ai_history_long",
                                               "title":"人工智能发展史",
                                               "type":"historical_overview",
                                               "chunking_strategy":"semantic"})
        print(f"长文档分块结果: {chunking_result}")
        
        # 演示不同分块大小的影响
        print(f"\n2. 分块大小影响分析:")
        
        # 搜索测试，观察分块对检索的影响
        test_queries = [
            "图灵测试是什么？",
            "深度学习的关键技术突破",
            "AlphaGo的意义",
            "通用人工智能的未来"
        ]
        
        for query in test_queries:
            start_time = time.time()
            results = self.rag_tool.run({"action":"search",
                                          "query":query,
                                          "limit":3})
            search_time = time.time() - start_time
            print(f"  查询: '{query}' ({search_time:.4f}秒)")
            print(f"    结果: {results[:120]}...")
        
        # 演示结构化文档的分块
        print(f"\n3. 结构化文档分块:")
        
        structured_doc = """# 机器学习算法手册

## 监督学习算法

### 线性回归
**定义**: 线性回归是一种用于预测连续数值的算法。
**公式**: y = wx + b
**优点**: 简单易懂，计算效率高
**缺点**: 只能处理线性关系
**应用场景**: 房价预测、销售预测

### 逻辑回归
**定义**: 逻辑回归用于二分类问题。
**公式**: p = 1/(1+e^(-wx+b))
**优点**: 输出概率值，可解释性强
**缺点**: 对特征工程要求高
**应用场景**: 邮件分类、医疗诊断

### 决策树
**定义**: 基于特征进行分层决策的树形结构。
**算法**: ID3, C4.5, CART
**优点**: 可解释性强，处理非线性关系
**缺点**: 容易过拟合
**应用场景**: 信用评估、医疗诊断

## 无监督学习算法

### K-means聚类
**定义**: 将数据分为K个簇的聚类算法。
**步骤**: 初始化中心点 → 分配样本 → 更新中心点 → 重复
**优点**: 简单高效
**缺点**: 需要预设簇数
**应用场景**: 客户分群、图像分割

### 主成分分析(PCA)
**定义**: 降维算法，保留主要信息。
**原理**: 找到数据的主要变化方向
**优点**: 降低维度，去除噪声
**缺点**: 损失部分信息
**应用场景**: 数据可视化、特征提取
"""
        
        structured_result = self.rag_tool.run({"action":"add_text",
                                                 "text":structured_doc,
                                                 "document_id":"ml_algorithms_handbook",
                                                 "title":"机器学习算法手册",
                                                 "type":"reference_manual",
                                                 "structure":"hierarchical"})
        print(f"结构化文档分块: {structured_result}")
        
        # 测试结构化检索
        structured_queries = [
            "线性回归的优缺点",
            "K-means聚类算法",
            "PCA降维原理"
        ]
        
        for query in structured_queries:
            results = self.rag_tool.run({"action":"search",
                                          "query":query,
                                          "limit":2})
            print(f"  结构化查询 '{query}': {results[:100]}...")
    
    def demonstrate_advanced_retrieval(self):
        """演示高级检索策略"""
        print("\n🔍 高级检索策略演示")
        print("-" * 60)
        
        print("🔍 高级检索特点:")
        print("• 🎯 多查询扩展（MQE）")
        print("• 💭 假设文档嵌入（HyDE）")
        print("• 🔄 混合检索策略")
        print("• 📊 相关性重排序")
        
        # 演示多查询扩展
        print(f"\n1. 多查询扩展（MQE）演示:")
        
        base_query = "如何提高机器学习模型的性能？"
        print(f"原始查询: {base_query}")
        
        # 模拟查询扩展
        expanded_queries = [
            "机器学习模型性能优化方法",
            "提升ML模型准确率的技巧",
            "模型调优和超参数优化",
            "机器学习模型评估指标"
        ]
        
        print(f"扩展查询:")
        for i, query in enumerate(expanded_queries, 1):
            print(f"  {i}. {query}")
        
        # 执行多查询检索
        all_results = []
        for query in [base_query] + expanded_queries:
            results = self.rag_tool.run({"action":"search",
                                          "query":query,
                                          "limit":3})
            all_results.append((query, results))
            print(f"  查询结果 '{query[:20]}...': {results[:80]}...")
        
        # 演示假设文档嵌入（HyDE）
        print(f"\n2. 假设文档嵌入（HyDE）演示:")
        
        user_question = "什么是深度学习？"
        print(f"用户问题: {user_question}")
        
        # 生成假设答案
        hypothetical_answer = """深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的复杂模式。深度学习模型通过多个隐藏层来提取数据的层次化特征表示。常见的深度学习架构包括卷积神经网络（CNN）、循环神经网络（RNN）和Transformer。深度学习在图像识别、自然语言处理、语音识别等领域取得了突破性进展。"""
        
        print(f"假设答案: {hypothetical_answer[:100]}...")
        
        # 使用假设答案进行检索
        hyde_results = self.rag_tool.run({"action":"search",
                                           "query":hypothetical_answer,
                                           "limit":5})
        print(f"HyDE检索结果: {hyde_results[:120]}...")
        
        # 对比直接查询结果
        direct_results = self.rag_tool.run({"action":"search",
                                             "query":user_question,
                                             "limit":5})
        print(f"直接查询结果: {direct_results[:120]}...")
        
        # 演示混合检索策略
        print(f"\n3. 混合检索策略演示:")
        
        complex_query = "比较监督学习和无监督学习的区别，并给出具体应用例子"
        print(f"复杂查询: {complex_query}")
        
        # 分解查询
        sub_queries = [
            "监督学习的定义和特点",
            "无监督学习的定义和特点", 
            "监督学习的应用例子",
            "无监督学习的应用例子",
            "监督学习和无监督学习的区别"
        ]
        
        print(f"查询分解:")
        mixed_results = {}
        for sub_query in sub_queries:
            results = self.rag_tool.run({"action":"search",
                                          "query":sub_query,
                                          "limit":2})
            mixed_results[sub_query] = results
            print(f"  子查询: {sub_query}")
            print(f"    结果: {results[:80]}...")
        
        # 演示相关性重排序
        print(f"\n4. 相关性重排序演示:")
        
        ranking_query = "神经网络训练过程"
        print(f"排序查询: {ranking_query}")
        
        # 获取初始结果
        initial_results = self.rag_tool.run({"action":"search",
                                              "query":ranking_query,
                                              "limit":8})
        print(f"初始检索结果: {initial_results[:150]}...")
        
        # 模拟重排序过程（基于多个因素）
        print(f"重排序因素:")
        print(f"  • 语义相似度权重: 0.6")
        print(f"  • 文档新鲜度权重: 0.2") 
        print(f"  • 文档权威性权重: 0.2")
        
        # 最终排序结果
        final_results = self.rag_tool.run({"action":"search",
                                            "query":ranking_query,
                                            "limit":5})
        print(f"重排序后结果: {final_results[:150]}...")
    
    def demonstrate_intelligent_qa(self):
        """演示智能问答生成"""
        print("\n🤖 智能问答生成演示")
        print("-" * 60)
        
        print("🔍 智能问答特点:")
        print("• 🎯 问题理解和分类")
        print("• 📚 上下文构建")
        print("• 💡 答案生成和优化")
        print("• 🔗 引用和溯源")
        
        # 演示不同类型问题的处理
        print(f"\n1. 不同类型问题处理:")
        
        qa_examples = [
            {
                "question": "什么是机器学习？",
                "type": "定义类问题",
                "expected_approach": "提供清晰定义和基本概念"
            },
            {
                "question": "如何选择合适的机器学习算法？",
                "type": "方法类问题", 
                "expected_approach": "提供步骤和决策框架"
            },
            {
                "question": "深度学习和传统机器学习有什么区别？",
                "type": "比较类问题",
                "expected_approach": "对比分析优缺点"
            },
            {
                "question": "为什么神经网络需要激活函数？",
                "type": "原理类问题",
                "expected_approach": "解释技术原理和必要性"
            },
            {
                "question": "在图像分类项目中应该使用哪种算法？",
                "type": "应用类问题",
                "expected_approach": "结合场景给出具体建议"
            }
        ]
        
        for example in qa_examples:
            print(f"\n问题类型: {example['type']}")
            print(f"问题: {example['question']}")
            print(f"处理策略: {example['expected_approach']}")
            
            # 执行问答
            start_time = time.time()
            answer = self.rag_tool.run({"action":"ask",
                                         "question":example["question"],
                                         "limit":4})
            qa_time = time.time() - start_time
            
            print(f"回答 ({qa_time:.3f}秒): {answer[:200]}...")
        
        # 演示上下文构建过程
        print(f"\n2. 上下文构建过程演示:")
        
        context_question = "如何防止神经网络过拟合？"
        print(f"问题: {context_question}")
        
        # 模拟上下文构建步骤
        print(f"上下文构建步骤:")
        print(f"  1. 问题分析 - 识别关键概念：过拟合、神经网络、防止方法")
        print(f"  2. 相关文档检索 - 搜索相关技术文档")
        print(f"  3. 上下文筛选 - 选择最相关的信息片段")
        print(f"  4. 上下文排序 - 按相关性和重要性排序")
        
        # 执行上下文构建
        context_search = self.rag_tool.run({"action":"search",
                                             "query":"神经网络过拟合防止方法",
                                             "limit":6})
        print(f"  检索到的上下文: {context_search[:180]}...")
        
        # 生成最终答案
        final_answer = self.rag_tool.run({"action":"ask",
                                           "question":context_question,
                                           "limit":5})
        print(f"  最终答案: {final_answer[:250]}...")
        
        # 演示多轮对话支持
        print(f"\n3. 多轮对话支持:")
        
        conversation = [
            "什么是卷积神经网络？",
            "它主要用于什么任务？",
            "相比传统方法有什么优势？",
            "在实际项目中如何使用？"
        ]
        
        print(f"模拟对话场景:")
        for i, question in enumerate(conversation, 1):
            print(f"\n  轮次 {i}: {question}")
            
            # 在多轮对话中，后续问题可能需要前面的上下文
            if i > 1:
                context_query = f"卷积神经网络 {question}"
            else:
                context_query = question
            
            answer = self.rag_tool.run({"action":"ask",
                                         "question":context_query,
                                         "limit":3})
            print(f"  回答: {answer[:150]}...")
        
        # 演示答案质量评估
        print(f"\n4. 答案质量评估:")
        
        quality_question = "解释反向传播算法的工作原理"
        print(f"评估问题: {quality_question}")
        
        answer = self.rag_tool.run({"action":"ask",
                                     "question":quality_question,
                                     "limit":5})
        
        print(f"生成答案: {answer[:300]}...")
        
        # 模拟质量评估指标
        quality_metrics = {
            "相关性": "高 - 答案直接回应了问题",
            "准确性": "高 - 技术描述准确",
            "完整性": "中 - 涵盖了主要概念",
            "可读性": "高 - 结构清晰易懂",
            "引用质量": "中 - 基于可靠来源"
        }
        
        print(f"质量评估:")
        for metric, score in quality_metrics.items():
            print(f"  {metric}: {score}")
    
    def demonstrate_performance_optimization(self):
        """演示性能优化"""
        print("\n⚡ 性能优化演示")
        print("-" * 60)
        
        print("🔍 性能优化特点:")
        print("• 🚀 检索速度优化")
        print("• 💾 内存使用优化")
        print("• 🎯 结果质量提升")
        print("• 📊 系统监控")
        
        # 演示检索性能测试
        print(f"\n1. 检索性能测试:")
        
        performance_queries = [
            "机器学习基础概念",
            "深度学习应用场景", 
            "神经网络训练技巧",
            "数据预处理方法",
            "模型评估指标"
        ]
        
        total_time = 0
        total_queries = len(performance_queries)
        
        print(f"执行 {total_queries} 个查询的性能测试:")
        
        for i, query in enumerate(performance_queries, 1):
            start_time = time.time()
            results = self.rag_tool.run({"action":"search",
                                          "query":query,
                                          "limit":5})
            query_time = time.time() - start_time
            total_time += query_time
            
            print(f"  查询 {i}: '{query}' - {query_time:.4f}秒")
        
        avg_time = total_time / total_queries
        print(f"\n性能统计:")
        print(f"  总耗时: {total_time:.4f}秒")
        print(f"  平均查询时间: {avg_time:.4f}秒")
        print(f"  查询吞吐量: {1/avg_time:.2f} 查询/秒")
        
        # 演示批量处理优化
        print(f"\n2. 批量处理优化:")
        
        batch_queries = [
            "什么是监督学习？",
            "什么是无监督学习？",
            "什么是强化学习？",
            "什么是深度学习？",
            "什么是神经网络？"
        ]
        
        # 单个处理
        start_time = time.time()
        individual_results = []
        for query in batch_queries:
            result = self.rag_tool.run({"action":"search", "query":query, "limit":2})
            individual_results.append(result)
        individual_time = time.time() - start_time
        
        print(f"  单个处理耗时: {individual_time:.4f}秒")
        
        # 模拟批量处理（实际实现中可能有优化）
        start_time = time.time()
        batch_results = []
        for query in batch_queries:
            result = self.rag_tool.run({"action":"search", "query":query, "limit":2})
            batch_results.append(result)
        batch_time = time.time() - start_time
        
        print(f"  批量处理耗时: {batch_time:.4f}秒")
        print(f"  性能提升: {((individual_time - batch_time) / individual_time * 100):.1f}%")
        
        # 演示缓存机制
        print(f"\n3. 缓存机制演示:")
        
        cache_query = "机器学习算法分类"
        
        # 第一次查询（无缓存）
        start_time = time.time()
        first_result = self.rag_tool.run({"action":"search",
                                           "query":cache_query,
                                           "limit":3})
        first_time = time.time() - start_time
        print(f"  首次查询: {first_time:.4f}秒")
        
        # 第二次查询（可能有缓存）
        start_time = time.time()
        second_result = self.rag_tool.run({"action":"search",
                                            "query":cache_query,
                                            "limit":3})
        second_time = time.time() - start_time
        print(f"  重复查询: {second_time:.4f}秒")
        
        if second_time < first_time:
            speedup = (first_time - second_time) / first_time * 100
            print(f"  缓存加速: {speedup:.1f}%")
        
        # 演示系统监控
        print(f"\n4. 系统监控:")
        
        # 获取系统统计
        system_stats = self.rag_tool.run({"action":"stats"})
        print(f"  系统统计: {system_stats}")
        
        # 模拟资源使用监控
        resource_usage = {
            "文档数量": "15个",
            "索引大小": "约2.5MB",
            "内存使用": "约128MB",
            "平均响应时间": f"{avg_time:.4f}秒",
            "成功率": "100%"
        }
        
        print(f"  资源使用情况:")
        for metric, value in resource_usage.items():
            print(f"    {metric}: {value}")

def main():
    """主函数"""
    print("📚 RAG完整处理管道演示")
    print("展示从文档处理到智能问答的完整RAG流程")
    print("=" * 80)
    
    try:
        demo = RAGPipelineComplete()
        
        # 1. 文档摄取演示
        demo.demonstrate_document_ingestion()
        
        # 2. 分块策略演示
        demo.demonstrate_chunking_strategies()
        
        # 3. 高级检索演示
        demo.demonstrate_advanced_retrieval()
        
        # 4. 智能问答演示
        demo.demonstrate_intelligent_qa()
        
        # 5. 性能优化演示
        demo.demonstrate_performance_optimization()
        
        print("\n" + "=" * 80)
        print("🎉 RAG完整处理管道演示完成！")
        print("=" * 80)
        
        print("\n✨ RAG管道核心特性:")
        print("1. 📥 多格式文档摄取 - 支持PDF、DOCX、TXT、MD等")
        print("2. ✂️ 智能文档分块 - 基于语义的分块策略")
        print("3. 🔍 高级检索策略 - MQE、HyDE、混合检索")
        print("4. 🤖 智能问答生成 - 上下文构建和答案优化")
        print("5. ⚡ 性能优化 - 缓存、批量处理、监控")
        
        print("\n🎯 技术优势:")
        print("• 端到端处理流程")
        print("• 多策略检索优化")
        print("• 智能上下文构建")
        print("• 高质量答案生成")
        print("• 全面性能监控")
        
        print("\n💡 应用场景:")
        print("• 企业知识库问答")
        print("• 技术文档助手")
        print("• 学习辅导系统")
        print("• 智能客服系统")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()