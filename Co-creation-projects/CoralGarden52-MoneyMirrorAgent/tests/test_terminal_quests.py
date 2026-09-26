"""Terminal-only Quest completion behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.coordinator import MoneyMirrorCoordinator

from .fakes import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_cli_can_confirm_subscription_quest_and_memory_preserves_it(tmp_path: Path) -> None:
    coordinator = MoneyMirrorCoordinator(tmp_path / "memory.db", runtime=FakeRuntime())
    try:
        report = coordinator.analyze_csv(ROOT / "data" / "sample_01.csv")
        result = coordinator.complete_quest(report, "subscription_hunter", "已检查三个订阅")
        quest = next(item for item in report.quests if item.quest_id == "subscription_hunter")
        assert quest.status == "completed"
        assert quest.progress == quest.target
        assert result["gained_exp"] == quest.exp_reward

        # Re-analyzing the same monthly bill must retain the user-confirmed
        # review rather than letting deterministic transaction parsing erase it.
        refreshed = coordinator.analyze_csv(ROOT / "data" / "sample_01.csv")
        refreshed_quest = next(item for item in refreshed.quests if item.quest_id == "subscription_hunter")
        assert refreshed_quest.status == "completed"
        assert "CLI" in refreshed_quest.evidence
    finally:
        coordinator.close()


def test_cli_cannot_override_spending_derived_quest(tmp_path: Path) -> None:
    coordinator = MoneyMirrorCoordinator(tmp_path / "memory.db", runtime=FakeRuntime())
    try:
        report = coordinator.analyze_csv(ROOT / "data" / "sample_01.csv")
        with pytest.raises(ValueError, match="账单自动计算"):
            coordinator.complete_quest(report, "late_night_guard")
    finally:
        coordinator.close()


def test_main_requires_an_explicit_csv_path() -> None:
    """A bill path is required; no hidden default bill is selected."""
    import main

    command = main.parser()
    args = command.parse_args(["--csv", "bill.csv"])
    assert args.csv.name == "bill.csv"
    assert not hasattr(args, "demo")

