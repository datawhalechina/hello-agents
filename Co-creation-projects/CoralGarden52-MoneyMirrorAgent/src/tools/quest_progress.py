"""Quest progress calculations: deterministic evidence, no invented completion."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from ..models import Quest, Transaction


class QuestProgressTool:
    def update(self, quest: Quest, transactions: Iterable[Transaction], month: str | None = None) -> Quest:
        items = [x for x in transactions if x.kind == "expense" and (not month or x.date.strftime("%Y-%m") == month)]
        if quest.quest_type == "zero_spend_days":
            all_days = {x.date for x in items}
            if all_days:
                start, end = min(all_days), max(all_days)
                days = 0
                cursor = start
                while cursor <= end:
                    if cursor not in all_days:
                        days += 1
                    cursor += timedelta(days=1)
                quest.progress = min(quest.target, float(days))
                quest.evidence = f"分析区间内发现 {days} 个无支出日"
        elif quest.quest_type == "late_night_limit":
            late = [x for x in items if x.hour >= 22 or x.hour < 6]
            quest.progress = max(0.0, quest.target - len(late))
            quest.evidence = f"深夜消费 {len(late)} 笔，目标最多 {quest.target:.0f} 笔"
        elif quest.quest_type == "category_limit":
            spent = sum(x.amount for x in items if x.category == quest.unit)
            quest.progress = max(0.0, quest.target - spent)
            quest.evidence = f"{quest.unit} 已消费 ¥{spent:.2f}，预算上限 ¥{quest.target:.2f}"
        elif quest.quest_type == "weekend_spend_limit":
            spent = sum(x.amount for x in items if x.date.weekday() >= 5)
            quest.progress = max(0.0, quest.target - spent)
            quest.evidence = f"周末已消费 ¥{spent:.2f}，温和上限 ¥{quest.target:.2f}"
        elif quest.quest_type == "payday_window_limit":
            income_dates = {x.date for x in transactions if x.kind == "income" and (not month or x.date.strftime("%Y-%m") == month)}
            spent = sum(
                x.amount
                for x in items
                if any(0 <= (x.date - income_date).days <= 3 for income_date in income_dates)
            )
            quest.progress = max(0.0, quest.target - spent)
            quest.evidence = f"工资到账后 3 天内已消费 ¥{spent:.2f}，温和上限 ¥{quest.target:.2f}"
        elif quest.quest_type == "subscription_review":
            quest.progress = min(quest.target, 0.0)
            quest.evidence = "需要用户在后续 CLI 引导中确认完成"
        else:
            quest.evidence = "等待用户更新进度"
        if quest.quest_type in {"zero_spend_days", "late_night_limit", "category_limit", "weekend_spend_limit", "payday_window_limit"} and quest.progress >= quest.target:
            quest.status = "completed"
        return quest
    def max_zero_spend_streak(self, transactions: Iterable[Transaction], month: str | None = None) -> int:
        """Return the longest consecutive no-expense-day streak in a period."""

        items = [x for x in transactions if x.kind == "expense" and (not month or x.date.strftime("%Y-%m") == month)]
        if not items:
            return 0
        spent_days = {x.date for x in items}
        start, end = min(spent_days), max(spent_days)
        longest = current = 0
        cursor = start
        while cursor <= end:
            if cursor in spent_days:
                current = 0
            else:
                current += 1
                longest = max(longest, current)
            cursor += timedelta(days=1)
        return longest

