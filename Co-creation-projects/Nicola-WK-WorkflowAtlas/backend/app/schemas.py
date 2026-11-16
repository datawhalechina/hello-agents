"""Shared contracts. Main Agent is the single owner of this file."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


ImportFormat = Literal['auto', 'json', 'jsonl', 'csv', 'txt', 'html']


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReference(Contract):
    message_id: str
    source_id: str
    quote: str = Field(min_length=1)


class StandardMessage(Contract):
    id: str = Field(min_length=1, max_length=300)
    source_id: str = Field(min_length=1, max_length=300)
    source_type: Literal["feishu", "wechat", "qq", "chat", "json", "document"] = "json"
    chat_id: str = ""
    sender: str = "unknown"
    text: str = Field(min_length=1, max_length=100000)
    timestamp: datetime
    thread_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value


class FactKind(StrEnum):
    task = "task"
    event = "event"
    decision = "decision"
    issue = "issue"
    artifact = "artifact"
    plan = "plan"


class WorkFact(Contract):
    id: str
    kind: FactKind
    summary: str
    project_hint: str | None = None
    project_id: str | None = None
    entity_key: str | None = None
    actor: str | None = None
    status: str = "observed"
    occurred_at: datetime
    evidence: list[EvidenceReference] = Field(min_length=1)
    confidence: float = Field(default=0.7, ge=0, le=1)
    verified: bool = False
    review_status: Literal["pending", "accepted", "rejected"] = "pending"
    attributes: dict[str, Any] = Field(default_factory=dict)


class Project(Contract):
    id: str
    name: str
    description: str = ""
    status: str = "active"
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    source_id: str | None = None
    analysis_mode: Literal['local', 'model'] = 'local'


class WorkflowNode(Contract):
    id: str
    project_id: str
    kind: FactKind
    label: str
    status: str = "observed"
    fact_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    occurred_at: datetime
    verified: bool = False


class WorkflowEdge(Contract):
    id: str
    project_id: str
    source: str
    target: str
    relation: Literal["precedes", "depends_on", "blocks", "resolves", "produces", "revises", "branches_to", "parallel_with"]
    evidence: list[EvidenceReference] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0, le=1)
    verified: bool = False
    rationale: str = ""


class WorkflowUpdateProposal(Contract):
    projects: list[Project] = Field(default_factory=list)
    facts: list[WorkFact] = Field(default_factory=list)
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkflowView(Contract):
    project: Project
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    facts: list[WorkFact]
    version: int
    warnings: list[str]
    related_nodes: list[WorkflowNode] = Field(default_factory=list)
    related_edges: list[WorkflowEdge] = Field(default_factory=list)
    related_facts: list[WorkFact] = Field(default_factory=list)


class WorkspaceStats(Contract):
    messages: int
    facts: int
    projects: int
    nodes: int
    edges: int
    pending_review: int
    versions: int


class SourceInfo(Contract):
    id: str
    type: str
    message_count: int
    last_timestamp: str


class SourceAnalysis(Contract):
    source_id: str
    messages: int
    message_types: dict[str, int]
    textual_messages: int
    attachment_messages: int
    reply_messages: int
    extracted_messages: int
    facts: int
    assigned_facts: int
    unassigned_facts: int
    verified_facts: int
    pending_review: int
    projects: int
    nodes: int
    explicit_edges: int
    attribution_methods: dict[str, int]
    notes: list[str]


class AgentTaskResult(Contract):
    agent: str
    status: Literal["completed", "failed", "skipped"]
    input_count: int = 0
    output_count: int = 0
    detail: str = ""
    duration_ms: float = 0


class AnalysisResult(Contract):
    proposal: WorkflowUpdateProposal
    agent_results: list[AgentTaskResult] = Field(default_factory=list)
    provider: str = "local-demo"


class ImportReport(Contract):
    imported: int = 0
    duplicates: int = 0
    source_id: str
    warnings: list[str] = Field(default_factory=list)


class ImportIssue(Contract):
    position: int
    line: int | None = None
    field: str
    code: str
    detail: str
    raw: Any = None


class ImportPreview(Contract):
    source_id: str
    format_detected: Literal['json', 'jsonl', 'csv', 'txt', 'html']
    total: int
    valid: int
    imported_candidates: int = 0
    duplicates: int = 0
    fingerprint: str = ''
    issues: list[ImportIssue] = Field(default_factory=list)
    messages: list[StandardMessage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    candidate_positions: list[int] = Field(default_factory=list, exclude=True)
    candidate_lines: list[int | None] = Field(default_factory=list, exclude=True)
    candidate_raw: list[Any] = Field(default_factory=list, exclude=True)


class ReviewRequest(Contract):
    status: Literal["accepted", "rejected", "pending"]
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=4000)


class ImportRequest(Contract):
    source_id: str = Field(min_length=1, max_length=300)
    messages: list[StandardMessage] = Field(min_length=1, max_length=10000)


class ProcessRequest(Contract):
    source_id: str | None = None


class SourceDeletionPreview(Contract):
    source_id: str
    messages: int
    facts: int
    projects_removed: int
    reviews: int
    versions: int
    checkpoint: bool
    jobs_reset: int
    version: int


class DeleteSourceRequest(Contract):
    confirmation: str = Field(min_length=1, max_length=300)
    expected_messages: int = Field(ge=0)
    expected_version: int = Field(ge=0)


class SourceDeletionResult(Contract):
    source_id: str
    messages_deleted: int
    facts_deleted: int
    projects_removed: int
    reviews_deleted: int
    versions_updated: int
    jobs_reset: int
    remaining_sources: int
    version: int


class FeishuSyncRequest(Contract):
    source_id: str = Field(min_length=1, max_length=300)
    chat_id: str = Field(min_length=1, max_length=300)
    start_time: int | None = Field(default=None, ge=0)
    end_time: int | None = Field(default=None, ge=0)
    incremental: bool = False
    max_pages: int = Field(default=1, ge=1, le=20)


class Job(Contract):
    id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    source_id: str | None = None
    cancel_requested: bool = False
    progress: dict[str, Any] = Field(default_factory=dict)
    purpose: Literal['answer', 'diagram', 'facts'] = 'answer'


class ModelConnectionRequest(Contract):
    model: str = Field(min_length=1, max_length=200)
    base_url: str = Field(min_length=1, max_length=1000)
    api_key: SecretStr | None = None


class ModelSettingsUpdate(Contract):
    provider: Literal["local-demo", "helloagents-llm"]
    model: str = Field(default="", max_length=200)
    base_url: str = Field(default="", max_length=1000)
    api_key: SecretStr | None = None
    clear_api_key: bool = False
    external_data_authorized: bool = False
    batch_size: int = Field(default=5, ge=1, le=10)
    thinking: bool = False


class ModelSettingsView(Contract):
    provider: Literal["local-demo", "helloagents-llm"]
    model: str
    base_url: str
    api_key_configured: bool
    external_data_authorized: bool
    batch_size: int
    saved: bool
    test_status: Literal["not_tested", "passed"] = "not_tested"
    storage_error: str | None = None
    thinking: bool = False


class ModelConnectionResult(Contract):
    ok: bool
    detail: str
    latency_ms: float = 0


class ModelWorkstream(Contract):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    owners: list[str] = Field(default_factory=list)
    status: str
    summary: str
    evidence: list[EvidenceReference] = Field(min_length=1)


class ModelWorkflowStep(Contract):
    id: str = Field(min_length=1)
    workstream_id: str | None = None
    title: str = Field(min_length=1)
    kind: FactKind = FactKind.event
    actor: str | None = None
    status: str
    occurred_at: datetime | None = None
    evidence: list[EvidenceReference] = Field(min_length=1)


class ModelWorkflowRelation(Contract):
    source_step_id: str
    target_step_id: str
    relation: Literal['precedes', 'depends_on', 'blocks', 'resolves', 'produces', 'revises', 'branches_to', 'parallel_with']
    rationale: str
    evidence: list[EvidenceReference] = Field(min_length=1)


class ModelTableRow(Contract):
    cells: list[str]
    evidence: list[EvidenceReference] = Field(min_length=1)


class ModelReportTable(Contract):
    title: str
    columns: list[str] = Field(min_length=1, max_length=12)
    rows: list[ModelTableRow]


class ModelWorkflowReport(Contract):
    summary: str
    workstreams: list[ModelWorkstream]
    steps: list[ModelWorkflowStep]
    relations: list[ModelWorkflowRelation] = Field(default_factory=list)
    tables: list[ModelReportTable] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DirectModelAnswer(Contract):
    markdown: str
    complete: bool = True
    finish_reason: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    model: str
    thinking: bool = False
    thinking_controlled: bool = False
    elapsed_ms: float = 0
