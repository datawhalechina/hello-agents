"""上下文工程模块

为HelloAgents框架提供上下文工程能力：
- ContextBuilder: GSSC流水线（Gather-Select-Structure-Compress）
- ContextEvaluator: 上下文质量评估
- Compactor: 对话压缩整合
- NotesManager: 结构化笔记管理
- ContextObserver: 可观测性与指标追踪
"""

from .evaluator import (
    ContextEvaluator,
    QualityReport,
    QualityMetrics,
    QualityLevel,
    evaluate_context,
)
from .compressor import (
    HybridCompressor,
    HybridOptions,
    HybridStrategy,
    TruncationStrategy,
    SlidingWindowStrategy,
    LLMSummarizeStrategy,
    CompressionResult,
    LatencyRequirement,
    ContentType,
    count_tokens,
    create_compressor,
)
from .builder import ContextBuilder, ContextConfig, ContextPacket
from .retrieval_router import (
    RetrievalRouter,
    IntentClassifier,
    ContextAnalyzer,
    RouterConfig,
    RoutingResult,
    IntentType,
    RoutingStrategy,
)

__all__ = [
    "ContextEvaluator",
    "QualityReport",
    "QualityMetrics",
    "QualityLevel",
    "evaluate_context",
    "HybridCompressor",
    "HybridOptions",
    "HybridStrategy",
    "TruncationStrategy",
    "SlidingWindowStrategy",
    "LLMSummarizeStrategy",
    "CompressionResult",
    "LatencyRequirement",
    "ContentType",
    "count_tokens",
    "create_compressor",
    "ContextBuilder",
    "ContextConfig",
    "ContextPacket",
    "RetrievalRouter",
    "IntentClassifier",
    "ContextAnalyzer",
    "RouterConfig",
    "RoutingResult",
    "IntentType",
    "RoutingStrategy",
]
