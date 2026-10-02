"""Validated model wire contracts. Evidence always points to supplied source text."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal["unknown", "secondary", "associate", "bachelor", "master", "doctorate"]


class Contract(BaseModel):
    """Strict wire model rejecting unexpected fields and implicit type coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Contract):
    """A verbatim CV quotation with inclusive physical line numbers."""

    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: str = Field(min_length=1)


class Section(Contract):
    """One CV category's explicit parsing status and source facts."""

    status: Literal["ok", "missing", "unparseable"]
    facts: list[Evidence]


class Sections(Contract):
    """The five supported CV categories, independent of Markdown chapter order."""

    summary: Section
    skills: Section
    history: Section
    education: Section
    achievements: Section

    def all_sections(self) -> tuple[Section, ...]:
        """Expose categories without depending on Pydantic storage internals."""
        return (
            self.summary,
            self.skills,
            self.history,
            self.education,
            self.achievements,
        )


class CV(Contract):
    """Extracted candidate facts and explicitly evidenced highest education level."""

    sections: Sections
    education_level: Level


class Requirement(Contract):
    """One independently checkable job qualification with its original wording."""

    id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    category: Literal["mandatory", "general", "bonus"]
    minimum_education: Level


class ParsedJob(Contract):
    """A source job's scoring requirements and quoted non-scoring background."""

    row: int = Field(ge=2)
    status: Literal["ok", "missing", "unparseable"]
    requirements: list[Requirement]
    background: list[str] = Field(default_factory=list)


class ParsedJobs(Contract):
    """Every parsed job, preserving original CSV record order."""

    jobs: list[ParsedJob]


class Assessment(Contract):
    """An evidence-based judgment for one identified qualification."""

    requirement_id: str
    verdict: Literal["match", "mismatch", "unknown"]
    reason: str = Field(min_length=1)
    cv_evidence: list[Evidence]


class Match(Contract):
    """Model-reasoned score, rationale and assessments for one source job."""

    row: int = Field(ge=2)
    score: float | None = Field(ge=0, le=100, allow_inf_nan=False)
    reason: str = Field(min_length=1)
    assessments: list[Assessment]


class Matches(Contract):
    """One model evaluation per source job, validated before presentation."""

    jobs: list[Match]


@dataclass(frozen=True)
class JobRow:
    """Raw CSV display fields paired with a stable physical record identity."""

    row: int  # physical starting line, including quoted multiline CSV records
    fields: dict[str, str]


EvaluationState = Literal["ranked", "unable", "eliminated"]


@dataclass(frozen=True)
class EvaluatedJob:
    """Source, parsed requirements and validated evaluation kept together."""

    source: JobRow
    parsed: ParsedJob
    match: Match
    state: EvaluationState
