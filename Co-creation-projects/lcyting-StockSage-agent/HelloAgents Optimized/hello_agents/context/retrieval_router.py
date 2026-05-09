"""智能检索路由模块

实现基于意图识别和上下文依赖度的智能检索路由：
- IntentClassifier: 判断问题类型（事实/个人/混合）
- ContextAnalyzer: 计算上下文依赖度
- RetrievalRouter: 协调决策，输出检索策略
"""

from typing import List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import re


class IntentType(Enum):
    """问题意图类型"""

    FACTUAL = "factual"
    PERSONAL = "personal"
    MIXED = "mixed"


class RoutingStrategy(Enum):
    """路由策略"""

    RAG_ONLY = "rag_only"
    MEMORY_ONLY = "memory_only"
    DUAL_RETRIEVAL = "dual_retrieval"


@dataclass
class RouterConfig:
    """路由器配置"""

    # 意图分类关键词
    personal_keywords: List[str] = field(
        default_factory=lambda: [
            "我记得",
            "上次",
            "之前",
            "我说过",
            "我的",
            "我们",
            "昨天",
            "刚才",
        ]
    )
    factual_keywords: List[str] = field(
        default_factory=lambda: [
            "什么是",
            "是什么",
            "定义",
            "原理",
            "如何实现",
            "如何解释",
            "解释",
            "为什么",
            "怎么",
            "有哪些",
            "如何做",
        ]
    )
    # 依赖度分析关键词
    dependency_keywords: List[str] = field(
        default_factory=lambda: [
            "这个",
            "那个",
            "它",
            "他",
            "上文的",
            "接着",
            "然后",
            "继续",
            "还有",
        ]
    )
    # 权重配置
    keyword_weight: float = 0.6
    overlap_weight: float = 0.4


@dataclass
class RoutingResult:
    """路由决策结果"""

    use_rag: bool = True
    use_memory: bool = True
    rag_weight: float = 0.5
    memory_weight: float = 0.5
    intent: IntentType = IntentType.MIXED
    dependency_score: float = 0.5
    strategy: RoutingStrategy = RoutingStrategy.DUAL_RETRIEVAL


class IntentClassifier:
    """意图分类器"""

    def __init__(self, config: RouterConfig = None):
        self.config = config or RouterConfig()

    def classify(self, query: str) -> IntentType:
        """分类 Query 的意图类型

        Args:
            query: 用户查询文本

        Returns:
            IntentType: factual / personal / mixed
        """
        if not query or not query.strip():
            return IntentType.MIXED

        query_lower = query.lower()
        personal_score = sum(
            1 for kw in self.config.personal_keywords if kw in query_lower
        )
        factual_score = sum(
            1 for kw in self.config.factual_keywords if kw in query_lower
        )

        if personal_score > factual_score:
            return IntentType.PERSONAL
        elif factual_score > personal_score:
            return IntentType.FACTUAL
        return IntentType.MIXED


class ContextAnalyzer:
    """上下文依赖度分析器"""

    def __init__(self, config: RouterConfig = None):
        self.config = config or RouterConfig()

    def analyze(self, query: str, history: List[Any]) -> float:
        """分析当前 Query 对历史对话的依赖程度

        Args:
            query: 用户查询文本
            history: 历史消息列表 (需有 content 属性)

        Returns:
            float: 依赖度分数 [0.0, 1.0]
        """
        if not query or not query.strip():
            return 0.0

        # 1. 关键词依赖得分
        kw_score = sum(1 for kw in self.config.dependency_keywords if kw in query)
        # 归一化，假设最多匹配 3 个关键词即为高度依赖
        kw_normalized = min(kw_score / 3.0, 1.0)

        # 2. 主题重叠得分
        overlap_score = 0.0
        if history:
            # 取最后一条消息
            last_msg = history[-1]
            last_content = (
                last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            )

            query_tokens = set(self._tokenize(query))
            history_tokens = set(self._tokenize(last_content))

            if query_tokens:
                overlap = len(query_tokens & history_tokens)
                overlap_score = overlap / len(query_tokens)

        # 3. 加权计算
        return min(
            1.0,
            (
                self.config.keyword_weight * kw_normalized
                + self.config.overlap_weight * overlap_score
            ),
        )

    def _tokenize(self, text: str) -> List[str]:
        """简单分词：提取连续的词块或单个汉字"""
        # 先用正则提取词块（字母、数字序列）
        word_tokens = re.findall(r"[a-zA-Z0-9]+", text)
        # 提取中文字符（每个汉字作为一个 token）
        char_tokens = re.findall(r"[\u4e00-\u9fa5]", text)
        return word_tokens + char_tokens


# 路由决策矩阵
ROUTING_MATRIX = {
    (IntentType.FACTUAL, "low"): {"rag": 1.0, "memory": 0.0},
    (IntentType.FACTUAL, "medium"): {"rag": 0.7, "memory": 0.3},
    (IntentType.FACTUAL, "high"): {"rag": 0.6, "memory": 0.4},
    (IntentType.PERSONAL, "low"): {"rag": 0.3, "memory": 0.7},
    (IntentType.PERSONAL, "medium"): {"rag": 0.4, "memory": 0.6},
    (IntentType.PERSONAL, "high"): {"rag": 0.0, "memory": 1.0},
    (IntentType.MIXED, "low"): {"rag": 0.7, "memory": 0.3},
    (IntentType.MIXED, "medium"): {"rag": 0.5, "memory": 0.5},
    (IntentType.MIXED, "high"): {"rag": 0.4, "memory": 0.6},
}


class RetrievalRouter:
    """智能检索路由引擎

    根据用户 Query 的意图和上下文依赖度，动态决定使用 RAG、Memory 或两者结合。
    """

    def __init__(self, config: RouterConfig = None):
        self.config = config or RouterConfig()
        self.intent_classifier = IntentClassifier(self.config)
        self.context_analyzer = ContextAnalyzer(self.config)

    def route(
        self, query: str, conversation_history: Optional[List[Any]] = None
    ) -> RoutingResult:
        """执行路由决策

        Args:
            query: 用户查询文本
            conversation_history: 历史对话消息列表

        Returns:
            RoutingResult: 包含检索策略和权重
        """
        # 1. 意图分类
        intent = self.intent_classifier.classify(query)

        # 2. 上下文依赖度分析
        history = conversation_history or []
        dependency = self.context_analyzer.analyze(query, history)

        # 3. 确定依赖度区间
        if dependency < 0.3:
            level = "low"
        elif dependency <= 0.7:
            level = "medium"
        else:
            level = "high"

        # 4. 查表获取权重
        weights = ROUTING_MATRIX.get((intent, level), {"rag": 0.5, "memory": 0.5})

        rag_weight = weights["rag"]
        memory_weight = weights["memory"]

        # 5. 生成策略
        if rag_weight > 0 and memory_weight > 0:
            strategy = RoutingStrategy.DUAL_RETRIEVAL
            use_rag = True
            use_memory = True
        elif rag_weight > 0:
            strategy = RoutingStrategy.RAG_ONLY
            use_rag = True
            use_memory = False
        else:
            strategy = RoutingStrategy.MEMORY_ONLY
            use_rag = False
            use_memory = True

        return RoutingResult(
            use_rag=use_rag,
            use_memory=use_memory,
            rag_weight=rag_weight,
            memory_weight=memory_weight,
            intent=intent,
            dependency_score=dependency,
            strategy=strategy,
        )
