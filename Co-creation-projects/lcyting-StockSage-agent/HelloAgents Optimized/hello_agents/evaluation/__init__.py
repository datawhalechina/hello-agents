"""
HelloAgents 智能体评估模块

本模块提供了完整的智能体评估框架,包括:
- BFCL (Berkeley Function Calling Leaderboard): 工具调用能力评估
- GAIA (General AI Assistants): 通用AI助手能力评估
- Data Generation: 数据生成质量评估（LLM Judge & Win Rate）
- Continuous Eval: 持续评估系统（分层评估 + 定时调度 + 趋势检测 + 告警）
- Report Generator: 评估报告生成系统（三层受众模板）

主要组件:
- benchmarks: 各种评估基准测试
  - bfcl: BFCL评估（包含专用metrics）
  - gaia: GAIA评估（包含专用metrics）
  - data_generation: 数据生成质量评估
- continuous_eval: 持续评估系统
- report_generator: 评估报告生成系统

使用示例:
    >>> from hello_agents.evaluation import BFCLDataset, BFCLEvaluator
    >>> from hello_agents import SimpleAgent
    >>>
    >>> agent = SimpleAgent(name="TestAgent")
    >>> dataset = BFCLDataset(category="simple_python")
    >>> evaluator = BFCLEvaluator(dataset=dataset)
    >>> results = evaluator.evaluate(agent, max_samples=5)
    >>> print(f"准确率: {results['overall_accuracy']:.2%}")
"""

# 导出benchmark评估器和数据集
from hello_agents.evaluation.benchmarks.bfcl.dataset import BFCLDataset
from hello_agents.evaluation.benchmarks.bfcl.evaluator import BFCLEvaluator
from hello_agents.evaluation.benchmarks.gaia.dataset import GAIADataset
from hello_agents.evaluation.benchmarks.gaia.evaluator import GAIAEvaluator
from hello_agents.evaluation.benchmarks.gaia.smart_answer_matcher import (
    SmartAnswerMatcher,
    MatchResult,
)
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
    generate_report as multi_judge_generate_report,
)

# 导出持续评估系统
from hello_agents.evaluation.continuous_eval import (
    ContinuousEvalSystem,
    EvalScheduler,
    EvalSchedule,
    run_quick_eval,
    run_standard_eval,
    run_full_eval,
    EvalDB,
    TrendDetector,
    AlertNotifier,
    Alert,
    AlertRule,
)

# 导出报告生成系统
from hello_agents.evaluation.report_generator import (
    ReportGenerator,
    report_for_developer,
    report_for_product,
    report_for_user,
)

__version__ = "0.2.0"

__all__ = [
    # Benchmark数据集
    "BFCLDataset",
    "GAIADataset",
    "AIDataset",
    # Benchmark评估器
    "BFCLEvaluator",
    "GAIAEvaluator",
    "LLMJudgeEvaluator",
    "WinRateEvaluator",
    "MultiJudgeEvaluator",
    "JudgeConfig",
    "JudgeVerdict",
    "MultiJudgeResult",
    "multi_judge_generate_report",
    # 智能匹配
    "SmartAnswerMatcher",
    "MatchResult",
    # 持续评估系统
    "ContinuousEvalSystem",
    "EvalScheduler",
    "EvalSchedule",
    "run_quick_eval",
    "run_standard_eval",
    "run_full_eval",
    "EvalDB",
    "TrendDetector",
    "AlertNotifier",
    "Alert",
    "AlertRule",
    # 报告生成系统
    "ReportGenerator",
    "report_for_developer",
    "report_for_product",
    "report_for_user",
]
