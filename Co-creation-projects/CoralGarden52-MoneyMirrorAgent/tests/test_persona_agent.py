"""Persona scoring must remain evidence-based and configurable."""

from __future__ import annotations

import json

import pytest

from src.agents.persona_agent import PersonaAgent

from .fakes import FakeRuntime


def _patterns(**overrides) -> dict:
    base = {
        "late_night": {"share": 0.0, "count": 0, "amount": 0.0},
        "weekend": {"share": 0.0, "count": 0, "amount": 0.0},
        "payday_window": {"share": 0.0, "count": 0, "amount": 0.0},
        "frequent_small": {"count": 0, "amount": 0.0, "average": 0.0},
    }
    base.update(overrides)
    return base


def test_persona_uses_scoring_and_evidence_validation() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, trace = agent.run(
        {"expense": 1000.0, "savings_rate": 8.0},
        {"餐饮": 350.0, "娱乐": 180.0, "购物": 120.0, "订阅": 0.0, "学习": 0.0},
        _patterns(
            late_night={"share": 28.0, "count": 5, "amount": 280.0},
            frequent_small={"count": 7, "amount": 210.0, "average": 30.0},
        ),
        [],
    )

    assert persona["archetype"] == "late_night_focus"
    assert persona["primary"] == "夜行消费探索者"
    assert persona["score"] >= 52
    assert persona["confidence"] == round(persona["score"] / 100, 2)
    assert any("深夜消费占比" in item for item in persona["evidence"])
    assert trace["llm_role"].startswith("仅生成")
    assert trace["candidates"][0]["archetype"] == "late_night_focus"


def test_generic_food_and_small_spending_never_claims_coffee_persona() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, _ = agent.run(
        {"expense": 1000.0, "savings_rate": 5.0},
        {"餐饮": 400.0, "娱乐": 0.0, "购物": 0.0},
        _patterns(frequent_small={"count": 9, "amount": 280.0, "average": 31.0}),
        [],
    )

    assert persona["archetype"] == "frequent_small_spend"
    assert persona["primary"] == "高频小额行动派"
    assert all("咖啡" not in label for label in persona["labels"])


def test_learning_persona_requires_history_not_a_single_large_month() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, trace = agent.run(
        {"expense": 1000.0, "savings_rate": 5.0},
        {"学习": 300.0},
        _patterns(),
        [],
    )

    learning = next(item for item in trace["candidates"] if item["archetype"] == "learning_investor")
    assert learning["evidence_valid"] is False
    assert persona["archetype"] != "learning_investor"

def test_persona_config_rejects_unknown_feature_reference(tmp_path) -> None:
    config_path = tmp_path / "personas.json"
    config_path.write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "id": "typo_guard",
                        "name": "配置校验测试",
                        "minimum_score": 50,
                        "required_features": {"nightt": 40},
                        "weights": {"nightt": 1.0},
                        "evidence_metrics": ["late_night_share"],
                    }
                ],
                "fallback": {"id": "balanced", "name": "均衡", "evidence_metrics": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="未知特征: nightt"):
        PersonaAgent(FakeRuntime(), config_path=config_path)



def test_richer_persona_catalog_exposes_distinct_data_driven_archetypes() -> None:
    agent = PersonaAgent(FakeRuntime())
    configured_ids = {item.archetype_id for item in agent.archetypes}

    assert len(configured_ids) >= 12
    assert {
        "payday_rhythm",
        "weekend_social",
        "food_routine",
        "savings_sprinter",
        "digital_lifestyle",
        "learning_consistent",
        "flexible_adventurer",
        "mindful_minimalist",
    } <= configured_ids


def test_payday_persona_is_selected_from_payday_evidence() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, trace = agent.run(
        {"expense": 1000.0, "savings_rate": 18.0},
        {"餐饮": 200.0, "娱乐": 80.0},
        _patterns(
            payday_window={"share": 68.0, "count": 6, "amount": 680.0},
            frequent_small={"count": 7, "amount": 210.0, "average": 30.0},
        ),
        [],
    )

    assert persona["archetype"] == "payday_rhythm"
    assert any(item["archetype"] == "payday_rhythm" and item["evidence_valid"] for item in trace["candidates"])
    assert "工资到账后消费占比" in "；".join(persona["evidence"])


def test_food_routine_persona_requires_repeated_small_food_behavior() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, _ = agent.run(
        {"expense": 1000.0, "savings_rate": 5.0},
        {"餐饮": 700.0, "娱乐": 0.0, "购物": 0.0},
        _patterns(frequent_small={"count": 6, "amount": 50.0, "average": 8.33}),
        [],
    )

    assert persona["archetype"] == "food_routine"
    assert persona["primary"] == "日常餐饮探索家"


def test_savings_feature_keeps_the_verified_savings_rate_shape() -> None:
    agent = PersonaAgent(FakeRuntime())
    persona, _ = agent.run(
        {"expense": 1000.0, "savings_rate": 47.5},
        {"餐饮": 300.0},
        _patterns(),
        [],
    )

    assert persona["feature_vector"]["savings"] == 47.5
