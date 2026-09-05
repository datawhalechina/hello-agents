"""Deterministic quality gate for resume experience evidence."""

from typing import Dict

from pydantic import BaseModel, ConfigDict

from .models import Experience, QualityDimension, Specificity


class QualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    scores: Dict[QualityDimension, int]
    present_dimensions: int
    total: int
    passes_gate: bool


def evaluate_experience(experience: Experience) -> QualityReport:
    scores: Dict[QualityDimension, int] = {}
    for dimension in QualityDimension:
        values = experience.statements.get(dimension, [])
        if not values:
            scores[dimension] = 0
        elif any(value.specificity is Specificity.CONCRETE for value in values):
            scores[dimension] = 2
        else:
            scores[dimension] = 1

    present_dimensions = sum(score > 0 for score in scores.values())
    passes_gate = (
        present_dimensions >= 4
        and scores[QualityDimension.ACTION] >= 1
        and (
            scores[QualityDimension.RESULT] >= 1
            or scores[QualityDimension.EVIDENCE] >= 1
        )
    )
    return QualityReport(
        scores=scores,
        present_dimensions=present_dimensions,
        total=sum(scores.values()),
        passes_gate=passes_gate,
    )
