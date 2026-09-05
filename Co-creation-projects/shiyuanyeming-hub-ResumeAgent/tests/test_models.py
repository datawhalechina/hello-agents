import pytest
from pydantic import ValidationError

from resume_agent.domain.models import (
    CareerFactBase,
    ConfidenceStatus,
    FactProposal,
    FactValue,
    QualityDimension,
    Specificity,
)


def test_sensitive_confirmed_fact_keeps_both_attributes():
    fact = FactValue(
        text="Managed a six-person team",
        confidence=ConfidenceStatus.CONFIRMED,
        specificity=Specificity.CONCRETE,
        sensitive=True,
    )

    assert fact.confidence is ConfidenceStatus.CONFIRMED
    assert fact.sensitive is True


def test_empty_fact_text_is_rejected():
    with pytest.raises(ValidationError):
        FactValue(text="   ")


def test_confirming_proposal_updates_experience_and_revision():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Data Analyst")
    proposal = FactProposal(
        fact_base_revision=0,
        experience_id=experience.id,
        dimension=QualityDimension.ACTION,
        values=[FactValue(text="Built an automated dashboard")],
    )

    base.confirm(proposal)

    assert base.revision == 1
    assert (
        base.get_experience(experience.id)
        .statements[QualityDimension.ACTION][0]
        .text
        == "Built an automated dashboard"
    )


def test_stale_proposal_is_rejected():
    base = CareerFactBase(revision=2)
    experience = base.add_experience("Yunshu", "Data Analyst")
    proposal = FactProposal(
        fact_base_revision=1,
        experience_id=experience.id,
        dimension=QualityDimension.ACTION,
        values=[FactValue(text="Built an automated dashboard")],
    )

    with pytest.raises(ValueError, match="revision conflict"):
        base.confirm(proposal)
