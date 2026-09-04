#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码示例 05: RAGTool高级检索策略
展示MQE、HyDE等先进检索技术的实现和应用
"""

import time
from rag_tool import RAGTool
from dotenv import load_dotenv
load_dotenv()

class AdvancedSearchDemo:
    """高级检索演示类"""
    
    def __init__(self):
        self.rag_tool = RAGTool(
            knowledge_base_path="./advanced_search_kb",
            rag_namespace="advanced_search_demo"
        )
        self._setup_knowledge_base()
    
    def _setup_knowledge_base(self):
        """设置知识库内容"""
        print("📚 设置知识库内容")
        print("=" * 50)
        
        # 添加技术文档
        tech_documents = [
            {
                "id": "transformer_architecture",
                "content": """# Transformer架构详解

## 注意力机制
Transformer的核心是自注意力机制（Self-Attention），它允许模型在处理序列时关注到序列中的不同位置。

### 多头注意力
多头注意力机制将输入投影到多个不同的子空间，每个头关注不同的表示子空间。

### 位置编码
由于Transformer没有循环结构，需要位置编码来提供序列中位置信息。

## 编码器-解码器结构
- 编码器：将输入序列编码为表示
- 解码器：基于编码器输出生成目标序列

## 应用领域
- 机器翻译
- 文本摘要
- 问答系统
- 代码生成
"""
            },
            {
                "id": "deep_learning_optimization",
                "content": """# 深度学习优化技术

## 梯度下降算法
梯度下降是深度学习中最基础的优化算法。

### 随机梯度下降（SGD）
- 每次使用单个样本更新参数
- 计算效率高，但收敛不稳定

### 批量梯度下降
- 使用全部训练数据计算梯度
- 收敛稳定，但计算成本高

### 小批量梯度下降
- 平衡了SGD和批量梯度下降的优缺点
- 是实际应用中最常用的方法

## 自适应学习率算法
- Adam：结合动量和自适应学习率
- AdaGrad：根据历史梯度调整学习率
- RMSprop：解决AdaGrad学习率衰减过快的问题

## 正则化技术
- Dropout：随机丢弃神经元防止过拟合
- Batch Normalization：标准化层输入
- Weight Decay：权重衰减正则化
"""
            },
            {
                "id": "nlp_applications",
                "content": """# 自然语言处理应用

## 文本分类
文本分类是NLP中的基础任务，包括情感分析、主题分类、垃圾邮件检测等。

### 传统方法
- 词袋模型（Bag of Words）
- TF-IDF特征
- 朴素贝叶斯分类器

### 深度学习方法
- CNN用于文本分类
- RNN和LSTM处理序列信息
- BERT等预训练模型

## 命名实体识别（NER）
识别文本中的人名、地名、组织名等实体。

### 序列标注方法
- BIO标注体系
- CRF条件随机场
- BiLSTM-CRF模型

## 机器翻译
将一种语言的文本翻译成另一种语言。

### 统计机器翻译
- 基于短语的翻译模型
- 语言模型和翻译模型

### 神经机器翻译
- Seq2Seq模型
- 注意力机制
- Transformer架构
"""
            },
            {
                "id": "computer_vision",
                "content": """# 计算机视觉技术

## 图像分类
图像分类是计算机视觉的基础任务，目标是将图像分配到预定义的类别中。

### 卷积神经网络（CNN）
- 卷积层：提取局部特征
- 池化层：降低维度和计算量
- 全连接层：进行最终分类

### 经典架构
- LeNet：最早的CNN架构
- AlexNet：深度学习在图像识别的突破
- VGG：使用小卷积核的深层网络
- ResNet：残差连接解决梯度消失

## 目标检测
在图像中定位和识别多个对象。

### 两阶段方法
- R-CNN：区域提议+CNN分类
- Fast R-CNN：端到端训练
- Faster R-CNN：RPN网络生成提议

### 单阶段方法
- YOLO：将检测作为回归问题
- SSD：多尺度特征检测

## 图像分割
将图像分割为不同的区域或对象。

### 语义分割
- FCN：全卷积网络
- U-Net：编码器-解码器结构
- DeepLab：空洞卷积

