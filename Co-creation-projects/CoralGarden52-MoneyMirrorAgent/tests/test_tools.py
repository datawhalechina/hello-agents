from pathlib import Path

from src.tools import AnomalyDetectionTool, BudgetCalculatorTool, CSVImportTool, StatisticsTool, SubscriptionDetectorTool
from src.agents.coordinator import MoneyMirrorCoordinator
from src.agents.transaction_agent import TransactionAgent
from src.memory import SQLiteMemory

from .fakes import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]


def classified_transactions():
    memory = SQLiteMemory(":memory:")
    imported = CSVImportTool().load(ROOT / "data" / "sample_01.csv")
    transactions, _ = TransactionAgent(memory, FakeRuntime()).run(imported)
    return memory, transactions


def test_statistics_anomaly_budget_and_subscription_are_data_driven() -> None:
    memory, transactions = classified_transactions()
    try:
        stats = StatisticsTool()
        summary = stats.summarize(transactions, "2026-07")
        assert summary["income"] == 7600
        assert summary["expense"] > 6000
        assert stats.patterns(transactions, "2026-07")["late_night"]["count"] >= 3
        anomalies = AnomalyDetectionTool().detect(transactions, "2026-07")
        assert any(item.merchant == "京东-电脑配件商城" for item in anomalies)
        budget = BudgetCalculatorTool().calculate(transactions, "2026-07")
        assert budget["categories"]["住房"]["bucket"] == "fixed"
        assert budget["categories"]["娱乐"]["bucket"] == "optional"
        assert budget["categories"]["餐饮"]["bucket"] == "necessary"
        subscriptions = SubscriptionDetectorTool().detect(transactions)
        names = {item["merchant"] for item in subscriptions}
        assert "腾讯视频会员" in names
        assert "房东-六月房租" not in names
        assert "星巴克" not in names
        assert "万达影院" not in names
        assert "滴滴出行" not in names
    finally:
        memory.close()


def test_hello_agents_registry_exposes_all_deterministic_tools() -> None:
    memory, transactions = classified_transactions()
    try:
        coordinator = MoneyMirrorCoordinator(":memory:", runtime=FakeRuntime())
        try:
            names = set(coordinator.runtime.status_dict()["registered_tools"])
            assert names == {
                "CSVImportTool",
                "TransactionCategoryTool",
                "StatisticsTool",
                "AnomalyDetectionTool",
                "BudgetCalculatorTool",
                "GoalProjectionTool",
                "SubscriptionDetectorTool",
                "QuestProgressTool",
            }
        finally:
            coordinator.close()
    finally:
        memory.close()
