from resume_agent.domain.models import (
    Experience,
    FactValue,
    QualityDimension,
    Specificity,
)
from resume_agent.domain.quality import evaluate_experience


def put(
    experience: Experience,
    dimension: QualityDimension,
    text: str,
    specificity: Specificity = Specificity.PRESENT,
) -> None:
    experience.statements[dimension].append(
        FactValue(text=text, specificity=specificity)
    )


def test_gate_requires_action_even_with_four_other_dimensions():
    experience = Experience(organization="A", role="Analyst")
    for dimension in [
        QualityDimension.CONTEXT,
        QualityDimension.RESPONSIBILITY,
        QualityDimension.METHOD,
        QualityDimension.RESULT,
    ]:
        put(experience, dimension, dimension.value)

    assert evaluate_experience(experience).passes_gate is False


def test_gate_passes_with_four_dimensions_action_and_result():
    experience = Experience(organization="A", role="Analyst")
    for dimension in [
        QualityDimension.CONTEXT,
        QualityDimension.RESPONSIBILITY,
        QualityDimension.ACTION,
        QualityDimension.RESULT,
    ]:
        put(experience, dimension, dimension.value)

    report = evaluate_experience(experience)

    assert report.passes_gate is True
    assert report.scores[QualityDimension.ACTION] == 1


def test_concrete_fact_scores_two():
    experience = Experience(organization="A", role="Analyst")
    put(
        experience,
        QualityDimension.EVIDENCE,
        "Saved four hours weekly",
        Specificity.CONCRETE,
    )

    assert evaluate_experience(experience).scores[QualityDimension.EVIDENCE] == 2
