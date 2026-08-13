"""Transport-only request models for the ResumeAgent API."""

from pydantic import BaseModel, Field

from resume_agent.domain.models import CareerTarget


class FactBaseCreateRequest(BaseModel):
    target: CareerTarget = Field(default_factory=CareerTarget)


class ExperienceCreateRequest(BaseModel):
    organization: str = Field(min_length=1)
    role: str = Field(min_length=1)
