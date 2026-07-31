from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from finance_agent.report_agents import AgentNode
from finance_agent.report_calculations import build_shared_calculated_context
from finance_agent.report_constants import DEFAULT_REPORT_OUTPUT
from finance_agent.report_io import camel_to_snake, extract_agent_data, normalize_agent_output, parse_llm_json, save_agent_run
from finance_agent.report_models import (
    HUMAN_APPROVED,
    HUMAN_FEEDBACK,
    HUMAN_REJECTED,
    HUMAN_REVIEW_STATUSES,
    PIPELINE_COMPLETED,
    PIPELINE_RERUN_REQUESTED,
    PIPELINE_STOPPED,
    PIPELINE_WAITING_HUMAN,
    AgentRunRecord,
    ReportContext,
    ReportPipelineState,
    SharedCalculatedContext,
    StatePatch,
)
from finance_agent.report_observability import (
    apply_state_patch,
    save_state_snapshot,
    trace_event,
)
from finance_agent.report_state_store import MySQLStateStore

MAX_AGENT_SCHEMA_ATTEMPTS = 2
MAX_ERROR_HISTORY_ITEMS = 12
ANALYSIS_AGENT_OUTPUTS = {
    "ExpenseInsightAgent": "expense_output",
    "BudgetVarianceAgent": "budget_output",
    "AcceptanceReviewAgent": "acceptance_output",
}


class RestoredAgentNode:
    def __init__(self, name: str, prompt: str = "", output_format: str = "json") -> None:
        self.name = name
        self.prompt = prompt
        self.output_format = output_format


def build_shared_state(state: ReportPipelineState) -> None:
    trace_event(state, "node_started", "build_shared_state")
    state.shared = build_shared_calculated_context(state.classification, state.records, state.budget_payload)
    trace_event(state, "node_completed", "build_shared_state", writes=["shared"])


def build_report_context(state: ReportPipelineState) -> ReportContext:
    return ReportContext(
        classification=state.classification,
        records=state.records,
        budget_payload=state.budget_payload,
        shared=state.shared,
    )


def run_expense_agent(state: ReportPipelineState, agent: AgentNode) -> StatePatch:
    trace_event(state, "node_started", agent.name)
    record = run_json_agent_with_retry(index=1, agent=agent, state=state, previous_outputs={})
    if not isinstance(record.parsed_output, dict):
        raise ValueError("ExpenseInsightAgent must produce a JSON object.")
    trace_event(state, "node_completed", agent.name, writes=["expense_output"])
    return StatePatch(node=agent.name, writes={"expense_output": record.parsed_output}, run_record=record)


def run_budget_agent(state: ReportPipelineState, agent: AgentNode) -> StatePatch:
    trace_event(state, "node_started", agent.name)
    record = run_json_agent_with_retry(index=2, agent=agent, state=state, previous_outputs={})
    if not isinstance(record.parsed_output, dict):
        raise ValueError("BudgetVarianceAgent must produce a JSON object.")
    trace_event(state, "node_completed", agent.name, writes=["budget_output"])
    return StatePatch(node=agent.name, writes={"budget_output": record.parsed_output}, run_record=record)


def run_acceptance_agent(state: ReportPipelineState, agent: AgentNode) -> StatePatch:
    trace_event(state, "node_started", agent.name)
    record = run_json_agent_with_retry(index=3, agent=agent, state=state, previous_outputs={})
    if not isinstance(record.parsed_output, dict):
        raise ValueError("AcceptanceReviewAgent must produce a JSON object.")
    trace_event(state, "node_completed", agent.name, writes=["acceptance_output"])
    return StatePatch(node=agent.name, writes={"acceptance_output": record.parsed_output}, run_record=record)


def run_final_report_agent(state: ReportPipelineState, agent: AgentNode) -> None:
    if state.final_report.strip() and state.final_report_generated_at:
        trace_event(state, "node_skipped", agent.name, reason="final_report_already_generated")
        state.pipeline_status = PIPELINE_COMPLETED
        return
    trace_event(state, "node_started", agent.name)
    previous_outputs = build_effective_outputs(state)
    record = run_state_agent(index=4, agent=agent, state=state, previous_outputs=previous_outputs)
    patch = StatePatch(node=agent.name, writes={"final_report": record.raw_output}, run_record=record)
    apply_state_patch(state, patch)
    state.pipeline_status = PIPELINE_COMPLETED
    state.final_report_generated_at = datetime.now().isoformat(timespec="seconds")
    trace_event(state, "node_completed", agent.name, writes=["final_report"])


