"""Evidence-based, configurable consumer-persona scoring for MoneyMirror."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Transaction
from ..tools.statistics import StatisticsTool
from .runtime import HelloAgentsRuntime


@dataclass(frozen=True, slots=True)
class PersonaArchetype:
    """A stable, configurable persona structure; wording is not a Python rule."""

    archetype_id: str
    name: str
    minimum_score: float
    required_features: dict[str, float]
    weights: dict[str, float]
    evidence_metrics: tuple[str, ...]


class PersonaAgent:
    """Score verified behavior features, validate evidence, then ask the LLM for prose.

    Python determines the reproducible archetype and its score. The LLM only
    turns the verified result into young, supportive language; it cannot
    change the score, invent a metric, or turn generic food spending into a
    coffee-specific claim.
    """

    paradigm = "Feature vector → configurable scoring → evidence validation → LLM narrative"
    DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "personas.json"

    # These names are the stable contract between deterministic extraction and
    # external persona configuration. They are deliberately behavior metrics,
    # not persona labels: adding or renaming an archetype remains a JSON-only
    # change, while a misspelled feature is rejected instead of silently
    # scoring as zero.
    FEATURE_KEYS = frozenset(
        {
            "night",
            "weekend",
            "frequent_small",
            "flexible_spend",
            "food",
            "subscription",
            "learning",
            "learning_consistency",
            "savings",
            "planning",
            "planning_inverse",
            "impulse",
            "payday",
            "impulse_inverse",
        }
    )
    METRIC_KEYS = frozenset(
        {
            "savings_rate",
            "late_night_share",
            "late_night_count",
            "weekend_share",
            "weekend_count",
            "payday_share",
            "frequent_small_count",
            "frequent_small_share",
            "food_share",
            "flexible_spend_share",
            "subscription_share",
            "subscription_count",
            "learning_share",
            "learning_active_months",
            "impulse",
        }
    )

    def __init__(self, runtime: HelloAgentsRuntime, config_path: str | Path | None = None) -> None:
        self.runtime = runtime
        self.statistics = StatisticsTool()
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.archetypes, self.fallback = self._load_config(self.config_path)
        self._validate_config_references()

    @staticmethod
    def _clamp_score(value: float) -> float:
        return round(max(0.0, min(100.0, value)), 2)

    @classmethod
    def _scaled(cls, value: float, full_score_at: float) -> float:
        if full_score_at <= 0:
            return 0.0
        return cls._clamp_score(value / full_score_at * 100)

    @staticmethod
    def _load_config(path: Path) -> tuple[tuple[PersonaArchetype, ...], dict[str, Any]]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取人格配置 {path}: {exc}") from exc
        items = raw.get("archetypes")
        fallback = raw.get("fallback")
        if not isinstance(items, list) or not items or not isinstance(fallback, dict):
            raise ValueError("人格配置必须包含非空 archetypes 和 fallback")

        archetypes: list[PersonaArchetype] = []
        seen_ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("人格配置中的 archetype 必须是对象")
            archetype_id = str(item.get("id", "")).strip()
            name = str(item.get("name", "")).strip()
            weights = item.get("weights")
            required = item.get("required_features", {})
            evidence = item.get("evidence_metrics", [])
            if not archetype_id or not name or archetype_id in seen_ids:
                raise ValueError("人格配置需要唯一且非空的 id 与 name")
            if not isinstance(weights, dict) or not weights or not isinstance(required, dict) or not isinstance(evidence, list):
                raise ValueError(f"人格配置 {archetype_id} 的字段格式无效")
            numeric_weights = {str(key): float(value) for key, value in weights.items()}
            if any(value < 0 for value in numeric_weights.values()) or sum(numeric_weights.values()) <= 0:
                raise ValueError(f"人格配置 {archetype_id} 的 weights 必须为正权重")
            archetypes.append(
                PersonaArchetype(
                    archetype_id=archetype_id,
                    name=name,
                    minimum_score=float(item.get("minimum_score", 0)),
                    required_features={str(key): float(value) for key, value in required.items()},
                    weights=numeric_weights,
                    evidence_metrics=tuple(str(key) for key in evidence),
                )
            )
            seen_ids.add(archetype_id)
        if not str(fallback.get("id", "")).strip() or not str(fallback.get("name", "")).strip():
            raise ValueError("人格配置 fallback 需要 id 与 name")
        return tuple(archetypes), fallback

    def _validate_config_references(self) -> None:
        """Fail fast when JSON references a metric the extractor cannot produce."""
        for archetype in self.archetypes:
            feature_keys = set(archetype.weights) | set(archetype.required_features)
            unknown_features = sorted(feature_keys - self.FEATURE_KEYS)
            if unknown_features:
                raise ValueError(
                    f"人格配置 {archetype.archetype_id} 引用了未知特征: {', '.join(unknown_features)}"
                )
            unknown_metrics = sorted(set(archetype.evidence_metrics) - self.METRIC_KEYS)
            if unknown_metrics:
                raise ValueError(
                    f"人格配置 {archetype.archetype_id} 引用了未知证据指标: {', '.join(unknown_metrics)}"
                )
            if not 0 <= archetype.minimum_score <= 100:
                raise ValueError(f"人格配置 {archetype.archetype_id} 的 minimum_score 必须在 0 到 100 之间")
            invalid_thresholds = [
                name for name, threshold in archetype.required_features.items() if not 0 <= threshold <= 100
            ]
            if invalid_thresholds:
                raise ValueError(
                    f"人格配置 {archetype.archetype_id} 的 required_features 阈值必须在 0 到 100 之间: "
                    f"{', '.join(sorted(invalid_thresholds))}"
                )
        fallback_unknown_metrics = sorted(set(self.fallback.get("evidence_metrics", [])) - self.METRIC_KEYS)
        if fallback_unknown_metrics:
            raise ValueError(f"人格配置 fallback 引用了未知证据指标: {', '.join(fallback_unknown_metrics)}")

    def _learning_active_months(self, transactions: Iterable[Transaction] | None) -> int:
        if transactions is None:
            return 0
        totals = self.statistics.monthly_category_totals(transactions)
        return sum(1 for categories in totals.values() if categories.get("学习", 0.0) > 0)

    def _extract_features(
        self,
        summary: dict[str, Any],
        categories: dict[str, float],
        patterns: dict[str, Any],
        subscriptions: list[dict[str, Any]],
        transactions: Iterable[Transaction] | None,
    ) -> tuple[dict[str, float], dict[str, float | int]]:
        expense = max(float(summary.get("expense", 0.0)), 1.0)
        savings_rate = float(summary.get("savings_rate", 0.0))
        late = patterns.get("late_night", {})
        weekend = patterns.get("weekend", {})
        payday = patterns.get("payday_window", {})
        frequent_small = patterns.get("frequent_small", {})

        late_share = float(late.get("share", 0.0))
        weekend_share = float(weekend.get("share", 0.0))
        payday_share = float(payday.get("share", 0.0))
        small_count = int(frequent_small.get("count", 0))
        small_share = float(frequent_small.get("amount", 0.0)) / expense * 100
        food_share = float(categories.get("餐饮", 0.0)) / expense * 100
        flexible_spend_share = (float(categories.get("娱乐", 0.0)) + float(categories.get("购物", 0.0))) / expense * 100
        subscription_share = float(categories.get("订阅", 0.0)) / expense * 100
        learning_share = float(categories.get("学习", 0.0)) / expense * 100
        learning_active_months = self._learning_active_months(transactions)

        night = 0.72 * self._scaled(late_share, 25) + 0.28 * self._scaled(int(late.get("count", 0)), 5)
        weekend_score = 0.72 * self._scaled(weekend_share, 50) + 0.28 * self._scaled(int(weekend.get("count", 0)), 6)
        frequent_small_score = 0.7 * self._scaled(small_count, 10) + 0.3 * self._scaled(small_share, 25)
        payday_score = self._scaled(payday_share, 45)
        impulse = 0.45 * frequent_small_score + 0.3 * payday_score + 0.25 * self._scaled(late_share, 30)
        learning = 0.75 * self._scaled(learning_share, 15) + 0.25 * self._scaled(learning_active_months, 4)
        subscription = 0.65 * self._scaled(subscription_share, 12) + 0.35 * self._scaled(len(subscriptions), 3)
        savings = self._clamp_score(savings_rate)
        planning = 0.5 * savings + 0.25 * (100 - self._scaled(payday_share, 45)) + 0.15 * (100 - frequent_small_score) + 0.1 * (100 - self._scaled(late_share, 30))

        feature_vector = {
            "night": self._clamp_score(night),
            "weekend": self._clamp_score(weekend_score),
            "frequent_small": self._clamp_score(frequent_small_score),
            "flexible_spend": self._scaled(flexible_spend_share, 40),
            "food": self._scaled(food_share, 40),
            "subscription": self._clamp_score(subscription),
            "learning": self._clamp_score(learning),
            "learning_consistency": self._scaled(learning_active_months, 4),
            "savings": self._clamp_score(savings),
            "planning": self._clamp_score(planning),
            "planning_inverse": self._clamp_score(100 - planning),
            "impulse": self._clamp_score(impulse),
            "payday": self._clamp_score(payday_score),
            "impulse_inverse": self._clamp_score(100 - impulse),
        }
        metrics: dict[str, float | int] = {
            "savings_rate": round(savings_rate, 2),
            "late_night_share": round(late_share, 2),
            "late_night_count": int(late.get("count", 0)),
            "weekend_share": round(weekend_share, 2),
            "weekend_count": int(weekend.get("count", 0)),
            "payday_share": round(payday_share, 2),
            "frequent_small_count": small_count,
            "frequent_small_share": round(small_share, 2),
            "food_share": round(food_share, 2),
            "flexible_spend_share": round(flexible_spend_share, 2),
            "subscription_share": round(subscription_share, 2),
            "subscription_count": len(subscriptions),
            "learning_share": round(learning_share, 2),
            "learning_active_months": learning_active_months,
            "impulse": round(feature_vector["impulse"], 2),
        }
        return feature_vector, metrics

    @staticmethod
    def _score(archetype: PersonaArchetype, features: dict[str, float]) -> float:
        total_weight = sum(archetype.weights.values())
        return round(
            sum(features.get(feature, 0.0) * weight for feature, weight in archetype.weights.items()) / total_weight,
            2,
        )

    @staticmethod
    def _has_valid_evidence(archetype: PersonaArchetype, features: dict[str, float], score: float) -> bool:
        return score >= archetype.minimum_score and all(
            features.get(feature, 0.0) >= threshold for feature, threshold in archetype.required_features.items()
        )

    @staticmethod
    def _format_metric(metric: str, value: float | int) -> str:
        labels = {
            "savings_rate": "储蓄率",
            "late_night_share": "深夜消费占比",
            "late_night_count": "深夜交易笔数",
            "weekend_share": "周末消费占比",
            "weekend_count": "周末交易笔数",
            "payday_share": "工资到账后消费占比",
            "frequent_small_count": "高频小额交易笔数",
            "frequent_small_share": "高频小额消费占比",
            "food_share": "餐饮消费占比",
            "flexible_spend_share": "娱乐与购物占比",
            "subscription_share": "订阅消费占比",
            "subscription_count": "疑似订阅项数",
            "learning_share": "学习消费占比",
            "learning_active_months": "有学习消费的月份数",
            "impulse": "冲动消费特征分",
        }
        suffix = "" if metric.endswith("count") or metric.endswith("months") else "%"
        rendered = str(value) if suffix == "" else f"{float(value):.1f}{suffix}"
        return f"{labels.get(metric, metric)} {rendered}"

    def _evidence_for(self, metric_keys: Iterable[str], metrics: dict[str, float | int]) -> list[str]:
        return [self._format_metric(key, metrics[key]) for key in metric_keys if key in metrics]

    def run(
        self,
        summary: dict,
        categories: dict[str, float],
        patterns: dict,
        subscriptions: list[dict],
        transactions: Iterable[Transaction] | None = None,
    ) -> tuple[dict, dict]:
        feature_vector, metrics = self._extract_features(summary, categories, patterns, subscriptions, transactions)
        scored = [
            {
                "archetype": archetype,
                "score": self._score(archetype, feature_vector),
            }
            for archetype in self.archetypes
        ]
        valid = [item for item in scored if self._has_valid_evidence(item["archetype"], feature_vector, item["score"])]
        valid.sort(key=lambda item: (-item["score"], item["archetype"].archetype_id))

        if valid:
            primary_item = valid[0]
            primary = primary_item["archetype"]
            primary_score = primary_item["score"]
            secondary_items = valid[1:3]
        else:
            primary = PersonaArchetype(
                archetype_id=str(self.fallback["id"]),
                name=str(self.fallback["name"]),
                minimum_score=0.0,
                required_features={},
                weights={},
                evidence_metrics=tuple(str(item) for item in self.fallback.get("evidence_metrics", [])),
            )
            primary_score = 0.0
            secondary_items = []

        evidence = self._evidence_for(primary.evidence_metrics, metrics)
        if not evidence:
            evidence = ["当前账单的高风险消费信号不集中，消费结构保持相对均衡"]
        secondary = [
            {
                "archetype": item["archetype"].archetype_id,
                "name": item["archetype"].name,
                "score": item["score"],
                "confidence": round(item["score"] / 100, 2),
                "evidence": self._evidence_for(item["archetype"].evidence_metrics, metrics),
            }
            for item in secondary_items
        ]
        narrative = self.runtime.explain(
            "基于经过程序验证的人格原型写两句年轻化、温和的消费说明。"
            f"稳定原型={primary.archetype_id}；展示名={primary.name}；匹配分={primary_score:.1f}；"
            f"证据={'；'.join(evidence)}。不要改写原型归属、不要编造金额或比例、不要将餐饮泛化成咖啡，"
            "可以给一个不含数字的趣味别称，但必须围绕稳定原型表达。",
            mode="simple",
            evidence=[
                "人格特征向量=" + json.dumps(feature_vector, ensure_ascii=False),
                "已验证人格证据=" + "；".join(evidence),
            ],
        )
        candidates = [
            {
                "archetype": item["archetype"].archetype_id,
                "name": item["archetype"].name,
                "score": item["score"],
                "evidence_valid": self._has_valid_evidence(item["archetype"], feature_vector, item["score"]),
            }
            for item in sorted(scored, key=lambda item: (-item["score"], item["archetype"].archetype_id))
        ]
        persona = {
            "primary": primary.name,
            "archetype": primary.archetype_id,
            "score": primary_score,
            "confidence": round(primary_score / 100, 2),
            "labels": [primary.name, *(item["name"] for item in secondary)],
            "secondary": secondary,
            "evidence": evidence,
            "feature_vector": feature_vector,
            "narrative": narrative,
        }
        trace = {
            "agent": "PersonaAgent",
            "paradigm": self.paradigm,
            "config_path": str(self.config_path),
            "grounded_metrics": metrics,
            "feature_vector": feature_vector,
            "candidates": candidates,
            "llm_role": "仅生成年轻化解释，不决定人格原型、分数或证据",
        }
        return persona, trace
