"""Ports that keep domain services independent from agents and storage."""

from typing import List, Protocol
from uuid import UUID

from resume_agent.application.question_planner import QuestionPlan
from resume_agent.domain.models import (
    CareerFactBase,
    CareerTarget,
    Experience,
    FactProposal,
    InterviewSession,
    ResumeVersion,
)


class RevisionConflict(RuntimeError):
    """Raised when a persisted aggregate changed since it was loaded."""


class FactAuditAgent(Protocol):
    def propose(
        self,
        message: str,
        session: InterviewSession,
        base: CareerFactBase,
    ) -> FactProposal: ...


class QuestionWriterAgent(Protocol):
    def write(
        self,
        plan: QuestionPlan,
        experience: Experience,
        target: CareerTarget,
    ) -> str: ...


class FactBaseRepository(Protocol):
    def create(self, base: CareerFactBase) -> None: ...

    def get(self, fact_base_id: UUID) -> CareerFactBase: ...

    def list(self) -> List[CareerFactBase]: ...

    def save(self, base: CareerFactBase, expected_revision: int) -> None: ...


class SessionRepository(Protocol):
    def create(self, session: InterviewSession) -> None: ...

    def get(self, session_id: UUID) -> InterviewSession: ...

    def list(self, fact_base_id: UUID) -> List[InterviewSession]: ...

    def save(self, session: InterviewSession) -> None: ...


class VersionRepository(Protocol):
    def get(self, version_id: UUID) -> ResumeVersion: ...

    def list(self, fact_base_id: UUID) -> List[ResumeVersion]: ...

    def save(self, version: ResumeVersion) -> None: ...

    def activate(self, version_id: UUID) -> ResumeVersion: ...

    def delete(self, version_id: UUID) -> None: ...
