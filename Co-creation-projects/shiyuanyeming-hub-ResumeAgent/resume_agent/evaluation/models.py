"""Validated contracts for the mentor evaluation dataset and scores."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, computed_field

from resume_agent.domain.models import (
    CareerTarget,
    ConfidenceStatus,
    Experience,
    QualityDimension,
    Specificity,
)


class QuestionEvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["question"]
    target: CareerTarget
    experience: Experience
    dimension: QualityDimension
    escalation: Literal["direct", "recall_anchors", "alternative_evidence"]
    must_include_any: list[str] = Field(min_length=1)
    must_not_include: list[str] = Field(default_factory=list)
    expected_question_marks: int = Field(default=1, ge=1)


class AuditEvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["audit"]
    target: CareerTarget
    experience: Experience
    message: str = Field(min_length=1)
    expected_dimension: QualityDimension
    required_fact_fragments: list[str] = Field(min_length=1)
    forbidden_fact_fragments: list[str] = Field(default_factory=list)
    expected_confidence: Optional[ConfidenceStatus] = None
    expected_specificity: Optional[Specificity] = None
    expected_sensitive: Optional[bool] = None


EvaluationCase = Annotated[
    Union[QuestionEvaluationCase, AuditEvaluationCase],
    Field(discriminator="kind"),
]


class MentorDataset(BaseModel):
    version: str
    cases: list[EvaluationCase]

    @computed_field
    @property
    def case_ids(self) -> list[str]:
        return [case.id for case in self.cases]

    @property
    def question_cases(self) -> list[QuestionEvaluationCase]:
        return [case for case in self.cases if isinstance(case, QuestionEvaluationCase)]

    @property
    def audit_cases(self) -> list[AuditEvaluationCase]:
        return [case for case in self.cases if isinstance(case, AuditEvaluationCase)]


class CaseScore(BaseModel):
    case_id: str
    kind: Literal["question", "audit"]
    checks: dict[str, bool]
    error_category: Optional[str] = None

    @computed_field
    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())


class BenchmarkReport(BaseModel):
    dataset_version: str
    repeats: int = Field(ge=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)
    scores: list[CaseScore]
    metrics: dict[str, float]

    @computed_field
    @property
    def total_runs(self) -> int:
        return len(self.scores)

    @computed_field
    @property
    def strict_pass_rate(self) -> float:
        return self.metrics.get("strict_pass_rate", 0.0)

    @property
    def failed_scores(self) -> list[CaseScore]:
        return [score for score in self.scores if not score.passed]
