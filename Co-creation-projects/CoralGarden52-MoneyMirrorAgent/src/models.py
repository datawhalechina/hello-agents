"""Typed domain models used by deterministic tools and agent orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Literal

TransactionKind = Literal["income", "expense"]


@dataclass(slots=True)
class Transaction:
    transaction_id: str
    occurred_at: str
    merchant: str
    amount: float
    kind: TransactionKind
    category: str = "Uncategorized"
    note: str = ""
    source: str = "csv"
    category_confidence: float = 0.0

    @property
    def date(self) -> date:
        return date.fromisoformat(self.occurred_at[:10])

    @property
    def hour(self) -> int:
        if "T" not in self.occurred_at:
            return 12
        return int(self.occurred_at.split("T", 1)[1][:2])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Anomaly:
    transaction_id: str
    merchant: str
    category: str
    amount: float
    occurred_at: str
    method: str
    score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Goal:
    goal_id: str
    title: str
    goal_type: Literal["savings", "travel", "category_limit"]
    target_amount: float
    current_amount: float
    deadline: str
    category: str | None = None
    monthly_limit: float | None = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Quest:
    quest_id: str
    title: str
    description: str
    quest_type: str
    target: float
    progress: float
    unit: str
    exp_reward: int
    status: Literal["active", "completed"] = "active"
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Achievement:
    key: str
    title: str
    description: str
    unlocked: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisReport:
    user_id: str
    month: str
    transactions: list[Transaction]
    summary: dict[str, Any]
    category_breakdown: dict[str, float]
    trends: dict[str, dict[str, float]]
    patterns: dict[str, Any]
    anomalies: list[Anomaly]
    subscriptions: list[dict[str, Any]]
    persona: dict[str, Any]
    budget: dict[str, Any]
    goals: list[dict[str, Any]]
    quests: list[Quest]
    achievements: list[Achievement]
    gamification: dict[str, Any]
    reflection: dict[str, Any]
    agent_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "month": self.month,
            "transactions": [item.to_dict() for item in self.transactions],
            "summary": self.summary,
            "category_breakdown": self.category_breakdown,
            "trends": self.trends,
            "patterns": self.patterns,
            "anomalies": [item.to_dict() for item in self.anomalies],
            "subscriptions": self.subscriptions,
            "persona": self.persona,
            "budget": self.budget,
            "goals": self.goals,
            "quests": [item.to_dict() for item in self.quests],
            "achievements": [item.to_dict() for item in self.achievements],
            "gamification": self.gamification,
            "reflection": self.reflection,
            "agent_trace": self.agent_trace,
        }