def run_state_agent(
    index: int,
    agent: AgentNode,
    state: ReportPipelineState,
    previous_outputs: dict[str, Any],
) -> AgentRunRecord:
    if agent.output_format == "markdown":
        return run_markdown_agent(index=index, agent=agent, state=state, previous_outputs=previous_outputs)
    return run_json_agent_with_retry(index=index, agent=agent, state=state, previous_outputs=previous_outputs)


def run_markdown_agent(
    index: int,
    agent: AgentNode,
    state: ReportPipelineState,
    previous_outputs: dict[str, Any],
) -> AgentRunRecord:
    input_json: dict[str, Any] = {}
    raw_output = ""
    try:
        input_json = build_agent_input(agent, state, previous_outputs)
        raw_output = call_agent_llm(agent, state, input_json, input_json, attempt=1)
        return build_agent_run_record(index, agent, input_json, raw_output, raw_output)
    except Exception as exc:
        state.agent_runs.append(build_failed_agent_run_record(index, agent, input_json, raw_output, exc))
        trace_event(state, "node_failed", agent.name, error_type=type(exc).__name__, error=str(exc))
        raise


def run_json_agent_with_retry(
    index: int,
    agent: AgentNode,
    state: ReportPipelineState,
    previous_outputs: dict[str, Any],
) -> AgentRunRecord:
    input_json: dict[str, Any] = {}
    raw_output = ""
    try:
        input_json = build_agent_input(agent, state, previous_outputs)
        parsed_output: dict[str, Any]
        last_error: ValueError | None = None
        for attempt in range(1, MAX_AGENT_SCHEMA_ATTEMPTS + 1):
            attempt_input = input_json
            if last_error is not None:
                attempt_input = build_schema_retry_input(input_json, agent.name, state.error_history)
                trace_event(
                    state,
                    "llm_output_schema_retry",
                    agent.name,
                    attempt=attempt,
                    error=str(last_error),
                )
            raw_output = call_agent_llm(agent, state, input_json, attempt_input, attempt)
            try:
                parsed_output = validate_json_agent_output(agent, raw_output, input_json)
                break
            except ValueError as exc:
                last_error = exc
                record_agent_error(state, agent.name, attempt, exc)
                if attempt == MAX_AGENT_SCHEMA_ATTEMPTS:
                    raise
        return build_agent_run_record(index, agent, input_json, raw_output, parsed_output)
    except Exception as exc:
        state.agent_runs.append(build_failed_agent_run_record(index, agent, input_json, raw_output, exc))
        trace_event(state, "node_failed", agent.name, error_type=type(exc).__name__, error=str(exc))
        raise


def build_agent_input(
    agent: AgentNode,
    state: ReportPipelineState,
    previous_outputs: dict[str, Any],
) -> dict[str, Any]:
    context = build_report_context(state)
    input_json = agent.build_input(context, previous_outputs)
    if agent.name == "AcceptanceReviewAgent":
        attach_material_folder_scan(input_json, state)
    if state.rerun_context and agent.name in state.rerun_context.get("rerun_targets", []):
        input_json["human_rerun_context"] = state.rerun_context
    return input_json


def attach_material_folder_scan(input_json: dict[str, Any], state: ReportPipelineState) -> None:
    try:
        from finance_agent.material_mcp_client import scan_material_folder_via_mcp

        max_files = int(os.getenv("MATERIAL_SCAN_MAX_FILES", "1000"))
        scan_result = scan_material_folder_via_mcp(max_files=max_files)
    except Exception as exc:
        scan_result = {
            "schema": "MaterialFolderScanResult",
            "schema_version": "1.0",
            "available": False,
            "read_only": True,
            "reason": f"MCP material folder scan failed: {type(exc).__name__}: {exc}",
            "files": [],
            "policy": {
                "scope": "File-name and metadata scan only.",
                "does_not_parse_file_content": True,
                "does_not_validate_authenticity_or_compliance": True,
            },
        }
        record_agent_error(state, "AcceptanceReviewAgent", 0, exc)

    calculated_data = input_json.setdefault("calculated_data", {})
    calculated_data["material_folder_scan"] = scan_result
    calculated_data["material_name_matching_policy"] = {
        "scope": "File-name keyword existence matching only.",
        "agent_may_output": ["candidate_materials", "missing_items", "human_verification_items"],
        "agent_must_not_judge": [
            "authenticity",
            "compliance",
            "amount_consistency",
            "signature_validity",
            "final_material_validity",
        ],
        "final_decision": "Human reviewer confirms material validity.",
    }
    if isinstance(input_json.get("next_input"), dict):
        input_json["next_input"]["material_folder_scan"] = scan_result

    contract = input_json.get("output_contract")
    if isinstance(contract, dict):
        contract["allowed_data_keys_if_data_is_included"] = sorted(calculated_data.keys())


