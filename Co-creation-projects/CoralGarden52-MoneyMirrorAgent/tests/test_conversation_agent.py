"""Tests for the compact, data-grounded LLM conversation payload."""

from __future__ import annotations

import json
from pathlib import Path

from src.agents.conversation_agent import ConversationAgent
from src.agents.coordinator import MoneyMirrorCoordinator

from .fakes import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_conversation_payload_keeps_verified_facts_without_raw_audit_data() -> None:
    coordinator = MoneyMirrorCoordinator(":memory:", runtime=FakeRuntime())
    try:
        report = coordinator.analyze_csv(ROOT / "data" / "sample_01.csv")
        payload = ConversationAgent.payload(
            report,
            [
                {"role": "assistant", "content": "开场"},
                {"role": "user", "content": "我想控制深夜外卖"},
                {"role": "assistant", "content": "请从一个小任务开始"},
            ],
        )
        parsed = json.loads(payload)
        facts = parsed["[Verified tool output]"]
        assert facts["summary"]["expense"] == 6574
        assert facts["patterns"]["late_night"]["count"] >= 3
        assert facts["persona"]["primary"]
        assert facts["quests"]
        assert facts["guided_conversation"][-1]["content"] == "请从一个小任务开始"
        # Raw accounting/audit detail remains in the persisted JSON only, not
        # in every LLM turn where it can crowd out the facts above.
        assert "transactions" not in facts
        assert "agent_trace" not in facts
    finally:
        coordinator.close()


def test_compact_conversation_bounds_history_and_message_length() -> None:
    history = [
        {"role": "user", "content": f"turn-{index}"}
        for index in range(8)
    ]
    history[-1]["content"] = "x" * 700
    compact = ConversationAgent.compact_conversation(history)
    assert len(compact) == ConversationAgent.MAX_HISTORY_ITEMS
    assert compact[0]["content"] == "turn-2"
    assert compact[-1]["content"].endswith("…")
    assert len(compact[-1]["content"]) == ConversationAgent.MAX_MESSAGE_CHARS + 1
