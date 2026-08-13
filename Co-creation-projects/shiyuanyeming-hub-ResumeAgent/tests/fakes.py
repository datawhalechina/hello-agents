from copy import deepcopy
from typing import Iterable
from uuid import UUID

from resume_agent.domain.models import (
    CareerFactBase,
    FactProposal,
    FactValue,
    InterviewSession,
    QualityDimension,
)


class InMemoryFactBaseRepository:
    def __init__(self, bases: Iterable[CareerFactBase] = ()):
        self.items = {base.id: deepcopy(base) for base in bases}

    def create(self, base: CareerFactBase) -> None:
        self.items[base.id] = deepcopy(base)

    def get(self, fact_base_id: UUID) -> CareerFactBase:
        return deepcopy(self.items[fact_base_id])

    def save(self, base: CareerFactBase, expected_revision: int) -> None:
        current = self.items[base.id]
        if current.revision != expected_revision:
            raise ValueError("revision conflict")
        self.items[base.id] = deepcopy(base)


class InMemorySessionRepository:
    def __init__(self, sessions: Iterable[InterviewSession] = ()):
        self.items = {session.id: deepcopy(session) for session in sessions}

    def create(self, session: InterviewSession) -> None:
        self.items[session.id] = deepcopy(session)

    def get(self, session_id: UUID) -> InterviewSession:
        return deepcopy(self.items[session_id])

    def save(self, session: InterviewSession) -> None:
        self.items[session.id] = deepcopy(session)


class StubAuditAgent:
    def propose(
        self,
        message: str,
        session: InterviewSession,
        base: CareerFactBase,
    ) -> FactProposal:
        return FactProposal(
            fact_base_revision=base.revision,
            experience_id=session.active_experience_id,
            dimension=QualityDimension.ACTION,
            values=[FactValue(text=message)],
        )


class StubQuestionWriter:
    def write(self, plan, experience, target) -> str:
        return f"请补充这段经历的{plan.dimension.value}。"
