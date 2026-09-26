"""Savings and category-limit feasibility calculations."""

from __future__ import annotations

from datetime import date
from math import ceil
from typing import Iterable

from ..models import Goal, Transaction


class GoalProjectionTool:
    def project(self, goal: Goal, transactions: Iterable[Transaction], current_month: str | None = None) -> dict:
        items = list(transactions)
        if current_month:
            current = date.fromisoformat(f"{current_month}-01")
        else:
            current = max((item.date for item in items), default=date.today()).replace(day=1)
        deadline = date.fromisoformat(goal.deadline[:10]).replace(day=1)
        months_left = max(1, (deadline.year - current.year) * 12 + deadline.month - current.month + 1)
        income_by_month: dict[str, float] = {}
        expenses_by_month: dict[str, float] = {}
        category_total = 0.0
        for item in items:
            key = item.date.strftime("%Y-%m")
            if item.kind == "income":
                income_by_month[key] = income_by_month.get(key, 0.0) + item.amount
            else:
                expenses_by_month[key] = expenses_by_month.get(key, 0.0) + item.amount
                if goal.category and item.category == goal.category and key == current.strftime("%Y-%m"):
                    category_total += item.amount
        months = sorted(set(income_by_month) | set(expenses_by_month))
        surpluses = [income_by_month.get(key, 0.0) - expenses_by_month.get(key, 0.0) for key in months if income_by_month.get(key, 0.0)]
        average_surplus = sum(surpluses) / len(surpluses) if surpluses else 0.0
        if goal.goal_type == "category_limit" and goal.category:
            required = max(0.0, (goal.monthly_limit or goal.target_amount) - category_total)
            feasible = category_total <= (goal.monthly_limit or goal.target_amount)
            projected = category_total
        else:
            remaining = max(0.0, goal.target_amount - goal.current_amount)
            required = remaining / months_left
            feasible = average_surplus >= required
            projected = goal.current_amount + max(0.0, average_surplus) * months_left
        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "goal_type": goal.goal_type,
            "target_amount": round(goal.target_amount, 2),
            "current_amount": round(goal.current_amount, 2),
            "deadline": goal.deadline,
            "months_left": months_left,
            "required_monthly_amount": round(required, 2),
            "average_monthly_surplus": round(average_surplus, 2),
            "projected_amount": round(projected, 2),
            "progress_percent": round(min(100.0, goal.current_amount / goal.target_amount * 100) if goal.target_amount else 0.0, 2),
            "feasible": feasible,
            "advice": "当前现金流支持该目标" if feasible else "目标偏紧，建议延长期限或降低阶段性目标",
        }
