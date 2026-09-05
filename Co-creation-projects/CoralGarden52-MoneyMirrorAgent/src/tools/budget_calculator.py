"""Behavior-aware next-month budget calculation."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Iterable

from ..models import Transaction


class BudgetCalculatorTool:
    fixed_categories = {"住房", "订阅"}
    necessary_categories = {"餐饮", "交通", "学习", "健身", "医疗"}
    # ``flexible`` is adjustable but still part of daily life; ``optional``
    # represents discretionary experiences and shopping that can be paused.
    flexible_categories = {"其他"}
    optional_categories = {"娱乐", "购物"}

    def calculate(self, transactions: Iterable[Transaction], month: str | None = None) -> dict:
        items = [x for x in transactions if x.kind == "expense"]
        by_month_category: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for item in items:
            by_month_category[item.date.strftime("%Y-%m")][item.category] += item.amount
        months = sorted(by_month_category)
        history = months[:-1] if month and month in months else months
        if not history:
            history = months
        categories = sorted({cat for values in by_month_category.values() for cat in values})
        lines: dict[str, dict] = {}
        for category in categories:
            values = [by_month_category[m].get(category, 0.0) for m in history]
            baseline = median(values) if values else 0.0
            if category in self.fixed_categories:
                recommended = baseline
                bucket = "fixed"
                rationale = "固定支出，原则上不做大幅削减"
            elif category in self.necessary_categories:
                recommended = max(baseline * 0.97, baseline - 80) if baseline else 0.0
                bucket = "necessary"
                rationale = "必要支出，参考历史中位数并保留缓冲"
            elif category in self.optional_categories:
                recommended = max(baseline * 0.85, baseline - 120) if baseline else 0.0
                bucket = "optional"
                rationale = "可选支出，保留真实体验额度并设置温和上限"
            else:
                recommended = max(baseline * 0.9, baseline - 80) if baseline else 0.0
                bucket = "flexible"
                rationale = "弹性支出，结合历史行为小幅调整"
            lines[category] = {"bucket": bucket, "historical_median": round(baseline, 2), "recommended": round(recommended, 2), "rationale": rationale}
        total = round(sum(item["recommended"] for item in lines.values()), 2)
        return {"month": month, "categories": lines, "recommended_total": total, "historical_months": history, "principle": "基于历史中位数，固定支出不削减，必要/弹性/可选支出分层温和调整"}
