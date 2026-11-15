from typing import Literal

from pydantic import BaseModel, Field, field_validator

Mode = Literal["demo", "live"]


class WorkspaceInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(default="Agent 应用开发工程师", max_length=120)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("名称不能为空")
        return value.strip()


class MaterialsInput(BaseModel):
    resume: str = Field(max_length=24000)
    job: str = Field(max_length=16000)


class ModeInput(BaseModel):
    mode: Mode = "demo"


class SessionInput(ModeInput):
    demonstration: bool = False
    count: int = Field(default=12, ge=2, le=24)
    max_topic_turns: int = Field(default=6, ge=2, le=8)
    focus: Literal["all", "weak"] = "all"
    source_session_id: str | None = None


class AnswerInput(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)
    question_id: str
    request_id: str = Field(min_length=8, max_length=100)

    @field_validator("answer")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请先填写回答")
        return value.strip()


class Requirement(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    requirement_quote: str = Field(min_length=1, max_length=1200)
    evidence_quote: str = Field(default="", max_length=1600)
    status: Literal["supported", "partial", "missing", "needs_review"]
    reason: str = Field(max_length=800)
    topic: str = Field(max_length=100)
    priority: Literal["high", "medium", "low"] = "medium"
    preparation_action: str = Field(default="", max_length=500)


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    quote: str = Field(min_length=1, max_length=1600)
    topic: str = Field(max_length=100)
    risk: Literal["normal", "ownership", "metric", "technical"] = "technical"


class AnalysisOutput(BaseModel):
    summary: str = Field(max_length=1200)
    requirements: list[Requirement] = Field(min_length=1, max_length=12)
    claims: list[Claim] = Field(min_length=1, max_length=8)


class Question(BaseModel):
    text: str = Field(min_length=8, max_length=700)
    topic: str = Field(max_length=100)
    source_quote: str = Field(default="", max_length=1600)
    intent: str = Field(max_length=500)
    criteria: list[str] = Field(min_length=2, max_length=5)


class ConfirmInput(BaseModel):
    confirmed: bool


class DemonstrationInput(BaseModel):
    question_id: str = Field(min_length=1, max_length=80)


class DemonstrationAnswer(BaseModel):
    answer: str = Field(min_length=20, max_length=3000)


Facet = Literal[
    "correctness", "implementation", "ownership", "tradeoffs", "validation", "clarity"
]


class EvidenceRef(BaseModel):
    turn_id: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=1000)


class TopicProgress(BaseModel):
    covered: list[Facet] = Field(default_factory=list, max_length=6)
    gaps: list[str] = Field(default_factory=list, max_length=6)
    contradictions: list[str] = Field(default_factory=list, max_length=4)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=6)


class InterviewDecision(BaseModel):
    action: Literal["ask_followup", "switch_topic", "finish"]
    topic_id: str = Field(max_length=80)
    reason: str = Field(min_length=3, max_length=600)
    closure: Literal["sufficient", "knowledge_boundary", "no_progress"] | None = None
    question: Question | None = None
    progress: TopicProgress = Field(default_factory=TopicProgress)


class DimensionScore(BaseModel):
    dimension: Facet
    score: int | None = Field(ge=0, le=4, strict=True)
    reason: str = Field(min_length=3, max_length=600)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=4)


class Finding(BaseModel):
    text: str = Field(min_length=3, max_length=600)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=4)


class TopicScore(BaseModel):
    topic_id: str
    score: int | None = Field(ge=0, le=4, strict=True)
    reason: str = Field(min_length=3, max_length=600)
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=4)


class Improvement(BaseModel):
    topic_id: str
    priority: Literal["high", "medium", "low"]
    title: str = Field(min_length=3, max_length=120)
    detail: str = Field(min_length=3, max_length=700)
    exercise: str = Field(min_length=3, max_length=700)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=4)


class JudgeOutput(BaseModel):
    summary: str = Field(min_length=3, max_length=1200)
    scores: list[DimensionScore] = Field(min_length=6, max_length=6)
    topics: list[TopicScore] = Field(min_length=1, max_length=6)
    strengths: list[Finding] = Field(default_factory=list, max_length=6)
    weaknesses: list[Finding] = Field(default_factory=list, max_length=8)
    improvements: list[Improvement] = Field(default_factory=list, max_length=8)


class ReferenceAnswer(BaseModel):
    turn_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=20, max_length=1600)
    key_points: list[str] = Field(min_length=1, max_length=6)
    pitfalls: list[str] = Field(default_factory=list, max_length=4)


class ReferenceAnswersOutput(BaseModel):
    answers: list[ReferenceAnswer] = Field(min_length=1, max_length=4)
