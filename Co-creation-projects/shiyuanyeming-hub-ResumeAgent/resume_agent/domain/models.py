"""Validated domain models for evidence-led resume mentoring."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConfidenceStatus(str, Enum):
    CONFIRMED = "confirmed"
    ESTIMATED = "estimated"
    UNVERIFIED = "unverified"


class Specificity(str, Enum):
    PRESENT = "present"
    CONCRETE = "concrete"


class QualityDimension(str, Enum):
    CONTEXT = "context"
    RESPONSIBILITY = "responsibility"
    ACTION = "action"
    METHOD = "method"
    RESULT = "result"
    EVIDENCE = "evidence"


class InterviewPhase(str, Enum):
    ORIENT = "orient"
    DISCOVER = "discover"
    DEEPEN = "deepen"
    CONFIRM = "confirm"
    SYNTHESIZE = "synthesize"
    REVISIT = "revisit"


class VersionStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    STALE = "stale"


class FactValue(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str
    confidence: ConfidenceStatus = ConfidenceStatus.UNVERIFIED
    specificity: Specificity = Specificity.PRESENT
    sensitive: bool = False
    source_message_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("fact text must not be empty")
        return stripped


def empty_statements() -> Dict[QualityDimension, List[FactValue]]:
    return {dimension: [] for dimension in QualityDimension}


class Experience(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    organization: str
    role: str
    location: str = ""
    start: str = ""
    end: str = ""
    statements: Dict[QualityDimension, List[FactValue]] = Field(
        default_factory=empty_statements
    )
    linked_skills: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("organization", "role")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("organization and role must not be empty")
        return stripped


class CareerTarget(BaseModel):
    role: str = ""
    seniority: str = ""
    industry: str = ""
    country: str = ""
    languages: List[str] = Field(default_factory=lambda: ["zh", "ja", "en"])


class CandidateProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = Field(default_factory=list)


class FactProposal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fact_base_revision: int = Field(ge=0)
    experience_id: UUID
    dimension: QualityDimension
    values: List[FactValue] = Field(min_length=1)
    rationale: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class CareerFactBase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    revision: int = Field(default=0, ge=0)
    profile: CandidateProfile = Field(default_factory=CandidateProfile)
    target: CareerTarget = Field(default_factory=CareerTarget)
    experiences: List[Experience] = Field(default_factory=list)
    confirmed_proposal_ids: Set[UUID] = Field(default_factory=set)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def add_experience(self, organization: str, role: str) -> Experience:
        experience = Experience(organization=organization, role=role)
        self.experiences.append(experience)
        self.updated_at = utc_now()
        return experience

    def get_experience(self, experience_id: UUID) -> Experience:
        for experience in self.experiences:
            if experience.id == experience_id:
                return experience
        raise KeyError(f"experience not found: {experience_id}")

    def confirm(self, proposal: FactProposal) -> None:
        if proposal.fact_base_revision != self.revision:
            raise ValueError(
                "revision conflict: "
                f"expected {self.revision}, got {proposal.fact_base_revision}"
            )
        if proposal.id in self.confirmed_proposal_ids:
            raise ValueError(f"proposal already confirmed: {proposal.id}")

        experience = self.get_experience(proposal.experience_id)
        confirmed_values = []
        for value in proposal.values:
            if value.confidence is ConfidenceStatus.UNVERIFIED:
                value = value.model_copy(
                    update={"confidence": ConfidenceStatus.CONFIRMED}
                )
            confirmed_values.append(value)
        experience.statements[proposal.dimension].extend(confirmed_values)
        experience.updated_at = utc_now()
        self.confirmed_proposal_ids.add(proposal.id)
        self.revision += 1
        self.updated_at = utc_now()


class InterviewMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message content must not be empty")
        return stripped


class InterviewQuestion(BaseModel):
    dimension: QualityDimension
    text: str
    priority: float
    escalation: str


class InterviewSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fact_base_id: UUID
    phase: InterviewPhase = InterviewPhase.DEEPEN
    active_experience_id: Optional[UUID] = None
    messages: List[InterviewMessage] = Field(default_factory=list)
    pending_proposals: Dict[UUID, FactProposal] = Field(default_factory=dict)
    attempts: Dict[QualityDimension, int] = Field(default_factory=dict)
    skipped_dimensions: Set[QualityDimension] = Field(default_factory=set)
    current_question: Optional[InterviewQuestion] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ResumeVersion(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    fact_base_id: UUID
    name: str
    target_role: str = ""
    company: str = ""
    locale: str = "zh"
    raw_jd: str = ""
    selected_experience_ids: List[UUID] = Field(default_factory=list)
    selected_project_ids: List[UUID] = Field(default_factory=list)
    ordering: List[UUID] = Field(default_factory=list)
    emphasis: Dict[UUID, List[str]] = Field(default_factory=dict)
    styles: Dict[str, str] = Field(default_factory=dict)
    manual_markdown: str = ""
    manual_html: str = ""
    base_revision: int = Field(ge=0)
    status: VersionStatus = VersionStatus.DRAFT
    is_active: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("version name must not be empty")
        return stripped
