"""
评估模块 - Agent 质量与性能考核

考核维度与实现:
- 结构合规率 / 条件化建议 / 数据真实性 → report_checks (纯规则，无依赖)
- 端到端延迟 / 工具调用与缓存统计     → telemetry
- 语义质量 (矛盾信号、可执行性等)     → judge (LLM-as-Judge)
"""

from .report_checks import (
    check_structure,
    check_conditional,
    check_grounding,
    evaluate_report,
    format_evaluation,
)
from .telemetry import ToolCallCounter, timed_run, format_metrics
from .signal_ledger import (
    record_signal,
    update_outcomes,
    summarize as summarize_signals,
    format_summary as format_signal_summary,
)

__all__ = [
    "record_signal",
    "update_outcomes",
    "summarize_signals",
    "format_signal_summary",
    "check_structure",
    "check_conditional",
    "check_grounding",
    "evaluate_report",
    "format_evaluation",
    "ToolCallCounter",
    "timed_run",
    "format_metrics",
]
