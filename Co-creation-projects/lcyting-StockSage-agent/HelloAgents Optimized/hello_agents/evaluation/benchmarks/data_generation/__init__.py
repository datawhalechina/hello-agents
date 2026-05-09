"""
Data Generation Evaluation Module

评估数据生成质量的模块，包括：
- LLM Judge: 使用LLM作为评委评估生成质量
- Win Rate: 通过对比评估计算胜率
"""

from hello_agents.evaluation.benchmarks.data_generation.dataset import AIDataset
from hello_agents.evaluation.benchmarks.data_generation.llm_judge import (
    LLMJudgeEvaluator,
)
from hello_agents.evaluation.benchmarks.data_generation.win_rate import WinRateEvaluator
from hello_agents.evaluation.benchmarks.data_generation.multi_judge import (
    MultiJudgeEvaluator,
    JudgeConfig,
    JudgeVerdict,
    MultiJudgeResult,
    generate_report,
)

__all__ = [
    "AIDataset",
    "LLMJudgeEvaluator",
    "WinRateEvaluator",
    "MultiJudgeEvaluator",
    "JudgeConfig",
    "JudgeVerdict",
    "MultiJudgeResult",
    "generate_report",
]