def call_agent_llm(
    agent: AgentNode,
    state: ReportPipelineState,
    input_json: dict[str, Any],
    attempt_input: dict[str, Any],
    attempt: int,
) -> str:
    trace_event(
        state,
        "llm_call_started",
        agent.name,
        attempt=attempt,
        output_format=agent.output_format,
        input_keys=sorted(attempt_input.keys()),
    )
    raw_output = agent.llm_client.generate(agent.name, agent.prompt, attempt_input, agent.output_format)
    trace_event(
        state,
        "llm_call_completed",
        agent.name,
        attempt=attempt,
        output_format=agent.output_format,
        char_count=len(raw_output),
    )
    return raw_output


def validate_json_agent_output(
    agent: AgentNode,
    raw_output: str,
    input_json: dict[str, Any],
) -> dict[str, Any]:
    parsed_json = parse_llm_json(raw_output, agent.name)
    if parsed_json.get("status") == "llm_output_parse_error":
        raise ValueError(f"{agent.name} LLM output must be valid JSON.")
    return normalize_agent_output(agent.name, parsed_json, input_json)


def build_agent_run_record(
    index: int,
    agent: AgentNode,
    input_json: dict[str, Any],
    raw_output: str,
    parsed_output: dict[str, Any] | str,
) -> AgentRunRecord:
    return AgentRunRecord(
        index=index,
        agent=agent,
        input_json=input_json,
        raw_output=raw_output,
        parsed_output=parsed_output,
    )


def build_failed_agent_run_record(
    index: int,
    agent: AgentNode,
    input_json: dict[str, Any],
    raw_output: str,
    error: Exception,
) -> AgentRunRecord:
    return AgentRunRecord(
        index=index,
        agent=agent,
        input_json=input_json,
        raw_output=raw_output,
        parsed_output={
            "agent": agent.name,
            "status": "agent_failed",
            "error_type": type(error).__name__,
            "error": str(error),
        },
    )


def build_schema_retry_input(
    input_json: dict[str, Any],
    agent_name: str,
    error_history: list[dict[str, Any]],
) -> dict[str, Any]:
    retry_input = dict(input_json)
    agent_errors = [
        item
        for item in error_history
        if item.get("agent") == agent_name
    ][-MAX_ERROR_HISTORY_ITEMS:]
    retry_input["schema_validation_error"] = {
        "error_history": agent_errors,
        "instruction": (
            "Your previous response violated the output contract. Learn from error_history and return corrected strict JSON only. "
            "Do not include a data field unless it exactly copies calculated_data keys and values. "
            "Do not add, rename, or infer structured fields. Do not wrap JSON in Markdown fences."
        ),
    }
    return retry_input


