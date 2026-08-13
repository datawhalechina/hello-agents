"""Transport-only request models for the ResumeAgent API."""

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from resume_agent.domain.models import CareerTarget, QualityDimension


class FactBaseCreateRequest(BaseModel):
    target: CareerTarget = Field(default_factory=CareerTarget)


class ExperienceCreateRequest(BaseModel):
    organization: str = Field(min_length=1)
    role: str = Field(min_length=1)


class SessionCreateRequest(BaseModel):
    fact_base_id: UUID
    active_experience_id: UUID


class AnswerRequest(BaseModel):
    message: str = Field(min_length=1)


class UnknownRequest(BaseModel):
    dimension: QualityDimension


class VersionCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    target_role: str = ""
    company: str = ""
    raw_jd: str = ""
    locale: str = "zh"
    selected_experience_ids: List[UUID] = Field(default_factory=list)


class VersionCloneRequest(BaseModel):
    name: str = Field(min_length=1)


class VersionRenameRequest(BaseModel):
    name: str = Field(min_length=1)
