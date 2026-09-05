"""ReflectionAgent compares persisted plans with actual outcomes."""

from __future__ import annotations

from ..memory import SQLiteMemory
from .runtime import HelloAgentsRuntime


class ReflectionAgent:
    paradigm = "ReflectionAgent-style: plan → actual → deviation → adjustment"

    def __init__(self, memory: SQLiteMemory, runtime: HelloAgentsRuntime) -> None:
        self.memory = memory
        self.runtime = runtime

    def run(self, month: str, summary: dict, categories: dict[str, float], budget: dict, quests: list, goals: list[dict]) -> tuple[dict, dict]:
        previous_month = self._previous_month(month)
        previous_snapshot = self.memory.get_snapshot(previous_month)
        budget_lines = budget.get("categories", {})
        deviations = []
        for category, planned in budget_lines.items():
            actual = categories.get(category, 0.0)
            limit = planned.get("recommended", 0.0)
            if limit:
                deviations.append({"category": category, "planned": limit, "actual": actual, "difference": round(actual - limit, 2), "on_budget": actual <= limit})
        completed = sum(1 for quest in quests if getattr(quest, "status", "active") == "completed")
        goal_state = goals[0] if goals else {}
        strategy = []
        overspent = sorted((item for item in deviations if item["difference"] > 0), key=lambda item: item["difference"], reverse=True)
        if overspent:
            strategy.append(f"优先为 {overspent[0]['category']} 保留明确额度，而不是一刀切禁止消费。")
        if summary.get("savings_rate", 0) < 20:
            strategy.append("把结余转入目标账户的动作安排在收入到账后 24 小时内。")
        if completed == 0 and quests:
            strategy.append("下阶段只保留 2 个可执行任务，降低任务负担。")
        if not strategy:
            strategy.append("当前计划与实际较匹配，维持预算框架并逐步提高目标储蓄。")

        next_month = self._next_month(month)
        next_budget = self._next_cycle_budget(budget_lines, deviations)
        next_cycle_quests = self._next_cycle_quests(quests, overspent, next_budget)
        prior_text = "没有上月快照，本次作为基线月。" if not previous_snapshot else f"已读取 {previous_month} 的历史快照用于比较。"
        narrative = self.runtime.explain(
            f"按 Reflection 模式解释：月度结余={summary.get('balance')}，储蓄率={summary.get('savings_rate')}，任务完成={completed}/{len(quests)}，预算偏差={deviations}，目标={goal_state}。只能基于这些数据给 2-3 句下一周期建议。",
            mode="reflection",
            evidence=[
                f"储蓄率={summary.get('savings_rate', 0):.2f}%",
                f"任务完成={completed}/{len(quests)}",
                f"预算偏差={deviations}",
            ],
            memory=[prior_text],
        )
        reflection = {
            "month": month,
            "previous_month": previous_month,
            "has_previous_snapshot": bool(previous_snapshot),
            "budget_deviations": deviations,
            "quest_completion": {"completed": completed, "total": len(quests)},
            "goal_progress": goal_state,
            "effective": ["预算和任务均基于实际账单计算"],
            "needs_adjustment": [item["category"] for item in overspent],
            "next_strategy": strategy,
            "next_cycle_month": next_month,
            "next_cycle_budget": next_budget,
            "next_cycle_quests": next_cycle_quests,
            "narrative": narrative,
        }
        # Reflection is not just prose: persist the next-cycle artifacts so
        # the following run/dashboard can inspect and act on them.
        self.memory.save_budget(next_month, next_budget)
        self.memory.save_reflection(month, reflection)
        return reflection, {"agent": "ReflectionAgent", "paradigm": self.paradigm, "context_sources": ["SQLiteMemory: previous snapshot", "budget", "quest outcomes", "goal projection"]}

    @staticmethod
    def _previous_month(month: str) -> str:
        year, value = map(int, month.split("-"))
        return f"{year - 1}-12" if value == 1 else f"{year}-{value - 1:02d}"

    @staticmethod
    def _next_month(month: str) -> str:
        year, value = map(int, month.split("-"))
        return f"{year + 1}-01" if value == 12 else f"{year}-{value + 1:02d}"

    @staticmethod
    def _next_cycle_budget(budget_lines: dict, deviations: list[dict]) -> dict:
        """Turn deviations into a gentle next-cycle budget adjustment.

        A large one-off purchase must not cause a punitive cut. For an
        overspent category, the next recommendation becomes a soft ceiling
        between the old plan and 150% of it, capped by 105% of actual spend.
        """

        overspent = {item["category"]: item for item in deviations if item["difference"] > 0}
        categories = {}
        for category, planned in budget_lines.items():
            line = dict(planned)
            if category in overspent:
                actual = overspent[category]["actual"]
                baseline = planned.get("recommended", 0.0)
                line["recommended"] = round(max(baseline, min(actual * 1.05, baseline * 1.5)), 2)
                line["rationale"] = "Reflection 根据实际偏差增加缓冲，避免对一次性消费一刀切"
            categories[category] = line
        return {"source": "monthly_reflection", "categories": categories}

    @staticmethod
    def _next_cycle_quests(quests: list, overspent: list[dict], next_budget: dict) -> list[dict]:
        plans = []
        for quest in quests:
            if getattr(quest, "status", "active") != "completed":
                plans.append({
                    "quest_id": f"carry_{quest.quest_id}",
                    "title": f"延续：{quest.title}",
                    "quest_type": quest.quest_type,
                    "target": quest.target,
                    "unit": quest.unit,
                    "exp_reward": quest.exp_reward,
                    "reason": "上周期未完成，Reflection 建议降低摩擦后继续",
                })
        if overspent:
            category = overspent[0]["category"]
            recommended = next_budget.get("categories", {}).get(category, {}).get("recommended", 0.0)
            plans.append({
                "quest_id": f"reflection_{category}",
                "title": f"{category}缓冲预算挑战",
                "quest_type": "category_limit",
                "target": recommended,
                "unit": category,
                "exp_reward": 100,
                "reason": "根据本月最大预算偏差生成",
            })
        return plans or [{"quest_id": "reflection_checkin", "title": "月度镜像回顾", "quest_type": "reflection_checkin", "target": 1, "unit": "次", "exp_reward": 60, "reason": "保持有效计划"}]
