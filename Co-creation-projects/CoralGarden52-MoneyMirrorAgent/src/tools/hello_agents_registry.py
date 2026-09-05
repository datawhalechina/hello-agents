"""JSON adapters that expose MoneyMirror tools through Hello-Agents ToolRegistry.

The coordinator still calls the Python tools directly for the normal pipeline.
These small adapters make the same deterministic capabilities available to a
Hello-Agents ReAct agent without moving financial arithmetic into an LLM.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Any, Callable

from ..models import Goal, Quest, Transaction
from .anomaly_detection import AnomalyDetectionTool
from .budget_calculator import BudgetCalculatorTool
from .csv_import import CSVImportTool
from .goal_projection import GoalProjectionTool
from .quest_progress import QuestProgressTool
from .statistics import StatisticsTool
from .subscription_detector import SubscriptionDetectorTool
from .transaction_category import TransactionCategoryTool


def _payload(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"input": raw}
    return value if isinstance(value, dict) else {"input": value}


def _transactions(payload: dict[str, Any]) -> list[Transaction]:
    fields = {
        "transaction_id",
        "occurred_at",
        "merchant",
        "amount",
        "kind",
        "category",
        "note",
        "source",
        "category_confidence",
    }
    return [Transaction(**{key: item[key] for key in fields if key in item}) for item in payload.get("transactions", [])]


def _json(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif isinstance(value, list):
        value = [item.to_dict() if hasattr(item, "to_dict") else item for item in value]
    return json.dumps(value, ensure_ascii=False, default=str)


def build_registry_functions(
    csv_import: CSVImportTool,
    category: TransactionCategoryTool,
    statistics: StatisticsTool,
    anomalies: AnomalyDetectionTool,
    budget: BudgetCalculatorTool,
    projection: GoalProjectionTool,
    subscriptions: SubscriptionDetectorTool,
    quest_progress: QuestProgressTool,
    memory_lookup: Callable[[str], str | None],
) -> dict[str, tuple[Callable[[str | dict[str, Any]], str], str]]:
    """Build function tools with stable JSON-in/JSON-out contracts."""

    def import_csv(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        transactions = csv_import.load(StringIO(str(data.get("csv_text", ""))))
        return _json([item.to_dict() for item in transactions])

    def classify_transaction(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        transaction = Transaction(
            transaction_id=str(data.get("transaction_id", "registry")),
            occurred_at=str(data.get("occurred_at", "2000-01-01T12:00")),
            merchant=str(data.get("merchant", "未知商户")),
            amount=float(data.get("amount", 0)),
            kind=data.get("kind", "expense"),
            note=str(data.get("note", "")),
        )
        result = category.classify(transaction, memory_lookup)
        return _json({
            "category": result.category,
            "confidence": result.confidence,
            "source": result.source,
        })

    def summarize(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        return _json(statistics.summarize(_transactions(data), data.get("month")))

    def detect_anomalies(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        return _json(anomalies.detect(_transactions(data), data.get("month")))

    def calculate_budget(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        return _json(budget.calculate(_transactions(data), str(data.get("month"))))

    def project_goal(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        return _json(projection.project(Goal(**data["goal"]), _transactions(data), data.get("month")))

    def detect_subscriptions(raw: str | dict[str, Any]) -> str:
        return _json(subscriptions.detect(_transactions(_payload(raw))))

    def update_quest(raw: str | dict[str, Any]) -> str:
        data = _payload(raw)
        quest = quest_progress.update(Quest(**data["quest"]), _transactions(data), data.get("month"))
        return _json(quest)

    return {
        "CSVImportTool": (import_csv, "从 csv_text 导入并规范化账单交易"),
        "TransactionCategoryTool": (classify_transaction, "按 Memory 和规则为一笔交易分类"),
        "StatisticsTool": (summarize, "计算收入、支出、结余和消费统计"),
        "AnomalyDetectionTool": (detect_anomalies, "使用确定性统计方法检测异常消费"),
        "BudgetCalculatorTool": (calculate_budget, "根据历史消费计算动态预算"),
        "GoalProjectionTool": (project_goal, "投影财务目标可行性和所需月度额度"),
        "SubscriptionDetectorTool": (detect_subscriptions, "识别疑似周期性订阅扣费"),
        "QuestProgressTool": (update_quest, "根据真实交易更新 Money Quest 进度"),
    }