def record_agent_error(state: ReportPipelineState, agent_name: str, attempt: int, error: Exception) -> None:
    state.error_history.append(
        {
            "agent": agent_name,
            "attempt": attempt,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    )
    if len(state.error_history) > MAX_ERROR_HISTORY_ITEMS:
        state.error_history = state.error_history[-MAX_ERROR_HISTORY_ITEMS:]


def state_agent_outputs(state: ReportPipelineState) -> dict[str, Any]:
    required = {
        "ExpenseInsightAgent": state.expense_output,
        "BudgetVarianceAgent": state.budget_output,
        "AcceptanceReviewAgent": state.acceptance_output,
    }
    missing = [name for name, output in required.items() if output is None]
    if missing:
        raise RuntimeError(f"Cannot build final report before agents finish: {', '.join(missing)}")
    return {name: output for name, output in required.items() if output is not None}


def build_effective_outputs(state: ReportPipelineState) -> dict[str, Any]:
    outputs = state_agent_outputs(state)
    human_review = state.human_review or {}
    overrides = human_review.get("overrides", {}) if isinstance(human_review.get("overrides"), dict) else {}
    effective_layer = {
        agent_name: {
            "original_output": output,
            "human_override": overrides.get(agent_name, {}),
            "review_notes": human_review.get("review_notes", []),
        }
        for agent_name, output in outputs.items()
    }
    return {
        **outputs,
        "human_review": human_review,
        "effective_outputs": effective_layer,
    }


def build_human_review_package(state: ReportPipelineState) -> dict:
    outputs = state_agent_outputs(state)
    expense_data = extract_agent_data(outputs["ExpenseInsightAgent"])
    budget_data = extract_agent_data(outputs["BudgetVarianceAgent"])
    acceptance_data = extract_agent_data(outputs["AcceptanceReviewAgent"])
    missing_fund_records = acceptance_data.get("missing_fund_info_records", [])
    large_voucher_records = expense_data.get("large_voucher_records", [])
    budget_variance_available = bool(budget_data.get("variance_available"))

    risk_points = []
    if not budget_variance_available:
        risk_points.append("预算基准缺失，最终报告不得编造预算执行率、预算差异额或差异率。")
    if missing_fund_records:
        risk_points.append("存在项目号、经费号或负责人缺失记录，需人工确认台账补充情况。")
    if large_voucher_records:
        risk_points.append("存在大额凭证，需重点确认合同、采购、验收和支付材料一致性。")

    return {
        "schema": "HumanReviewPackage",
        "schema_version": "1.0",
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "pipeline_status": state.pipeline_status,
        "expense_review": {
            "agent": "ExpenseInsightAgent",
            "status": outputs["ExpenseInsightAgent"].get("status"),
            "summary": {
                "total_record_count": expense_data.get("total_record_count"),
                "total_expense_amount": expense_data.get("total_expense_amount"),
                "large_voucher_count": len(large_voucher_records),
                "top_categories": expense_data.get("category_summary", [])[:5],
            },
            "key_findings": outputs["ExpenseInsightAgent"].get("key_findings", []),
            "risk_points": [item for item in risk_points if "大额凭证" in item],
            "missing_items": [],
        },
        "budget_review": {
            "agent": "BudgetVarianceAgent",
            "status": outputs["BudgetVarianceAgent"].get("status"),
            "summary": {
                "variance_available": budget_data.get("variance_available"),
                "category_variance_count": len(budget_data.get("category_variance", [])),
                "message": budget_data.get("message"),
            },
            "key_findings": outputs["BudgetVarianceAgent"].get("key_findings", []),
            "risk_points": [item for item in risk_points if "预算基准" in item],
            "missing_items": [] if budget_variance_available else ["budget_baseline"],
        },
        "acceptance_review": {
            "agent": "AcceptanceReviewAgent",
            "status": outputs["AcceptanceReviewAgent"].get("status"),
            "summary": {
                "acceptance_required_count": acceptance_data.get("acceptance_required_count"),
                "acceptance_required_amount": acceptance_data.get("acceptance_required_amount"),
                "missing_fund_info_count": len(missing_fund_records),
                "meeting_fee_required_count": len(acceptance_data.get("meeting_fee_required_records", [])),
                "cost_type_sample_count": len(acceptance_data.get("cost_type_sample_records", [])),
            },
            "preparation_focus": outputs["AcceptanceReviewAgent"].get("preparation_focus", []),
            "risk_points": [item for item in risk_points if "缺失" in item],
            "missing_items": missing_fund_records,
        },
        "raw_evidence_refs": {
            "policy_version": state.classification.get("policy_version"),
            "source_record_count": state.classification.get("source_record_count"),
            "record_ids": [record.get("record_id") for record in state.records if record.get("record_id")],
        },
        "editable_policy": {
            "locked": [
                "amount",
                "computed_total",
                "rule_hit_ids",
                "raw_evidence_refs",
                "acceptance_required",
                "is_large_voucher",
                "is_meeting_fee_required",
                "is_cost_type_sample",
            ],
            "editable_with_evidence": [
                "category",
                "responsible_person",
                "funding_code",
                "acceptance_status",
            ],
            "freely_editable": [
                "narrative",
                "review_notes",
                "final_report_instruction",
            ],
        },
        "suggested_actions": [
            HUMAN_APPROVED,
            HUMAN_FEEDBACK,
            HUMAN_REJECTED,
        ],
        "risk_points": risk_points,
    }


def human_review_gate(state: ReportPipelineState) -> ReportPipelineState:
    trace_event(state, "node_started", "human_review_gate")
    state.human_review_package = build_human_review_package(state)
    state.pipeline_status = PIPELINE_WAITING_HUMAN
    if state.review_mode == "auto_approve":
        state.human_review = {
            "status": HUMAN_APPROVED,
            "reviewer": "system:auto_approve",
            "review_notes": [],
            "overrides": {},
            "rerun_required": False,
            "rerun_targets": [],
        }
        state.pipeline_status = HUMAN_APPROVED
        save_state_snapshot(
            state,
            "03_human_review_gate",
            status=HUMAN_APPROVED,
            current_node="human_review_gate",
            next_node="FinalReportAgent",
        )
    else:
        state.human_review = None
        save_state_snapshot(
            state,
            "03_human_review_gate",
            status=PIPELINE_WAITING_HUMAN,
            current_node="human_review_gate",
            next_node=None,
        )
    trace_event(
        state,
        "node_completed",
        "human_review_gate",
        writes=["human_review_package", "pipeline_status", "human_review"],
    )
    return state


def route_after_human_review(state: ReportPipelineState) -> str:
    if state.pipeline_status == PIPELINE_WAITING_HUMAN or not state.human_review:
        return "stop_pipeline"
    status = state.human_review.get("status")
    if status == HUMAN_APPROVED:
        return "final_report_agent"
    if status == HUMAN_FEEDBACK:
        return "rerun_router" if state.human_review.get("rerun_required") else "final_report_agent"
    if status == HUMAN_REJECTED:
        return "stop_pipeline"
    return "stop_pipeline"


def build_rerun_context(state: ReportPipelineState) -> dict:
    human_review = state.human_review or {}
    return {
        "rerun_targets": list(human_review.get("rerun_targets") or []),
        "review_notes": list(human_review.get("review_notes") or []),
        "supplemental_inputs": human_review.get("supplemental_inputs", {}),
        "previous_outputs": state_agent_outputs(state),
        "overrides": human_review.get("overrides", {}),
    }


def rerun_router(state: ReportPipelineState) -> str:
    if state.rerun_count > state.max_rerun_count:
        state.pipeline_status = PIPELINE_STOPPED
        return "stop_pipeline"
    if state.rerun_context is None:
        state.rerun_context = build_rerun_context(state)
    targets = [target for target in state.rerun_context.get("rerun_targets", []) if target in ANALYSIS_AGENT_OUTPUTS]
    if not targets:
        state.pipeline_status = PIPELINE_STOPPED
        return "stop_pipeline"
    state.pipeline_status = PIPELINE_RERUN_REQUESTED
    if len(targets) == 1:
        return {
            "ExpenseInsightAgent": "rerun_expense_agent",
            "BudgetVarianceAgent": "rerun_budget_agent",
            "AcceptanceReviewAgent": "rerun_acceptance_agent",
        }[targets[0]]
    return "analysis_subgraph"


def submit_human_review(run_id: str, human_review: dict) -> ReportPipelineState:
    status = human_review.get("status")
    if status not in HUMAN_REVIEW_STATUSES:
        raise ValueError(
            "human_review.status must be one of "
            f"{', '.join(sorted(HUMAN_REVIEW_STATUSES))}."
        )
    store = MySQLStateStore.from_env()
    if store is None:
        raise RuntimeError("State store is disabled. Enable REPORT_STATE_MYSQL_ENABLED to submit human review by run_id.")
    snapshot = store.latest_waiting_human_snapshot(run_id)
    if snapshot is None:
        raise RuntimeError(f"No WAITING_HUMAN snapshot found for run_id={run_id}.")
    if snapshot.get("status") != PIPELINE_WAITING_HUMAN:
        raise RuntimeError(f"Cannot submit human review when snapshot status is {snapshot.get('status')}.")

    state = restore_state_from_snapshot(snapshot)
    if state.pipeline_status != PIPELINE_WAITING_HUMAN:
        raise RuntimeError(f"Cannot submit human review when pipeline_status is {state.pipeline_status}.")

    normalized_review = {
        "status": status,
        "reviewer": human_review.get("reviewer", "human"),
        "review_notes": list(human_review.get("review_notes") or []),
        "overrides": human_review.get("overrides", {}),
        "rerun_required": bool(human_review.get("rerun_required", False)),
        "rerun_targets": list(human_review.get("rerun_targets") or []),
        "supplemental_inputs": human_review.get("supplemental_inputs", {}),
    }
    if status != HUMAN_FEEDBACK:
        normalized_review["rerun_required"] = False
        normalized_review["rerun_targets"] = []

    state.human_review = normalized_review
    state.pipeline_status = status
    if status == HUMAN_FEEDBACK and normalized_review["rerun_required"]:
        state.rerun_context = build_rerun_context(state)
    else:
        state.rerun_context = None

    next_node = route_after_human_review(state)
    snapshot_status = status
    save_state_snapshot(
        state,
        "04_after_human_review",
        status=snapshot_status,
        current_node="human_review_gate",
        next_node=None if next_node == "stop_pipeline" else next_node,
    )
    return state




def validate_report(state: ReportPipelineState) -> None:
    trace_event(state, "node_started", "validate_report")
    outputs = state_agent_outputs(state)
    expense_data = extract_agent_data(outputs["ExpenseInsightAgent"])
    acceptance_data = extract_agent_data(outputs["AcceptanceReviewAgent"])
    summary = state.classification.get("summary", {})

    checks = [
        {
            "check": "final_report_non_empty",
            "status": "passed" if bool(state.final_report.strip()) else "failed",
        },
        {
            "check": "expense_total_matches_classification_summary",
            "status": "passed"
            if expense_data.get("total_expense_amount") == summary.get("total_expense_amount")
            else "failed",
            "expected": summary.get("total_expense_amount"),
            "actual": expense_data.get("total_expense_amount"),
        },
        {
            "check": "acceptance_count_matches_classification_summary",
            "status": "passed"
            if acceptance_data.get("acceptance_required_count") == summary.get("acceptance_required_count")
            else "failed",
            "expected": summary.get("acceptance_required_count"),
            "actual": acceptance_data.get("acceptance_required_count"),
        },
        {
            "check": "all_analysis_agents_completed",
            "status": "passed",
            "agents": sorted(outputs.keys()),
        },
    ]
    state.validation_checks = checks
    failed = [check["check"] for check in checks if check["status"] != "passed"]
    if failed:
        trace_event(state, "node_failed", "validate_report", failed_checks=failed)
        raise ValueError(f"Report validation failed: {', '.join(failed)}")
    trace_event(state, "node_completed", "validate_report", writes=["validation_checks"])


def write_outputs(state: ReportPipelineState) -> tuple[dict[str, Any], str]:
    if state.output_payload is not None and state.outputs_written_at:
        trace_event(state, "node_skipped", "write_outputs", reason="outputs_already_written")
        state.pipeline_status = PIPELINE_COMPLETED
        return state.output_payload, state.final_report
    trace_event(state, "node_started", "write_outputs")
    state.agent_run_dir.mkdir(parents=True, exist_ok=True)
    for record in sorted(state.agent_runs, key=lambda item: item.index):
        save_agent_run(
            state.agent_run_dir / f"{record.index:02d}_{camel_to_snake(record.agent.name)}.json",
            agent=record.agent,
            input_json=record.input_json,
            raw_output=record.raw_output,
            parsed_output=record.parsed_output,
        )

    state.outputs_written_at = datetime.now().isoformat(timespec="seconds")
    state.output_payload = {
        "schema": "ResearchFinanceReportAgentOutputs",
        "schema_version": "2.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "outputs_written_at": state.outputs_written_at,
        "source_policy_version": state.classification.get("policy_version"),
        "agent_run_dir": str(state.agent_run_dir),
        "agents": state_agent_outputs(state),
        "human_review": state.human_review,
        "effective_outputs": build_effective_outputs(state).get("effective_outputs"),
        "validation_checks": state.validation_checks,
        "final_report": {
            "agent": "FinalReportAgent",
            "path": str(DEFAULT_REPORT_OUTPUT),
            "generated_at": state.final_report_generated_at,
        },
    }
    state.pipeline_status = PIPELINE_COMPLETED
    trace_event(state, "node_completed", "write_outputs", writes=["output_payload"])
    trace_event(
        state,
        "outputs_written",
        "write_outputs",
        report_path=str(DEFAULT_REPORT_OUTPUT),
        agent_output_path=str(state.agent_run_dir),
    )
    return state.output_payload, state.final_report


def restore_state_from_snapshot(snapshot: dict[str, Any]) -> ReportPipelineState:
    payload = decode_snapshot_json(snapshot.get("state_json"))
    runtime_state = payload.get("runtime_state") if isinstance(payload, dict) else None
    if not isinstance(runtime_state, dict):
        raise RuntimeError("Snapshot does not include runtime_state; cannot restore ReportPipelineState.")
    state = restore_runtime_state(runtime_state)
    if snapshot.get("step_no") is not None:
        state.step_no = int(snapshot["step_no"]) + 1
    if snapshot.get("id") is not None:
        state.parent_snapshot_id = int(snapshot["id"])
    return state


def decode_snapshot_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise RuntimeError("Unsupported snapshot state_json payload.")


def restore_runtime_state(payload: dict[str, Any]) -> ReportPipelineState:
    state = ReportPipelineState(
        classification=payload.get("classification", {}),
        records=payload.get("records", []),
        budget_payload=payload.get("budget_payload"),
        agent_run_dir=Path(payload.get("agent_run_dir", "data/processed/agent_runs")),
        run_id=payload.get("run_id", ""),
        thread_id=payload.get("thread_id", ""),
        business_task=payload.get("business_task", "research_finance_acceptance_report"),
        schema_version=payload.get("schema_version", "report_pipeline_state_v1"),
        step_no=int(payload.get("step_no", 0)),
        parent_snapshot_id=payload.get("parent_snapshot_id"),
        shared=restore_shared_context(payload.get("shared")),
        expense_output=payload.get("expense_output"),
        budget_output=payload.get("budget_output"),
        acceptance_output=payload.get("acceptance_output"),
        final_report=payload.get("final_report", ""),
        final_report_generated_at=payload.get("final_report_generated_at"),
        outputs_written_at=payload.get("outputs_written_at"),
        agent_runs=restore_agent_runs(payload.get("agent_runs", [])),
        validation_checks=payload.get("validation_checks", []),
        output_payload=payload.get("output_payload"),
        error_history=payload.get("error_history", []),
        trace_events=payload.get("trace_events", []),
        state_diffs=payload.get("state_diffs", []),
        pipeline_status=payload.get("pipeline_status", "RUNNING"),
        human_review_package=payload.get("human_review_package"),
        human_review=payload.get("human_review"),
        rerun_context=payload.get("rerun_context"),
        review_mode=payload.get("review_mode", "interactive"),
        rerun_count=int(payload.get("rerun_count", 0)),
        max_rerun_count=int(payload.get("max_rerun_count", 2)),
    )
    return state


def restore_shared_context(payload: dict[str, Any] | None) -> SharedCalculatedContext | None:
    if not isinstance(payload, dict):
        return None
    return SharedCalculatedContext(
        records=payload.get("records", []),
        budget_payload=payload.get("budget_payload"),
        total_amount=Decimal(str(payload.get("total_amount", "0"))),
        category_summary=payload.get("category_summary", []),
        project_summary=payload.get("project_summary", []),
        fund_destination_summary=payload.get("fund_destination_summary", []),
        large_voucher_records=payload.get("large_voucher_records", []),
    )


def restore_agent_runs(payload: list[dict[str, Any]]) -> list[AgentRunRecord]:
    records: list[AgentRunRecord] = []
    for item in payload:
        agent_info = item.get("agent", {})
        agent = RestoredAgentNode(
            name=agent_info.get("name", "UnknownAgent"),
            prompt=agent_info.get("prompt", ""),
            output_format=agent_info.get("output_format", "json"),
        )
        records.append(
            AgentRunRecord(
                index=int(item.get("index", 0)),
                agent=agent,  # type: ignore[arg-type]
                input_json=item.get("input_json", {}),
                raw_output=item.get("raw_output", ""),
                parsed_output=item.get("parsed_output", {}),
            )
        )
    return records
