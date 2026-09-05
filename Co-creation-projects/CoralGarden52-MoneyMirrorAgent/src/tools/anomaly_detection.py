"""Transparent IQR, z-score, and median-ratio anomaly detection."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Iterable

from ..models import Anomaly, Transaction


class AnomalyDetectionTool:
    def detect(self, transactions: Iterable[Transaction], month: str | None = None) -> list[Anomaly]:
        items = [x for x in transactions if x.kind == "expense" and (not month or x.date.strftime("%Y-%m") == month)]
        by_category: dict[str, list[float]] = defaultdict(list)
        for item in items:
            by_category[item.category].append(item.amount)
        anomalies: list[Anomaly] = []
        for item in items:
            values = by_category[item.category]
            if len(values) < 4:
                # For sparse categories, use a conservative median multiplier.
                # A 2.5x ratio still requires a meaningful amount gap, while
                # making three-point categories (for example, shopping) useful.
                baseline = median(values) if values else 0
                if baseline and item.amount >= max(2.5 * baseline, baseline + 200):
                    anomalies.append(Anomaly(item.transaction_id, item.merchant, item.category, item.amount, item.occurred_at, "sparse-median", round(item.amount / baseline, 2), f"金额约为该类别中位数的 {item.amount / baseline:.1f} 倍"))
                continue
            ordered = sorted(values)
            category_median = median(values)
            # IQR and z-score are intentionally complemented by a large
            # median-ratio guard. In small, skewed categories a single large
            # purchase can pull Q3 and the mean upward, hiding the very event
            # a user expects the agent to explain (for example a ¥1,288
            # electronics purchase among ordinary shopping transactions).
            median_upper = max(3 * category_median, category_median + 500)
            if item.amount >= median_upper:
                ratio = item.amount / category_median if category_median else 0.0
                anomalies.append(Anomaly(item.transaction_id, item.merchant, item.category, item.amount, item.occurred_at, "median-ratio", round(ratio, 2), f"金额约为该类别中位数的 {ratio:.1f} 倍"))
                continue
            q1 = self._percentile(ordered, 0.25)
            q3 = self._percentile(ordered, 0.75)
            iqr = q3 - q1
            upper = q3 + 1.5 * iqr
            category_mean = mean(values)
            deviation = pstdev(values)
            z = (item.amount - category_mean) / deviation if deviation else 0.0
            if item.amount > upper:
                anomalies.append(Anomaly(item.transaction_id, item.merchant, item.category, item.amount, item.occurred_at, "IQR", round(z, 2), f"高于 {item.category} 类别 IQR 上界 {upper:.2f}"))
            elif abs(z) >= 2.5:
                anomalies.append(Anomaly(item.transaction_id, item.merchant, item.category, item.amount, item.occurred_at, "Z-score", round(z, 2), f"相对该类别均值偏离 {z:.1f} 个标准差"))
        return sorted(anomalies, key=lambda item: item.amount, reverse=True)

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float:
        if len(values) == 1:
            return values[0]
        position = (len(values) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        return values[lower] + (values[upper] - values[lower]) * (position - lower)
