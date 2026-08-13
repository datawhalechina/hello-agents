"""Stateful interview orchestration across specialized agent ports."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from resume_agent.application.ports import (
    FactAuditAgent,
    FactBaseRepository,
    QuestionWriterAgent,
    SessionRepository,
)
from resume_agent.application.question_planner import (
    PlanningSignals,
    QuestionHistory,
    QuestionPlan,
    QuestionPlanner,
)
from resume_agent.domain.models import (
    CareerFactBase,
    FactProposal,
    InterviewQuestion,
    InterviewMessage,
    InterviewSession,
    QualityDimension,
    utc_now,
)


MentorQuestion = InterviewQuestion


class InterviewTurn(BaseModel):
    proposal: Optional[FactProposal] = None
    question: Optional[MentorQuestion] = None
    questions: List[str] = Field(default_factory=list, max_length=1)


class UnknownOutcome(BaseModel):
    dimension: QualityDimension
    attempts: int
    skipped: bool


class InterviewService:
    def __init__(
        self,
        fact_bases: FactBaseRepository,
        sessions: SessionRepository,
        audit_agent: FactAuditAgent,
        question_writer: QuestionWriterAgent,
        planner: Optional[QuestionPlanner] = None,
    ) -> None:
        self.fact_bases = fact_bases
        self.sessions = sessions
        self.audit_agent = audit_agent
        self.question_writer = question_writer
        self.planner = planner or QuestionPlanner()

    def create_session(
        self,
        fact_base_id: UUID,
        active_experience_id: UUID,
    ) -> InterviewSession:
        base = self.fact_bases.get(fact_base_id)
        try:
            base.get_experience(active_experience_id)
        except KeyError as error:
            raise ValueError(
                "active experience does not belong to the selected fact base"
            ) from error
        session = InterviewSession(
            fact_base_id=fact_base_id,
            active_experience_id=active_experience_id,
        )
        self.sessions.create(session)
        return self.sessions.get(session.id)

    def get_session(self, session_id: UUID) -> InterviewSession:
        return self.sessions.get(session_id)

    def list_sessions(
        self,
        fact_base_id: UUID,
        experience_id: Optional[UUID] = None,
    ) -> List[InterviewSession]:
        self.fact_bases.get(fact_base_id)
        sessions = self.sessions.list(fact_base_id)
        if experience_id is not None:
            sessions = [
                session
                for session in sessions
                if session.active_experience_id == experience_id
            ]
        return sessions

    def answer(self, session_id: UUID, message: str) -> InterviewTurn:
        session = self.sessions.get(session_id)
        base = self.fact_bases.get(session.fact_base_id)
        if session.active_experience_id is None:
            raise ValueError("an active experience is required before deepening")

        session.messages.append(InterviewMessage(role="user", content=message))
        session.current_question = None
        session.updated_at = utc_now()
        self.sessions.save(session)
        proposal = self.audit_agent.propose(message, session, base)
        if proposal.experience_id != session.active_experience_id:
            raise ValueError("agent proposal targeted a different experience")
        if proposal.fact_base_revision != base.revision:
            raise ValueError("agent proposal used a stale fact-base revision")

        session.pending_proposals[proposal.id] = proposal
        session.updated_at = utc_now()
        self.sessions.save(session)
        return InterviewTurn(proposal=proposal)

    def confirm(self, session_id: UUID, proposal_id: UUID) -> InterviewTurn:
        session = self.sessions.get(session_id)
        try:
            proposal = session.pending_proposals[proposal_id]
        except KeyError as error:
            raise KeyError(f"proposal not pending: {proposal_id}") from error

        base = self.fact_bases.get(session.fact_base_id)
        expected_revision = base.revision
        base.confirm(proposal)
        self.fact_bases.save(base, expected_revision=expected_revision)

        del session.pending_proposals[proposal_id]
        question = self._make_question(session, base)
        if question is not None:
            session.messages.append(
                InterviewMessage(role="assistant", content=question.text)
            )
            session.current_question = question
        session.updated_at = utc_now()
        self.sessions.save(session)
        return InterviewTurn(
            question=question,
            questions=[question.text] if question is not None else [],
        )

    def reject(self, session_id: UUID, proposal_id: UUID) -> InterviewSession:
        session = self.sessions.get(session_id)
        if proposal_id not in session.pending_proposals:
            raise KeyError(f"proposal not pending: {proposal_id}")
        del session.pending_proposals[proposal_id]
        session.updated_at = utc_now()
        self.sessions.save(session)
        return self.sessions.get(session_id)

    def record_unknown(
        self,
        session_id: UUID,
        dimension: QualityDimension,
    ) -> UnknownOutcome:
        session = self.sessions.get(session_id)
        attempts = session.attempts.get(dimension, 0) + 1
        session.attempts[dimension] = attempts
        skipped = attempts >= 2
        if skipped:
            session.skipped_dimensions.add(dimension)
        if (
            session.current_question is not None
            and session.current_question.dimension is dimension
        ):
            session.current_question = None
        session.updated_at = utc_now()
        self.sessions.save(session)
        return UnknownOutcome(
            dimension=dimension,
            attempts=attempts,
            skipped=skipped,
        )

    def next_question(self, session_id: UUID) -> Optional[MentorQuestion]:
        session = self.sessions.get(session_id)
        if session.current_question is not None:
            return session.current_question
        base = self.fact_bases.get(session.fact_base_id)
        question = self._make_question(session, base)
        if question is not None:
            session.messages.append(
                InterviewMessage(role="assistant", content=question.text)
            )
            session.current_question = question
            session.updated_at = utc_now()
            self.sessions.save(session)
        return question

    def _make_question(
        self,
        session: InterviewSession,
        base: CareerFactBase,
    ) -> Optional[MentorQuestion]:
        if session.active_experience_id is None:
            return None
        experience = base.get_experience(session.active_experience_id)
        plan = self.planner.plan(
            experience,
            PlanningSignals(),
            QuestionHistory(
                attempts=session.attempts,
                skipped=session.skipped_dimensions,
            ),
        )
        if plan is None:
            return None
        text = self.question_writer.write(plan, experience, base.target).strip()
        if not text:
            raise ValueError("question writer returned an empty question")
        return MentorQuestion(
            dimension=plan.dimension,
            text=text,
            priority=plan.priority,
            escalation=plan.escalation,
        )
