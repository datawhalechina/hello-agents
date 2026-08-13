"""Transport-neutral models produced by the resume renderer."""

from uuid import UUID

from pydantic import BaseModel, Field


class RenderWarning(BaseModel):
    code: str
    message: str


class RenderedExperience(BaseModel):
    organization: str
    role: str
    period: str
    bullets: list[str] = Field(default_factory=list)


class RenderedResume(BaseModel):
    version_id: UUID
    base_revision: int
    version_base_revision: int
    locale: str
    style: str
    title: str
    filename_stem: str
    candidate_name: str
    headline: str
    contact_line: str
    summary: str
    experiences: list[RenderedExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    markdown: str
    html: str
    warnings: list[RenderWarning] = Field(default_factory=list)
