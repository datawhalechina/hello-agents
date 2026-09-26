"""PatternAgent plans deterministic tool use for patterns and anomalies."""

from __future__ import annotations

import json
from typing import Iterable

from ..models import Transaction
from ..tools import AnomalyDetectionTool, StatisticsTool, SubscriptionDetectorTool
from .runtime import HelloAgentsRuntime


class PatternAgent:
    paradigm = "PlanAndSolveAgent-style: plan metrics → call statistical tools → return evidence"

    def __init__(self, runtime: HelloAgentsRuntime | None = None) -> None:
        self.runtime = runtime
        self.statistics = StatisticsTool()
        self.anomalies = AnomalyDetectionTool()
        self.subscriptions = SubscriptionDetectorTool()

    def run(self, transactions: Iterable[Transaction], month: str) -> tuple[dict, list, list[dict], dict]:
        items = list(transactions)
        patterns = self.statistics.patterns(items, month)
        anomalies = self.anomalies.detect(items, month)
        subscriptions = self.subscriptions.detect(items)
        evidence = {
            "late_night_count": patterns["late_night"]["count"],
            "anomaly_count": len(anomalies),
            "subscription_count": len(subscriptions),
        }
        planning_note = "Python 工具已按深夜、周末、工资到账窗口、异常和连续扣费顺序完成统计。"
        if self.runtime is not None:
            planning_note = self.runtime.explain(
                "请用一句话说明下一步应如何解读这组已验证的消费模式证据，不要重新计算金额。",
                mode="plan",
                evidence=[json.dumps(evidence, ensure_ascii=False)],
            )
        trace = {
            "agent": "PatternAgent",
            "paradigm": self.paradigm,
            "tools": ["StatisticsTool", "AnomalyDetectionTool", "SubscriptionDetectorTool"],
            "evidence": evidence,
            "planning_note": planning_note,
        }
        return patterns, anomalies, subscriptions, trace
