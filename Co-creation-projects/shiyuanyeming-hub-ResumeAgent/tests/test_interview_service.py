from resume_agent.application.interview_service import InterviewService
from resume_agent.domain.models import (
    CareerFactBase,
    InterviewSession,
    QualityDimension,
)
from tests.fakes import (
    InMemoryFactBaseRepository,
    InMemorySessionRepository,
    StubAuditAgent,
    StubQuestionWriter,
)


def make_interview():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Data Analyst")
    session = InterviewSession(
        fact_base_id=base.id,
        active_experience_id=experience.id,
    )
    bases = InMemoryFactBaseRepository([base])
    sessions = InMemorySessionRepository([session])
    service = InterviewService(
        bases,
        sessions,
        StubAuditAgent(),
        StubQuestionWriter(),
    )
    return service, session, bases, sessions, experience


def test_answer_creates_unconfirmed_proposal_without_mutating_fact_base():
    service, session, bases, sessions, experience = make_interview()

    turn = service.answer(session.id, "I built the weekly dashboard myself")

    assert turn.proposal is not None
    assert turn.proposal.dimension is QualityDimension.ACTION
    assert (
        bases.get(session.fact_base_id)
        .get_experience(experience.id)
        .statements[QualityDimension.ACTION]
        == []
    )
    assert turn.proposal.id in sessions.get(session.id).pending_proposals


def test_confirmation_updates_base_and_returns_one_next_question():
    service, session, bases, sessions, experience = make_interview()
    turn = service.answer(session.id, "I built the weekly dashboard myself")

    result = service.confirm(session.id, turn.proposal.id)

    assert bases.get(session.fact_base_id).revision == 1
    assert len(result.questions) == 1
    assert turn.proposal.id not in sessions.get(session.id).pending_proposals


def test_skip_after_two_unknown_answers_prevents_same_gap():
    service, session, bases, sessions, experience = make_interview()

    first = service.record_unknown(session.id, QualityDimension.RESULT)
    second = service.record_unknown(session.id, QualityDimension.RESULT)

    assert first.skipped is False
    assert second.skipped is True
    assert service.next_question(session.id).dimension is not QualityDimension.RESULT


def test_interview_asks_only_one_question_per_turn():
    service, session, bases, sessions, experience = make_interview()
    turn = service.answer(session.id, "I built the weekly dashboard myself")

    result = service.confirm(session.id, turn.proposal.id)

    assert result.questions == [result.question.text]


def test_confirmation_rejects_unknown_proposal():
    service, session, bases, sessions, experience = make_interview()

    try:
        service.confirm(session.id, experience.id)
    except KeyError as error:
        assert "proposal not pending" in str(error)
    else:
        raise AssertionError("unknown proposal must be rejected")