### 实例分割
- Mask R-CNN：在Faster R-CNN基础上添加分割分支
"""
            }
        ]
        
        # 批量添加文档
        for doc in tech_documents:
            result = self.rag_tool.run({"action":"add_text",
                                         "text":doc["content"],
                                         "document_id":doc["id"]})
            print(f"✅ 添加文档: {doc['id']}")
        
        print(f"📊 知识库设置完成，共添加 {len(tech_documents)} 个文档")
    
    def demonstrate_basic_search(self):
        """演示基础搜索功能"""
        print("\n🔍 基础搜索功能演示")
        print("-" * 50)
        
        print("基础搜索特点:")
        print("• 向量相似度匹配")
        print("• 基于嵌入的语义理解")
        print("• 相关性排序")
        print("• 快速响应")
        
        basic_queries = [
            ("注意力机制", "测试精确概念匹配"),
            ("深度学习优化", "测试主题匹配"),
            ("图像分类CNN", "测试多词匹配"),
            ("机器翻译模型", "测试跨文档匹配")
        ]
        
        print(f"\n🔍 基础搜索测试:")
        for query, description in basic_queries:
            print(f"\n查询: '{query}' ({description})")
            
            start_time = time.time()
            result = self.rag_tool.run({"action":"search",
                                         "query":query,
                                         "limit":2,
                                         "enable_advanced_search":False})
            search_time = time.time() - start_time
            
            print(f"耗时: {search_time:.3f}秒")
            print(f"结果: {result[:200]}...")
    
    def demonstrate_mqe_search(self):
        """演示多查询扩展（MQE）搜索"""
        print("\n🔄 多查询扩展（MQE）搜索演示")
        print("-" * 50)
        
        print("MQE搜索原理:")
        print("• 🤖 使用LLM生成语义等价查询")
        print("• 🔍 并行执行多个查询")
        print("• 📊 合并和去重结果")
        print("• 🎯 提高召回率和覆盖面")
        
        mqe_queries = [
            ("深度学习", "测试概念扩展"),
            ("优化算法", "测试技术扩展"),
            ("神经网络", "测试架构扩展")
        ]
        
        print(f"\n🔄 MQE搜索测试:")
        for query, description in mqe_queries:
            print(f"\n查询: '{query}' ({description})")
            
            # 基础搜索对比
            start_time = time.time()
            basic_result = self.rag_tool.run({"action":"search",
                                               "query":query,
                                               "limit":3,
                                               "enable_advanced_search":False})
            basic_time = time.time() - start_time
            
            # MQE搜索
            start_time = time.time()
            mqe_result = self.rag_tool.run({"action":"search",
                                             "query":query,
                                             "limit":3,
                                             "enable_advanced_search":True})
            mqe_time = time.time() - start_time
            
            print(f"基础搜索耗时: {basic_time:.3f}秒")
            print(f"MQE搜索耗时: {mqe_time:.3f}秒")
            print(f"基础结果: {basic_result[:150]}...")
            print(f"MQE结果: {mqe_result[:150]}...")
            if basic_time > 0:
                print(f"性能对比: MQE搜索耗时是基础搜索的 {mqe_time/basic_time:.1f} 倍")
            else:
                print("性能对比: 搜索速度过快，无法精确对比")
    
    def demonstrate_hyde_search(self):
        """演示假设文档嵌入（HyDE）搜索"""
        print("\n📝 假设文档嵌入（HyDE）搜索演示")
        print("-" * 50)
        
        print("HyDE搜索原理:")
        print("• 🤖 LLM生成假设性答案文档")
        print("• 📄 将假设文档作为查询向量")
        print("• 🎯 改善查询-文档匹配效果")
        print("• 🔍 特别适合复杂问题检索")
        
        hyde_queries = [
            ("如何提高深度学习模型的性能？", "测试方法性问题"),
            ("Transformer相比RNN有什么优势？", "测试对比性问题"),
            ("什么是计算机视觉中的目标检测？", "测试定义性问题")
        ]
        
        print(f"\n📝 HyDE搜索测试:")
        for query, description in hyde_queries:
            print(f"\n查询: '{query}' ({description})")
            
            # 使用智能问答（内部使用HyDE）
            start_time = time.time()
            hyde_result = self.rag_tool.run({"action":"ask",
                                              "question":query,
                                              "limit":3,
                                              "enable_advanced_search":True})
            hyde_time = time.time() - start_time
            
            print(f"HyDE问答耗时: {hyde_time:.3f}秒")
            print(f"HyDE结果: {hyde_result[:300]}...")
    
    def demonstrate_combined_advanced_search(self):
        """演示组合高级搜索"""
        print("\n🚀 组合高级搜索演示")
        print("-" * 50)
        
        print("组合搜索策略:")
        print("• 🔄 MQE + HyDE 双重扩展")
        print("• 📊 多策略结果融合")
        print("• 🎯 最大化检索效果")
        print("• ⚡ 智能缓存优化")
        
        complex_queries = [
            ("深度学习中的注意力机制是如何工作的？", "复杂技术问题"),
            ("比较不同的梯度下降优化算法", "对比分析问题"),
            ("计算机视觉和自然语言处理的共同技术", "跨领域问题")
        ]
        
        print(f"\n🚀 组合高级搜索测试:")
        for query, description in complex_queries:
            print(f"\n查询: '{query}' ({description})")
            
            # 组合高级搜索
            start_time = time.time()
            
            # 先进行高级搜索获取相关片段
            search_result = self.rag_tool.run({"action":"search",
                                                "query":query,
                                                "limit":4,
                                                "enable_advanced_search":True})
            
            # 再进行智能问答生成完整答案
            qa_result = self.rag_tool.run({"action":"ask",
                                            "question":query,
                                            "limit":4,
                                            "enable_advanced_search":True,
                                            "include_citations":True})
            
            combined_time = time.time() - start_time
            
            print(f"组合搜索耗时: {combined_time:.3f}秒")
            print(f"搜索片段: {search_result[:200]}...")
            print(f"智能问答: {qa_result[:400]}...")
    
    def demonstrate_search_performance_analysis(self):
        """演示搜索性能分析"""
        print("\n📊 搜索性能分析")
        print("-" * 50)
        
        print("性能分析指标:")
        print("• ⏱️ 响应时间对比")
        print("• 🎯 检索质量评估")
        print("• 💾 资源使用情况")
        print("• 📈 扩展性分析")
        
        # 性能测试查询
        performance_queries = [
            "机器学习",
            "深度学习优化算法",
            "Transformer注意力机制原理",
            "计算机视觉目标检测方法比较"
        ]
        
        print(f"\n📊 性能对比测试:")
        
        # 测试不同搜索策略的性能
        strategies = [
            ("基础搜索", {"enable_advanced_search": False}),
            ("高级搜索", {"enable_advanced_search": True})
        ]
        
        performance_results = {}
        
        for strategy_name, params in strategies:
            print(f"\n{strategy_name}性能测试:")
            strategy_times = []
            
            for query in performance_queries:
                start_time = time.time()
                
                result = self.rag_tool.run({"action":"search",
                                             "query":query,
                                             "limit":3,
                                             **params})
                
                query_time = time.time() - start_time
                strategy_times.append(query_time)
                
                print(f"  查询: '{query[:20]}...' 耗时: {query_time:.3f}秒")
            
            avg_time = sum(strategy_times) / len(strategy_times)
            performance_results[strategy_name] = {
                "times": strategy_times,
                "average": avg_time
            }
            
            print(f"  平均耗时: {avg_time:.3f}秒")
        
        # 性能对比分析
        print(f"\n📈 性能对比分析:")
        basic_avg = performance_results["基础搜索"]["average"]
        advanced_avg = performance_results["高级搜索"]["average"]
        
        print(f"基础搜索平均耗时: {basic_avg:.3f}秒")
        print(f"高级搜索平均耗时: {advanced_avg:.3f}秒")
        if basic_avg > 0:
            print(f"性能比值: {advanced_avg/basic_avg:.1f}x")
            print(f"分析: 高级搜索通过多策略提升检索质量，耗时增加 {((advanced_avg/basic_avg-1)*100):.0f}%")
        else:
            print("性能比值: 搜索速度过快，无法精确对比")
        
        # 获取系统统计
        stats = self.rag_tool.run({"action":"stats"})
        print(f"\n📊 系统统计: {stats}")

def main():
    """主函数"""
    print("🚀 RAGTool高级检索策略演示")
    print("展示MQE、HyDE等先进检索技术的实现和应用")
    print("=" * 70)
    
    try:
        demo = AdvancedSearchDemo()
        
        # 1. 基础搜索演示
        demo.demonstrate_basic_search()
        
        # 2. MQE搜索演示
        demo.demonstrate_mqe_search()
        
        # 3. HyDE搜索演示
        demo.demonstrate_hyde_search()
        
        # 4. 组合高级搜索演示
        demo.demonstrate_combined_advanced_search()
        
        # 5. 搜索性能分析
        demo.demonstrate_search_performance_analysis()
        
        print("\n" + "=" * 70)
        print("🎉 高级检索策略演示完成！")
        print("=" * 70)
        
        print("\n✨ 高级检索核心技术:")
        print("1. 🔄 MQE多查询扩展 - 提高召回率和覆盖面")
        print("2. 📝 HyDE假设文档嵌入 - 改善查询匹配效果")
        print("3. 🚀 组合搜索策略 - 多技术融合优化")
        print("4. 📊 智能结果排序 - 多因素评分机制")
        print("5. ⚡ 性能优化 - 缓存和批量处理")
        
        print("\n🎯 技术优势:")
        print("• 语义理解 - 超越关键词匹配的语义检索")
        print("• 查询扩展 - 自动生成相关查询提升召回")
        print("• 上下文感知 - 理解查询意图和上下文")
        print("• 质量优化 - 多策略融合提升检索质量")
        
        print("\n💡 应用场景:")
        print("• 技术文档问答 - 复杂技术问题的精准回答")
        print("• 知识发现 - 从大量文档中发现相关知识")
        print("• 智能搜索 - 理解用户意图的智能搜索")
        print("• 内容推荐 - 基于语义相似度的内容推荐")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()