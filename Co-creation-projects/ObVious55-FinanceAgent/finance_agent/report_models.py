from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4


PIPELINE_RUNNING = "RUNNING"
PIPELINE_WAITING_HUMAN = "WAITING_HUMAN"
PIPELINE_COMPLETED = "COMPLETED"
PIPELINE_STOPPED = "STOPPED"
PIPELINE_RERUN_REQUESTED = "RERUN_REQUESTED"

HUMAN_APPROVED = "HUMAN_APPROVED"
HUMAN_FEEDBACK = "HUMAN_FEEDBACK"
HUMAN_REJECTED = "HUMAN_REJECTED"
HUMAN_REVIEW_STATUSES = {HUMAN_APPROVED, HUMAN_FEEDBACK, HUMAN_REJECTED}


@dataclass(slots=True)
class SharedCalculatedContext:
    records: list[dict[str, Any]]
    budget_payload: dict[str, Any] | None
    total_amount: Decimal
    category_summary: list[dict[str, Any]]
    project_summary: list[dict[str, Any]]
    fund_destination_summary: list[dict[str, Any]]
    large_voucher_records: list[dict[str, Any]]


@dataclass(slots=True)
class ReportContext:
    classification: dict[str, Any]
    records: list[dict[str, Any]]
    budget_payload: dict[str, Any] | None = None
    shared: SharedCalculatedContext | None = None


@dataclass(slots=True)
class AgentRunRecord:
    index: int
    agent: AgentNode
    input_json: dict[str, Any]
    raw_output: str
    parsed_output: dict[str, Any] | str


@dataclass(slots=True)
class StatePatch:
    node: str
    writes: dict[str, Any]
    run_record: AgentRunRecord | None = None


@dataclass(slots=True)
class ReportPipelineState:
    classification: dict[str, Any]
    records: list[dict[str, Any]]
    budget_payload: dict[str, Any] | None
    agent_run_dir: Path
    run_id: str = field(default_factory=lambda: uuid4().hex)
    thread_id: str = field(default_factory=lambda: uuid4().hex)
    business_task: str = "research_finance_acceptance_report"
    schema_version: str = "report_pipeline_state_v1"
    step_no: int = 0
    parent_snapshot_id: int | None = None
    shared: SharedCalculatedContext | None = None
    expense_output: dict[str, Any] | None = None
    budget_output: dict[str, Any] | None = None
    acceptance_output: dict[str, Any] | None = None
    final_report: str = ""
    final_report_generated_at: str | None = None
    outputs_written_at: str | None = None
    agent_runs: list[AgentRunRecord] = field(default_factory=list)
    validation_checks: list[dict[str, Any]] = field(default_factory=list)
    output_payload: dict[str, Any] | None = None
    error_history: list[dict[str, Any]] = field(default_factory=list)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    state_diffs: list[dict[str, Any]] = field(default_factory=list)
    pipeline_status: str = PIPELINE_RUNNING
    human_review_package: dict | None = None
    human_review: dict | None = None
    rerun_context: dict | None = None
    review_mode: str = "interactive"
    rerun_count: int = 0
    max_rerun_count: int = 2
