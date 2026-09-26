"""Deterministic cash-flow, category, trend, and behavior statistics."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from typing import Iterable

from ..models import Transaction


class StatisticsTool:
    def summarize(self, transactions: Iterable[Transaction], month: str | None = None) -> dict:
        items = [item for item in transactions if not month or item.date.strftime("%Y-%m") == month]
        income = round(sum(item.amount for item in items if item.kind == "income"), 2)
        expense = round(sum(item.amount for item in items if item.kind == "expense"), 2)
        balance = round(income - expense, 2)
        return {
            "transaction_count": len(items),
            "income": income,
            "expense": expense,
            "balance": balance,
            "savings_rate": round(balance / income * 100, 2) if income else 0.0,
            "average_expense": round(expense / max(1, sum(1 for x in items if x.kind == "expense")), 2),
            "active_days": len({item.date.isoformat() for item in items if item.kind == "expense"}),
        }

    def category_breakdown(self, transactions: Iterable[Transaction], month: str | None = None) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for item in transactions:
            if item.kind == "expense" and (not month or item.date.strftime("%Y-%m") == month):
                totals[item.category] += item.amount
        return dict(sorted(((key, round(value, 2)) for key, value in totals.items()), key=lambda pair: pair[1], reverse=True))

    def trends(self, transactions: Iterable[Transaction], month: str | None = None) -> dict[str, dict[str, float]]:
        daily: dict[str, float] = defaultdict(float)
        weekly: dict[str, float] = defaultdict(float)
        monthly: dict[str, float] = defaultdict(float)
        for item in transactions:
            if item.kind != "expense" or (month and item.date.strftime("%Y-%m") != month):
                continue
            daily[item.date.isoformat()] += item.amount
            monday = item.date - timedelta(days=item.date.weekday())
            weekly[monday.isoformat()] += item.amount
            monthly[item.date.strftime("%Y-%m")] += item.amount
        return {
            "daily": dict(sorted((key, round(value, 2)) for key, value in daily.items())),
            "weekly": dict(sorted((key, round(value, 2)) for key, value in weekly.items())),
            "monthly": dict(sorted((key, round(value, 2)) for key, value in monthly.items())),
        }

    def patterns(self, transactions: Iterable[Transaction], month: str | None = None) -> dict:
        items = [item for item in transactions if item.kind == "expense" and (not month or item.date.strftime("%Y-%m") == month)]
        if not items:
            return {"late_night": {"count": 0, "amount": 0.0}, "weekend": {"count": 0, "amount": 0.0}, "payday_window": {"count": 0, "amount": 0.0}, "frequent_small": {"count": 0, "amount": 0.0}, "category_spikes": {}}
        late = [x for x in items if x.hour >= 22 or x.hour < 6]
        weekend = [x for x in items if x.date.weekday() >= 5]
        income_dates = {x.date for x in transactions if x.kind == "income"}
        payday = [x for x in items if any(0 <= (x.date - income_date).days <= 3 for income_date in income_dates)]
        small = [x for x in items if x.amount <= 50]
        category_amounts: dict[str, float] = defaultdict(float)
        for x in items:
            category_amounts[x.category] += x.amount
        return {
            "late_night": {"count": len(late), "amount": round(sum(x.amount for x in late), 2), "share": round(sum(x.amount for x in late) / sum(x.amount for x in items) * 100, 2)},
            "weekend": {"count": len(weekend), "amount": round(sum(x.amount for x in weekend), 2), "share": round(sum(x.amount for x in weekend) / sum(x.amount for x in items) * 100, 2)},
            "payday_window": {"count": len(payday), "amount": round(sum(x.amount for x in payday), 2), "share": round(sum(x.amount for x in payday) / sum(x.amount for x in items) * 100, 2)},
            "frequent_small": {"count": len(small), "amount": round(sum(x.amount for x in small), 2), "average": round(mean(x.amount for x in small), 2) if small else 0.0},
            "category_spikes": {key: round(value, 2) for key, value in sorted(category_amounts.items(), key=lambda pair: pair[1], reverse=True)},
        }

    def month_keys(self, transactions: Iterable[Transaction]) -> list[str]:
        return sorted({item.date.strftime("%Y-%m") for item in transactions})

    def monthly_category_totals(self, transactions: Iterable[Transaction]) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for item in transactions:
            if item.kind == "expense":
                result[item.date.strftime("%Y-%m")][item.category] += item.amount
        return {month: {cat: round(value, 2) for cat, value in cats.items()} for month, cats in sorted(result.items())}

    @staticmethod
    def historical_average(values: list[float]) -> float:
        return round(mean(values), 2) if values else 0.0

    @staticmethod
    def historical_median(values: list[float]) -> float:
        return round(median(values), 2) if values else 0.0
