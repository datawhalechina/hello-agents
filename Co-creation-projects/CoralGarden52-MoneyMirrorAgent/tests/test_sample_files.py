"""Coverage for bundled fictional bill files and the explicit CSV CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from main import _parse_goal, parser
from src.agents.coordinator import MoneyMirrorCoordinator
from src.tools import CSVImportTool

from .fakes import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILES = tuple(ROOT / "data" / f"sample_{index:02d}.csv" for index in range(1, 6))


def test_all_bundled_sample_files_exist_and_import() -> None:
    importer = CSVImportTool()
    assert len(SAMPLE_FILES) == 5
    for index, path in enumerate(SAMPLE_FILES, start=1):
        assert path.is_file(), f"sample-{index:02d} is missing its CSV: {path}"
        transactions = importer.load(path)
        assert transactions, f"sample-{index:02d} should contain transactions"
        assert not importer.last_errors, f"sample-{index:02d} has invalid rows: {importer.last_errors}"


def test_samples_produce_distinct_data_grounded_quest_signals(tmp_path) -> None:
    quest_ids: dict[str, set[str]] = {}
    subscription_merchants: dict[str, set[str]] = {}
    for index, path in enumerate(SAMPLE_FILES, start=1):
        sample_id = f"sample-{index:02d}"
        coordinator = MoneyMirrorCoordinator(tmp_path / f"{sample_id}.db", runtime=FakeRuntime())
        try:
            report = coordinator.analyze_csv(path)
            assert report.summary["income"] > 0
            assert report.summary["expense"] > 0
            assert report.quests
            quest_ids[sample_id] = {quest.quest_id for quest in report.quests}
            subscription_merchants[sample_id] = {item["merchant"] for item in report.subscriptions}
        finally:
            coordinator.close()

    assert "weekend_wallet_shield" in quest_ids["sample-03"]
    assert "payday_cooldown" in quest_ids["sample-04"]
    assert "learning_loot_log" in quest_ids["sample-02"]
    assert "subscription_hunter" in quest_ids["sample-05"]
    assert "房东-六月房租" not in subscription_merchants["sample-04"]
    assert "腾讯视频会员" in subscription_merchants["sample-05"]
    assert len({tuple(sorted(ids)) for ids in quest_ids.values()}) >= 4


def test_csv_path_is_required_and_demo_flag_is_removed() -> None:
    command = parser()
    args = command.parse_args(["--csv", "bill.csv"])
    assert args.csv == Path("bill.csv")
    assert args.interactive is False
    assert not hasattr(args, "demo")

    interactive_args = command.parse_args(["--interactive", "--csv", "bill.csv"])
    assert interactive_args.interactive is True
    with pytest.raises(SystemExit):
        command.parse_args([])
    with pytest.raises(SystemExit):
        command.parse_args(["--demo", "--csv", "bill.csv"])


def test_cli_goal_parsing_is_explicit_and_validated() -> None:
    travel = _parse_goal("三个月旅行基金|travel|10000|2800|2026-10-31")
    assert travel.goal_type == "travel"
    assert travel.target_amount == 10000
    assert travel.current_amount == 2800

    category = _parse_goal("本月娱乐限额|category_limit|800|0|2026-08-31|娱乐|800")
    assert category.category == "娱乐"
    assert category.monthly_limit == 800

    with pytest.raises(ValueError, match="格式"):
        _parse_goal("格式不完整|travel")
    with pytest.raises(ValueError, match="category_limit"):
        _parse_goal("娱乐限额|category_limit|800|0|2026-08-31")
