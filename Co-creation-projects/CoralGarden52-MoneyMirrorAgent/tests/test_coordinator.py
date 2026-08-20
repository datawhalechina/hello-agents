from pathlib import Path

from src.agents.coordinator import MoneyMirrorCoordinator
from src.models import Goal

from .fakes import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_complete_demo_pipeline_persists_memory_and_reflects(tmp_path: Path) -> None:
    coordinator = MoneyMirrorCoordinator(tmp_path / "memory.db", "test_user", runtime=FakeRuntime())
    try:
        coordinator.add_goal(Goal("travel_fund_2026", "三个月旅行基金", "travel", 10000, 2800, "2026-10-31"))
        report = coordinator.analyze_csv(ROOT / "data" / "sample_01.csv")
        assert report.month == "2026-07"
        assert report.summary["balance"] == 1026
        assert report.persona["primary"]
        assert report.quests
        assert report.gamification["level"] >= 1
        assert "longest_streak_days" in report.gamification
        assert report.reflection["has_previous_snapshot"] is True
        assert report.reflection["next_cycle_month"] == "2026-08"
        assert report.reflection["next_cycle_budget"]["categories"]
        assert report.reflection["next_cycle_quests"]
        assert coordinator.memory.get_budget("2026-08") is not None
        assert report.goals[0]["required_monthly_amount"] > 0
        assert coordinator.memory.get_snapshot("2026-07") is not None
        coordinator.correct_merchant_category("测试奶茶店", "餐饮")
        assert coordinator.memory.get_merchant_category("测试奶茶店") == "餐饮"
        json_path, markdown_path = coordinator.write_outputs(
            report,
            tmp_path / "outputs",
            source_csv=ROOT / "data" / "sample_01.csv",
        )
        assert json_path.name == "sample_01_money_mirror_report.json"
        assert markdown_path.name == "sample_01_money_mirror_report.md"
        assert json_path.exists() and markdown_path.exists()
    finally:
        coordinator.close()


def test_output_stem_uses_input_csv_basename() -> None:
    assert MoneyMirrorCoordinator._output_stem("data/sample_01.csv") == "sample_01_money_mirror_report"
    assert MoneyMirrorCoordinator._output_stem("/tmp/八月账单.csv") == "八月账单_money_mirror_report"
