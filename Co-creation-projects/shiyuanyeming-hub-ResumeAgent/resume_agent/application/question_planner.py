"""Choose the next highest-value evidence gap deterministically."""

from typing import Dict, Optional, Set

from pydantic import BaseModel, Field

from resume_agent.domain.models import Experience, QualityDimension
from resume_agent.domain.quality import evaluate_experience


class PlanningSignals(BaseModel):
    target_relevance: Dict[QualityDimension, float] = Field(default_factory=dict)
    differentiating_value: Dict[QualityDimension, float] = Field(default_factory=dict)
    answerability: Dict[QualityDimension, float] = Field(default_factory=dict)


class QuestionHistory(BaseModel):
    attempts: Dict[QualityDimension, int] = Field(default_factory=dict)
    skipped: Set[QualityDimension] = Field(default_factory=set)

    @property
    def total_attempts(self) -> int:
        return sum(self.attempts.values())


class QuestionPlan(BaseModel):
    dimension: QualityDimension
    priority: float
    attempt: int
    escalation: str


class QuestionPlanner:
    """Rank gaps using relevance, distinctiveness, answerability, and fatigue."""

    def rank(
        self,
        experience: Experience,
        signals: PlanningSignals,
        history: QuestionHistory,
    ) -> Dict[QualityDimension, float]:
        report = evaluate_experience(experience)
        fatigue_penalty = min(0.3, 0.03 * history.total_attempts)
        ranked: Dict[QualityDimension, float] = {}

        for dimension in QualityDimension:
            if dimension in history.skipped:
                continue
            attempts = history.attempts.get(dimension, 0)
            missing_information = (2 - report.scores[dimension]) / 2
            target_relevance = signals.target_relevance.get(dimension, 0.5)
            differentiating_value = signals.differentiating_value.get(
                dimension, 0.5
            )
            answerability = signals.answerability.get(dimension, 0.5)
            freshness = 1.0 if attempts == 0 else 0.5
            repetition_penalty = 0.25 * attempts
            priority = (
                0.30 * missing_information
                + 0.25 * target_relevance
                + 0.20 * differentiating_value
                + 0.15 * answerability
                + 0.10 * freshness
                - repetition_penalty
                - fatigue_penalty
            )
            ranked[dimension] = round(priority, 6)

        return ranked

    def plan(
        self,
        experience: Experience,
        signals: PlanningSignals,
        history: QuestionHistory,
        *,
        continue_after_gate: bool = False,
    ) -> Optional[QuestionPlan]:
        report = evaluate_experience(experience)
        if report.passes_gate and not continue_after_gate:
            return None

        ranked = self.rank(experience, signals, history)
        if not ranked:
            return None

        dimension = max(ranked, key=ranked.get)
        attempt = history.attempts.get(dimension, 0)
        escalation = "direct" if attempt == 0 else "recall_anchors"
        if attempt >= 2:
            escalation = "alternative_evidence"
        return QuestionPlan(
            dimension=dimension,
            priority=ranked[dimension],
            attempt=attempt,
            escalation=escalation,
        )
