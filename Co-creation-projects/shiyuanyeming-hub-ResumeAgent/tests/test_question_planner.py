from resume_agent.application.question_planner import (
    PlanningSignals,
    QuestionHistory,
    QuestionPlanner,
)
from resume_agent.domain.models import Experience, FactValue, QualityDimension


def test_planner_selects_highest_value_missing_dimension():
    experience = Experience(organization="A", role="Analyst")
    experience.statements[QualityDimension.ACTION].append(
        FactValue(text="Built a dashboard")
    )
    signals = PlanningSignals(
        target_relevance={QualityDimension.RESULT: 1.0, QualityDimension.METHOD: 0.2},
        differentiating_value={QualityDimension.RESULT: 1.0},
        answerability={QualityDimension.RESULT: 0.8},
    )

    plan = QuestionPlanner().plan(experience, signals, QuestionHistory())

    assert plan is not None
    assert plan.dimension is QualityDimension.RESULT


def test_planner_never_returns_skipped_dimension():
    experience = Experience(organization="A", role="Analyst")
    history = QuestionHistory(skipped={QualityDimension.RESULT})

    plan = QuestionPlanner().plan(experience, PlanningSignals(), history)

    assert plan is not None
    assert plan.dimension is not QualityDimension.RESULT


def test_planner_stops_when_gate_passes_by_default():
    experience = Experience(organization="A", role="Analyst")
    for dimension in [
        QualityDimension.CONTEXT,
        QualityDimension.RESPONSIBILITY,
        QualityDimension.ACTION,
        QualityDimension.RESULT,
    ]:
        experience.statements[dimension].append(FactValue(text=dimension.value))

    assert (
        QuestionPlanner().plan(experience, PlanningSignals(), QuestionHistory())
        is None
    )


def test_repetition_and_fatigue_lower_priority():
    experience = Experience(organization="A", role="Analyst")
    fresh = QuestionPlanner().rank(
        experience, PlanningSignals(), QuestionHistory()
    )
    repeated = QuestionPlanner().rank(
        experience,
        PlanningSignals(),
        QuestionHistory(attempts={QualityDimension.CONTEXT: 1}),
    )

    assert repeated[QualityDimension.CONTEXT] < fresh[QualityDimension.CONTEXT]


def test_targeted_revisit_can_continue_after_gate():
    experience = Experience(organization="A", role="Analyst")
    for dimension in [
        QualityDimension.CONTEXT,
        QualityDimension.RESPONSIBILITY,
        QualityDimension.ACTION,
        QualityDimension.RESULT,
    ]:
        experience.statements[dimension].append(FactValue(text=dimension.value))
    signals = PlanningSignals(
        target_relevance={QualityDimension.EVIDENCE: 1.0},
        differentiating_value={QualityDimension.EVIDENCE: 1.0},
    )

    plan = QuestionPlanner().plan(
        experience,
        signals,
        QuestionHistory(),
        continue_after_gate=True,
    )

    assert plan is not None
    assert plan.dimension is QualityDimension.EVIDENCE
