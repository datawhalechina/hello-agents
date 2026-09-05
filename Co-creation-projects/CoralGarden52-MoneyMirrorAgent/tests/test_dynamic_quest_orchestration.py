"""Tests for signal → LLM JSON → Python-validated Quest orchestration."""

from __future__ import annotations

from pathlib import Path

from src.agents.quest_agent import QuestAgent
from src.memory import SQLiteMemory
from src.models import Transaction

from .fakes import FakeRuntime


def test_weekend_signal_can_produce_a_different_llm_orchestrated_quest(tmp_path: Path) -> None:
    memory = SQLiteMemory(tmp_path / "memory.db")
    agent = QuestAgent(memory, FakeRuntime())
    transactions = [
        Transaction("a", "2026-07-04T12:00", "周末餐馆", 100, "expense", "餐饮"),
        Transaction("b", "2026-07-05T15:00", "周末展览", 100, "expense", "餐饮"),
        Transaction("c", "2026-07-11T19:00", "周末聚餐", 100, "expense", "餐饮"),
    ]
    try:
        quests, _, _, trace = agent.run(
            transactions,
            "2026-07",
            {"expense": 300, "balance": 0, "savings_rate": 0},
            {"餐饮": 300},
            {
                "late_night": {"count": 0, "amount": 0, "share": 0},
                "frequent_small": {"count": 0, "amount": 0},
                "weekend": {"count": 3, "amount": 300, "share": 100},
                "payday_window": {"count": 0, "amount": 0, "share": 0},
            },
            [],
            {"categories": {"餐饮": {"recommended": 290}}},
            [],
        )
        assert [quest.quest_id for quest in quests] == ["weekend_wallet_shield"]
        quest = quests[0]
        # The LLM supplied the non-numeric title/copy, while Python supplied
        # the target (300 * 0.85) and current progress evidence.
        assert quest.title == "周末钱包护盾"
        assert quest.target == 255
        assert quest.quest_type == "weekend_spend_limit"
        assert "已核验目标" in quest.description
        assert trace["llm_orchestration"]["accepted_signal_ids"] == ["weekend"]
        assert trace["llm_orchestration"]["numeric_authority"].startswith("Python only")
    finally:
        memory.close()


def test_quest_candidate_with_model_invented_number_is_rejected(tmp_path: Path) -> None:
    memory = SQLiteMemory(tmp_path / "memory.db")
    agent = QuestAgent(memory, FakeRuntime())
    try:
        blueprint = agent._discover_signals(
            {"expense": 100, "balance": 0},
            {},
            {
                "late_night": {"count": 2, "amount": 80, "share": 80},
                "frequent_small": {"count": 0, "amount": 0},
                "weekend": {"count": 0, "amount": 0, "share": 0},
                "payday_window": {"count": 0, "amount": 0, "share": 0},
            },
            [],
            {"categories": {}},
            [],
        )
        raw = '{"quests":[{"signal_id":"late_night","title":"夜航2号结界","narrative":"连续2天不点外卖，冲刺奖励。","action_hint":"先忍十分钟再决定是否下单。"}]}'
        candidates, problems = agent._parse_and_validate_candidates(raw, blueprint)
        assert candidates == []
        assert any("金额、百分比或阿拉伯数字" in item for item in problems)
    finally:
        memory.close()
