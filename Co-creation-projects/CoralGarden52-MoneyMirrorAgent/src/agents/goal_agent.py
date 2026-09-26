"""GoalAgent: feasibility comes from GoalProjectionTool, not an LLM guess."""

from __future__ import annotations

import json
from typing import Iterable

from ..memory import SQLiteMemory
from ..models import Goal, Transaction
from ..tools.goal_projection import GoalProjectionTool
from .runtime import HelloAgentsRuntime


class GoalAgent:
    paradigm = "PlanAndSolveAgent-style goal feasibility projection"

    def __init__(self, memory: SQLiteMemory, runtime: HelloAgentsRuntime | None = None) -> None:
        self.memory = memory
        self.runtime = runtime
        self.tool = GoalProjectionTool()

    def run(self, transactions: Iterable[Transaction], month: str) -> tuple[list[dict], dict]:
        goals = [Goal(**item) for item in self.memory.list_goals(active_only=True)]
        results = [self.tool.project(goal, transactions, month) for goal in goals]
        planning_note = (
            "GoalProjectionTool 已根据现金流、历史结余和截止日期计算可行性。"
            if results
            else "当前没有已保存的财务目标；可通过 CLI 的 Memory 配置或后续输入创建目标，避免替真实用户臆造目标。"
        )
        if self.runtime is not None:
            planning_note = self.runtime.explain(
                "请用一句话说明如何把目标投影转成下一步行动；不得修改工具计算出的金额。",
                mode="plan",
                evidence=[json.dumps(results, ensure_ascii=False)],
            )
        return results, {"agent": "GoalAgent", "paradigm": self.paradigm, "tools": ["GoalProjectionTool"], "goal_count": len(results), "planning_note": planning_note}
