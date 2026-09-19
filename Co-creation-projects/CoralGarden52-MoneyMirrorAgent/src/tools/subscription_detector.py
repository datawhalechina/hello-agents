"""Recurring-charge and subscription detector.

Periodicity alone is not enough: people can visit the same canteen, cinema or
station on a similar day every month. A candidate therefore needs both a stable
cross-month amount and semantic evidence that it is a membership/auto-renewal
charge. The tool intentionally returns *suspected* subscriptions only; it never
cancels or modifies a service.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Iterable

from ..models import Transaction


class SubscriptionDetectorTool:
    """Detect likely recurring memberships without mistaking routine spending for one."""

    _RECURRING_MARKERS = ("自动续费", "会员", "订阅", "月卡", "年卡", "续费", "连续扣费")

    @classmethod
    def _has_recurring_evidence(cls, items: list[Transaction]) -> bool:
        """Return semantic evidence supplied by classification or transaction text."""
        if any(item.category == "订阅" for item in items):
            return True
        return any(
            marker in f"{item.merchant} {item.note}".lower()
            for item in items
            for marker in cls._RECURRING_MARKERS
        )

    def detect(self, transactions: Iterable[Transaction]) -> list[dict]:
        groups: dict[str, list[Transaction]] = defaultdict(list)
        for item in transactions:
            if item.kind == "expense":
                groups[item.merchant].append(item)

        result: list[dict] = []
        for merchant, items in groups.items():
            # Rent and other housing costs are deliberately budgeted as fixed living
            # expenses. Although they are periodic, presenting rent as a disposable
            # "subscription" would be misleading and makes the Subscription Hunter
            # less trustworthy.
            if any(item.category == "住房" for item in items):
                continue
            months = sorted({item.date.strftime("%Y-%m") for item in items})
            if len(months) < 2 or not self._has_recurring_evidence(items):
                continue

            amounts = [item.amount for item in items]
            stable_amount = max(amounts) - min(amounts) <= max(10.0, median(amounts) * 0.15)
            if stable_amount:
                latest = items[-1]
                result.append(
                    {
                        "merchant": merchant,
                        "months": months,
                        "occurrences": len(items),
                        "typical_amount": round(median(amounts), 2),
                        "category": latest.category,
                        "low_value_flag": median(amounts) < 100,
                        "message": "连续多月的会员或续费扣款，建议检查是否仍有使用价值",
                    }
                )
        return sorted(result, key=lambda item: item["typical_amount"], reverse=True)
