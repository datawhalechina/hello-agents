"""课程学习系统 - 可视化报告生成器

生成课程进度的可视化报告：
1. 性能趋势图（文本表格）
2. 工具使用热力图（文本表格）
3. 阶段过渡状态
4. 综合评估报告
"""

from __future__ import annotations

from typing import List, Any
from .types import CurriculumState, StageProgress


class CurriculumVisualizer:
    """课程可视化报告生成器

    生成纯文本形式的可视化报告（不依赖matplotlib等外部库）。
    适合在命令行和日志中展示。
    """

    @staticmethod
    def render_progress_bar(
        current: int, total: int, width: int = 30, label: str = ""
    ) -> str:
        """渲染进度条"""
        if total == 0:
            filled = 0
        else:
            filled = int(current / total * width)
        bar = "█" * filled + "░" * (width - filled)
        pct = current / max(total, 1) * 100
        label_part = f" {label}" if label else ""
        return f"{bar} {current}/{total} ({pct:.0f}%){label_part}"

    @staticmethod
    def render_stage_table(state: CurriculumState, stage_defs: List[Any]) -> str:
        """渲染阶段进度表"""
        lines = []
        lines.append(
            f"{'Stage':<50s} {'Tasks':>6s} {'Succ':>6s} {'Rate':>6s} "
            f"{'Reward':>8s} {'Eff.':>6s} {'Status':>10s}"
        )
        lines.append("-" * 92)

        for i, sp in enumerate(state.stages):
            stage_name = sp.stage_id[:48]
            if i <= state.current_stage_index and i < len(stage_defs):
                sd = stage_defs[i]
                stage_name = f"[{sd.stage_type.value[:8]}] {sd.name[:38]}"

            status = (
                "✓ DONE"
                if sp.is_completed
                else "→ NOW"
                if i == state.current_stage_index
                else "⏳ PEND"
            )

            lines.append(
                f"{stage_name:<50s} "
                f"{sp.tasks_completed:>6d} "
                f"{sp.tasks_succeeded:>6d} "
                f"{sp.success_rate:>6.2f} "
                f"{sp.avg_reward:>8.3f} "
                f"{sp.efficiency:>6.2f} "
                f"{status:>10s}"
            )

        return "\n".join(lines)

    @staticmethod
    def render_tool_heatmap(state: CurriculumState) -> str:
        """渲染工具使用热力图（文本形式）"""
        if not state.all_tool_usage:
            return "No tool usage data yet."

        total = sum(state.all_tool_usage.values())
        if total == 0:
            return "No tool usage data yet."

        max_count = max(state.all_tool_usage.values())
        lines = ["Tool Usage Heatmap:"]
        for tool, count in sorted(state.all_tool_usage.items()):
            pct = count / max(max_count, 1)
            bar_length = int(pct * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            lines.append(
                f"  {tool:<20s} |{bar}| {count:4d}x ({count / total * 100:5.1f}%)"
            )

        return "\n".join(lines)

    @staticmethod
    def render_difficulty_chart(adapter: Any, width: int = 40) -> str:
        """渲染难度变化图"""
        history = adapter.get_adjustment_history()
        if not history:
            return "No difficulty data yet."

        # 采样最近的值
        step = max(1, len(history) // width)
        sampled = history[::step][:width]

        lines = ["Difficulty Trend (█ = 0.5 baseline):"]
        chart = ""
        for d in sampled:
            if d > 0.55:
                chart += "▲"
            elif d < 0.45:
                chart += "▼"
            else:
                chart += "─"
        lines.append(f"  {chart}")
        lines.append(
            f"  Current: {sampled[-1]:.2f} | "
            f"Min: {min(sampled):.2f} | "
            f"Max: {max(sampled):.2f}"
        )
        return "\n".join(lines)

    @staticmethod
    def render_performance_metrics(state: CurriculumState) -> str:
        """渲染性能指标摘要"""
        current = (
            state.stages[state.current_stage_index]
            if state.stages
            else StageProgress(stage_id="")
        )
        lines = [
            "Performance Metrics:",
            f"  Global Tasks: {state.global_tasks_completed}",
            f"  Global Avg Reward: {state.global_avg_reward:.4f}",
            f"  Current Stage Tasks: {current.tasks_completed}",
            f"  Current Success Rate: {current.success_rate:.2%}",
            f"  Current Efficiency: {current.efficiency:.2%}",
            f"  Difficulty Level: {state.difficulty_level:.2f}",
            f"  Bottleneck: {current.bottleneck or 'N/A'}",
        ]
        return "\n".join(lines)

    @staticmethod
    def render_full_report(
        state: CurriculumState,
        stage_defs: List[Any],
        adapter: Any,
    ) -> str:
        """渲染完整报告"""
        lines = []
        lines.append("=" * 92)
        lines.append("  CURRICULUM LEARNING REPORT")
        lines.append("=" * 92)
        lines.append("")
        lines.append(CurriculumVisualizer.render_performance_metrics(state))
        lines.append("")
        lines.append("--- Stage Progress ---")
        lines.append(CurriculumVisualizer.render_stage_table(state, stage_defs))
        lines.append("")
        lines.append("--- Tool Usage ---")
        lines.append(CurriculumVisualizer.render_tool_heatmap(state))
        lines.append("")
        lines.append("--- Difficulty Trend ---")
        lines.append(CurriculumVisualizer.render_difficulty_chart(adapter))
        lines.append("")
        lines.append("=" * 92)
        return "\n".join(lines)
