from uuid import uuid4

import pytest

from resume_agent.agents.mentor import (
    DeterministicQuestionWriter,
    StructuredFactAuditAgent,
    StructuredQuestionWriterAgent,
)
from resume_agent.agents.structured import AgentOutputError
from resume_agent.application.question_planner import QuestionPlan
from resume_agent.domain.models import (
    CareerFactBase,
    ConfidenceStatus,
    InterviewSession,
    QualityDimension,
    Specificity,
)


class FakeRunner:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def make_state():
    base = CareerFactBase(revision=3)
    experience = base.add_experience("Yunshu", "Data Analyst")
    session = InterviewSession(
        fact_base_id=base.id,
        active_experience_id=experience.id,
    )
    return base, experience, session


def test_fact_audit_uses_authoritative_target_and_revision():
    base, experience, session = make_state()
    runner = FakeRunner(
        """{
          "experience_id": "00000000-0000-0000-0000-000000000000",
          "fact_base_revision": 999,
          "dimension": "action",
          "values": [{"text": "Built the weekly dashboard"}],
          "rationale": "The user described a personal action"
        }"""
    )

    proposal = StructuredFactAuditAgent(runner).propose(
        "I built the weekly dashboard",
        session,
        base,
    )

    assert proposal.experience_id == experience.id
    assert proposal.fact_base_revision == 3
    assert proposal.dimension is QualityDimension.ACTION


def test_estimate_and_sensitive_flag_remain_independent():
    base, experience, session = make_state()
    runner = FakeRunner(
        """{
          "dimension": "evidence",
          "values": [{
            "text": "Approximately 500 users",
            "confidence": "estimated",
            "specificity": "concrete",
            "sensitive": true
          }]
        }"""
    )

    proposal = StructuredFactAuditAgent(runner).propose(
        "Roughly 500 users, but this is confidential",
        session,
        base,
    )

    value = proposal.values[0]
    assert value.confidence is ConfidenceStatus.ESTIMATED
    assert value.specificity is Specificity.CONCRETE
    assert value.sensitive is True


def test_audit_rejects_model_claim_that_fact_is_already_confirmed():
    base, experience, session = make_state()
    response = """{
      "dimension": "result",
      "values": [{"text": "Revenue increased", "confidence": "confirmed"}]
    }"""
    runner = FakeRunner(response, response)

    with pytest.raises(AgentOutputError):
        StructuredFactAuditAgent(runner).propose("Revenue increased", session, base)


@pytest.mark.parametrize(
    ("escalation", "expected"),
    [
        ("direct", "结果"),
        ("recall_anchors", "例如"),
        ("alternative_evidence", "没有数字"),
    ],
)
def test_deterministic_writer_supports_three_escalation_levels(
    escalation,
    expected,
):
    base, experience, session = make_state()
    plan = QuestionPlan(
        dimension=QualityDimension.RESULT,
        priority=0.9,
        attempt=0,
        escalation=escalation,
    )

    question = DeterministicQuestionWriter().write(plan, experience, base.target)

    assert expected in question
    assert question.count("？") == 1


@pytest.mark.parametrize("escalation", ["recall_anchors", "alternative_evidence"])
def test_deterministic_follow_ups_are_dimension_specific(escalation):
    base, experience, session = make_state()
    writer = DeterministicQuestionWriter()

    questions = [
        writer.write(
            QuestionPlan(
                dimension=dimension,
                priority=0.9,
                attempt=1,
                escalation=escalation,
            ),
            experience,
            base.target,
        )
        for dimension in QualityDimension
    ]

    assert len(set(questions)) == len(QualityDimension)
    assert all(question.count("?") + question.count("？") == 1 for question in questions)


def test_structured_writer_returns_exactly_one_question():
    base, experience, session = make_state()
    runner = FakeRunner('{"question": "这项工作最终带来了什么变化？"}')
    plan = QuestionPlan(
        dimension=QualityDimension.RESULT,
        priority=0.9,
        attempt=0,
        escalation="direct",
    )

    question = StructuredQuestionWriterAgent(runner).write(
        plan,
        experience,
        base.target,
    )

    assert question == "这项工作最终带来了什么变化？"


def test_structured_writer_rejects_multiple_questions():
    base, experience, session = make_state()
    response = '{"question": "你做了什么？结果是什么？"}'
    runner = FakeRunner(response, response)
    plan = QuestionPlan(
        dimension=QualityDimension.ACTION,
        priority=0.9,
        attempt=0,
        escalation="direct",
    )

    with pytest.raises(AgentOutputError):
        StructuredQuestionWriterAgent(runner).write(plan, experience, base.target)
