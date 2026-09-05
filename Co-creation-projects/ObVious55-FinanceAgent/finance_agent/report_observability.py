from __future__ import annotations

import json
import os
import hashlib
from dataclasses import is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from finance_agent.report_io import camel_to_snake
from finance_agent.report_models import (
    PIPELINE_WAITING_HUMAN,
    AgentRunRecord,
    ReportPipelineState,
    SharedCalculatedContext,
    StatePatch,
)
from finance_agent.report_state_store import MySQLStateStore


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def trace_event(state: ReportPipelineState, event: str, node: str, **details: Any) -> None:
    entry = {
        "time": now_iso(),
        "event": event,
        "node": node,
        **details,
    }
    state.trace_events.append(entry)
    log_trace_event(entry)


def log_trace_event(entry: dict[str, Any]) -> None:
    if os.getenv("REPORT_CONSOLE_LOG", "1").lower() in FALSE_VALUES:
        return
    message = format_console_event(entry)
    if message:
        print(message, flush=True)


def format_console_event(entry: dict[str, Any]) -> str | None:
    event = str(entry.get("event", ""))
    node = str(entry.get("node", ""))
    timestamp = str(entry.get("time", ""))[11:19]
    prefix = f"[{timestamp}]"

    if event == "pipeline_started":
        return f"{prefix} Pipeline started: run_id={entry.get('run_id', '-')}, thread_id={entry.get('thread_id', '-')}"
    if event == "pipeline_completed":
        return f"{prefix} Pipeline completed."
    if event == "pipeline_failed":
        return f"{prefix} Pipeline failed at {node}: {entry.get('error_type', 'Error')} - {entry.get('error', '')}"
    if event == "node_started":
        return f"{prefix} Starting {node}..."
    if event == "node_completed":
        writes = ", ".join(entry.get("writes", []) or [])
        suffix = f" wrote: {writes}" if writes else ""
        return f"{prefix} Finished {node}.{suffix}"
    if event == "node_failed":
        return f"{prefix} Failed {node}: {entry.get('error_type', 'Error')} - {entry.get('error', entry.get('failed_checks', ''))}"
    if event == "llm_call_started":
        return f"{prefix} Calling LLM for {node} (attempt {entry.get('attempt', 1)}, format={entry.get('output_format', '-')})..."
    if event == "llm_call_completed":
        return f"{prefix} LLM completed for {node}: {entry.get('char_count', 0)} chars."
    if event == "llm_output_schema_retry":
        return f"{prefix} Retrying {node} because output schema validation failed: {entry.get('error', '')}"
    if event == "state_patch_applied":
        writes = ", ".join(entry.get("writes", []) or [])
        return f"{prefix} Applied state patch from {node}: {writes}"
    if event == "state_snapshot_skipped":
        reason = entry.get("reason", "")
        return f"{prefix} Snapshot skipped for {node}: {reason}."
    if event == "state_snapshot_saved":
        backend = entry.get("backend", "-")
        path = entry.get("path")
        location = f" -> {path}" if path else ""
        return f"{prefix} Snapshot saved for {node} ({backend}){location}."
    if event == "state_snapshot_failed":
        return f"{prefix} Snapshot failed for {node}: {entry.get('error', '')}"
    if event == "outputs_written":
        return f"{prefix} Outputs ready: report={entry.get('report_path')}, agents={entry.get('agent_output_path')}"
    if event == "observability_flushed":
        return f"{prefix} Trace written: {entry.get('trace_path')}"
    if event == "failure_debug_bundle_saved":
        return f"{prefix} Failure debug bundle saved: {entry.get('path')}"
    return None


def apply_state_patch(state: ReportPipelineState, patch: StatePatch) -> None:
    before = summarize_state(state)
    for field_name, value in patch.writes.items():
        setattr(state, field_name, value)
    if patch.run_record is not None:
        state.agent_runs.append(patch.run_record)

    after = summarize_state(state)
    diff = build_state_diff(patch.node, before, after, patch.writes.keys())
    state.state_diffs.append(diff)
    trace_event(
        state,
        "state_patch_applied",
        patch.node,
        writes=sorted(patch.writes.keys()),
        diff=diff["changes"],
    )


def build_state_diff(
    node: str,
    before: dict[str, Any],
    after: dict[str, Any],
    written_fields: Any,
) -> dict[str, Any]:
    changes = {}
    for field_name in written_fields:
        changes[field_name] = {
            "before": before.get(field_name),
            "after": after.get(field_name),
        }
    return {
        "time": now_iso(),
        "node": node,
        "writes": sorted(written_fields),
        "changes": changes,
    }


def save_state_snapshot(
    state: ReportPipelineState,
    name: str,
    *,
    status: str = "SUCCESS",
    current_node: str | None = None,
    next_node: str | None = None,
    error_message: str | None = None,
) -> None:
    snapshot = summarize_state(state)
    snapshot_payload = {
        "summary": snapshot,
        "runtime_state": serialize_runtime_state(state),
    }
    current_node = current_node or infer_current_node(name)
    next_node = next_node if next_node is not None else infer_next_node(name, state)
    patch = current_patch_for_node(state, current_node)
    evidence_refs = build_evidence_references(state)
    store = MySQLStateStore.from_env()
    if store is None:
        trace_event(
            state,
            "state_snapshot_skipped",
            name,
            reason="mysql_disabled",
            step_no=state.step_no,
            current_node=current_node,
            next_node=next_node,
        )
        state.step_no += 1
        if os.getenv("REPORT_STATE_FILE_SNAPSHOT_FALLBACK", "").lower() in TRUE_VALUES:
            snapshot_dir = state.agent_run_dir / "state_snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                snapshot_dir / f"{name}.json",
                {
                    "thread_id": state.thread_id,
                    "step_no": state.step_no - 1,
                    "snapshot_name": name,
                    "current_node": current_node,
                    "next_node": next_node,
                    "status": status,
                    "state": snapshot_payload,
                    "patch": patch,
                    "evidence_references": evidence_refs,
                },
            )
            trace_event(state, "state_snapshot_saved", name, backend="file", path=str(snapshot_dir / f"{name}.json"))
        return

    try:
        state_json = json.dumps(to_jsonable(snapshot_payload), ensure_ascii=False)
        patch_json = json.dumps(to_jsonable(patch), ensure_ascii=False)
        evidence_refs_json = json.dumps(to_jsonable(evidence_refs), ensure_ascii=False)
        snapshot_id = store.save_snapshot(
            run_id=state.run_id,
            business_task=state.business_task,
            thread_id=state.thread_id,
            step_no=state.step_no,
            snapshot_name=name,
            current_node=current_node,
            next_node=next_node,
            policy_version=state.classification.get("policy_version"),
            schema_version=state.schema_version,
            state_json=state_json,
            patch_json=patch_json,
            evidence_refs_json=evidence_refs_json,
            status=status,
            parent_snapshot_id=state.parent_snapshot_id,
            state_hash=hash_json(state_json),
            error_message=error_message,
        )
        state.parent_snapshot_id = snapshot_id
        trace_event(
            state,
            "state_snapshot_saved",
            name,
            backend="mysql",
            run_id=state.run_id,
            thread_id=state.thread_id,
            step_no=state.step_no,
            snapshot_id=snapshot_id,
            current_node=current_node,
            next_node=next_node,
            status=status,
        )
        state.step_no += 1
    except Exception as exc:
        trace_event(state, "state_snapshot_failed", name, backend="mysql", error=str(exc))
        if os.getenv("REPORT_STATE_MYSQL_STRICT", "1").lower() in TRUE_VALUES:
            raise
        if os.getenv("REPORT_STATE_FILE_SNAPSHOT_FALLBACK", "").lower() in TRUE_VALUES:
            snapshot_dir = state.agent_run_dir / "state_snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                snapshot_dir / f"{name}.json",
                {
                    "thread_id": state.thread_id,
                    "step_no": state.step_no,
                    "snapshot_name": name,
                    "current_node": current_node,
                    "next_node": next_node,
                    "status": status,
                    "state": snapshot_payload,
                    "patch": patch,
                    "evidence_references": evidence_refs,
                },
            )
            trace_event(state, "state_snapshot_saved", name, backend="file", path=str(snapshot_dir / f"{name}.json"))
        state.step_no += 1


def flush_observability(state: ReportPipelineState) -> None:
    state.agent_run_dir.mkdir(parents=True, exist_ok=True)
    if os.getenv("REPORT_WRITE_STATE_DIFFS", "").lower() in TRUE_VALUES:
        write_json(state.agent_run_dir / "state_diffs.json", state.state_diffs)
    write_pipeline_graph(state.agent_run_dir / "pipeline_graph.md")
    trace_path = state.agent_run_dir / "pipeline_trace.jsonl"
    trace_event(state, "observability_flushed", "ReportPipeline", trace_path=str(trace_path))
    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in state.trace_events) + "\n",
        encoding="utf-8",
    )


def save_failure_debug_bundle(state: ReportPipelineState, error: BaseException) -> None:
    debug_dir = state.agent_run_dir / "failure_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    trace_event(state, "failure_debug_bundle_saved", "ReportPipeline", path=str(debug_dir), error=str(error))
    write_json(
        debug_dir / "failure_state.json",
        {
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
            "state": summarize_state(state),
            "evidence_references": build_evidence_references(state),
        },
    )
    write_json(debug_dir / "full_patches.json", [full_patch_record(record) for record in state.agent_runs])
    write_json(debug_dir / "state_diffs.json", state.state_diffs)
    trace_path = debug_dir / "pipeline_trace.jsonl"
    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in state.trace_events) + "\n",
        encoding="utf-8",
    )


def serialize_runtime_state(state: ReportPipelineState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "business_task": state.business_task,
        "schema_version": state.schema_version,
        "step_no": state.step_no,
        "parent_snapshot_id": state.parent_snapshot_id,
        "classification": state.classification,
        "records": state.records,
        "budget_payload": state.budget_payload,
        "agent_run_dir": str(state.agent_run_dir),
        "shared": state.shared,
        "expense_output": state.expense_output,
        "budget_output": state.budget_output,
        "acceptance_output": state.acceptance_output,
        "final_report": state.final_report,
        "final_report_generated_at": state.final_report_generated_at,
        "outputs_written_at": state.outputs_written_at,
        "agent_runs": [serialize_agent_run(record) for record in sorted(state.agent_runs, key=lambda item: item.index)],
        "validation_checks": state.validation_checks,
        "output_payload": state.output_payload,
        "error_history": state.error_history,
        "trace_events": state.trace_events,
        "state_diffs": state.state_diffs,
        "pipeline_status": state.pipeline_status,
        "human_review_package": state.human_review_package,
        "human_review": state.human_review,
        "rerun_context": state.rerun_context,
        "review_mode": state.review_mode,
        "rerun_count": state.rerun_count,
        "max_rerun_count": state.max_rerun_count,
    }


def serialize_agent_run(record: AgentRunRecord) -> dict[str, Any]:
    return {
        "index": record.index,
        "agent": {
            "name": record.agent.name,
            "prompt": record.agent.prompt,
            "output_format": record.agent.output_format,
        },
        "input_json": record.input_json,
        "raw_output": record.raw_output,
        "parsed_output": record.parsed_output,
    }


def summarize_state(state: ReportPipelineState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "business_task": state.business_task,
        "schema_version": state.schema_version,
        "step_no": state.step_no,
        "parent_snapshot_id": state.parent_snapshot_id,
        "pipeline_status": state.pipeline_status,
        "classification": summarize_classification(state.classification),
        "records": {"count": len(state.records)},
        "budget_payload": summarize_budget_payload(state.budget_payload),
        "agent_run_dir": str(state.agent_run_dir),
        "shared": summarize_shared(state.shared),
        "expense_output": summarize_agent_output(state.expense_output),
        "budget_output": summarize_agent_output(state.budget_output),
        "acceptance_output": summarize_agent_output(state.acceptance_output),
        "final_report": summarize_text(state.final_report),
        "final_report_generated_at": state.final_report_generated_at,
        "outputs_written_at": state.outputs_written_at,
        "agent_runs": [summarize_agent_run(record) for record in sorted(state.agent_runs, key=lambda item: item.index)],
        "validation_checks": state.validation_checks,
        "output_payload": summarize_output_payload(state.output_payload),
        "error_history": state.error_history,
        "human_review_package": summarize_human_review_package(state.human_review_package),
        "human_review": summarize_human_review(state.human_review),
        "rerun_context": summarize_rerun_context(state.rerun_context),
        "review_mode": state.review_mode,
        "rerun_count": state.rerun_count,
        "max_rerun_count": state.max_rerun_count,
        "waiting_human": state.pipeline_status == PIPELINE_WAITING_HUMAN,
    }


def infer_current_node(snapshot_name: str) -> str:
    mapping = {
        "00_initial_state": "ReportPipeline",
        "01_shared_state": "build_shared_state",
        "03_human_review_gate": "human_review_gate",
        "04_after_human_review": "human_review_gate",
        "05_after_final_report": "FinalReportAgent",
        "06_after_validation": "validate_report",
        "07_after_write_outputs": "write_outputs",
        "99_failure": "ReportPipeline",
    }
    if snapshot_name.startswith("02_after_"):
        return snapshot_name.removeprefix("02_after_")
    return mapping.get(snapshot_name, snapshot_name)


def infer_next_node(snapshot_name: str, state: ReportPipelineState) -> str | None:
    if snapshot_name == "00_initial_state":
        return "build_shared_state"
    if snapshot_name == "01_shared_state":
        return "analysis_subgraph"
    if snapshot_name.startswith("02_after_"):
        if state.expense_output and state.budget_output and state.acceptance_output:
            return "human_review_gate"
        return "analysis_subgraph"
    if snapshot_name == "03_human_review_gate":
        if state.human_review:
            return "FinalReportAgent"
        return None
    if snapshot_name == "04_after_human_review":
        if not state.human_review:
            return None
        if state.human_review.get("status") == "HUMAN_REJECTED":
            return None
        if state.human_review.get("rerun_required"):
            return "rerun_router"
        return "FinalReportAgent"
    if snapshot_name == "05_after_final_report":
        return "validate_report"
    if snapshot_name == "06_after_validation":
        return "write_outputs"
    if snapshot_name == "07_after_write_outputs":
        return None
    return None


def current_patch_for_node(state: ReportPipelineState, current_node: str) -> dict[str, Any]:
    for diff in reversed(state.state_diffs):
        diff_node = str(diff.get("node"))
        if diff_node == current_node or camel_to_snake(diff_node) == current_node:
            return diff
    if current_node == "build_shared_state":
        return {
            "node": current_node,
            "writes": ["shared"],
            "changes": {
                "shared": {
                    "after": summarize_shared(state.shared),
                }
            },
        }
    if current_node == "validate_report":
        return {
            "node": current_node,
            "writes": ["validation_checks"],
            "changes": {
                "validation_checks": {
                    "after": state.validation_checks,
                }
            },
        }
    if current_node == "write_outputs":
        return {
            "node": current_node,
            "writes": ["output_payload"],
            "changes": {
                "output_payload": {
                    "after": summarize_output_payload(state.output_payload),
                }
            },
        }
    if current_node == "human_review_gate":
        return {
            "node": current_node,
            "writes": ["human_review_package", "human_review", "pipeline_status", "rerun_context"],
            "changes": {
                "pipeline_status": {"after": state.pipeline_status},
                "human_review": {"after": summarize_human_review(state.human_review)},
                "rerun_context": {"after": summarize_rerun_context(state.rerun_context)},
            },
        }
    return {
        "node": current_node,
        "writes": [],
        "changes": {},
    }


def hash_json(json_text: str) -> str:
    return hashlib.sha256(json_text.encode("utf-8")).hexdigest()


def build_evidence_references(state: ReportPipelineState) -> dict[str, Any]:
    record_ids = [
        record.get("record_id")
        for record in state.records
        if record.get("record_id")
    ]
    return {
        "run_id": state.run_id,
        "policy_version": state.classification.get("policy_version"),
        "source_record_count": state.classification.get("source_record_count"),
        "record_ids": record_ids,
        "agent_artifacts": [
            {
                "agent": record.agent.name,
                "index": record.index,
                "file": f"{record.index:02d}_{camel_to_snake(record.agent.name)}.json",
            }
            for record in sorted(state.agent_runs, key=lambda item: item.index)
        ],
        "report_output": state.output_payload.get("final_report") if state.output_payload else None,
    }


def summarize_classification(classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": classification.get("schema"),
        "schema_version": classification.get("schema_version"),
        "policy_version": classification.get("policy_version"),
        "source_record_count": classification.get("source_record_count"),
        "summary": classification.get("summary"),
        "category_summary_count": len(classification.get("category_summary", [])),
        "record_count": len(classification.get("records", [])),
    }


def summarize_budget_payload(budget_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not budget_payload:
        return {"available": False}
    return {
        "available": True,
        "category_budget_count": len(budget_payload.get("category_budgets", [])),
    }


def summarize_shared(shared: SharedCalculatedContext | None) -> dict[str, Any] | None:
    if shared is None:
        return None
    return {
        "record_count": len(shared.records),
        "budget_available": shared.budget_payload is not None,
        "total_amount": money_like(shared.total_amount),
        "category_summary_count": len(shared.category_summary),
        "project_summary_count": len(shared.project_summary),
        "fund_destination_summary_count": len(shared.fund_destination_summary),
        "large_voucher_count": len(shared.large_voucher_records),
        "top_categories": shared.category_summary[:3],
    }


def summarize_agent_output(output: dict[str, Any] | None) -> dict[str, Any] | None:
    if output is None:
        return None
    data = output.get("data") if isinstance(output.get("data"), dict) else {}
    return {
        "agent": output.get("agent"),
        "status": output.get("status"),
        "data_keys": sorted(data.keys()),
        "next_input_keys": sorted(output.get("next_input", {}).keys()) if isinstance(output.get("next_input"), dict) else [],
        "data_summary": summarize_agent_data(data),
    }


def summarize_agent_data(data: dict[str, Any]) -> dict[str, Any]:
    summary = {}
    for key in [
        "total_record_count",
        "total_expense_amount",
        "status",
        "variance_available",
        "acceptance_required_count",
        "acceptance_required_amount",
    ]:
        if key in data:
            summary[key] = data[key]
    for key in [
        "category_summary",
        "project_summary",
        "fund_destination_summary",
        "large_voucher_records",
        "category_variance",
        "meeting_fee_required_records",
        "cost_type_sample_records",
        "missing_fund_info_records",
        "preparation_checklist",
        "insights",
    ]:
        if isinstance(data.get(key), list):
            summary[f"{key}_count"] = len(data[key])
    return summary


def summarize_text(text: str) -> dict[str, Any]:
    return {
        "present": bool(text),
        "char_count": len(text),
        "line_count": len(text.splitlines()) if text else 0,
    }


def summarize_agent_run(record: AgentRunRecord) -> dict[str, Any]:
    return {
        "index": record.index,
        "agent": record.agent.name,
        "output_format": record.agent.output_format,
        "input_keys": sorted(record.input_json.keys()),
        "raw_output": summarize_text(record.raw_output),
        "parsed_output_type": type(record.parsed_output).__name__,
        "file": f"{record.index:02d}_{camel_to_snake(record.agent.name)}.json",
    }


def full_patch_record(record: AgentRunRecord) -> dict[str, Any]:
    return {
        "index": record.index,
        "agent": record.agent.name,
        "input_json": record.input_json,
        "raw_output": record.raw_output,
        "parsed_output": record.parsed_output,
    }


def summarize_output_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        "schema": payload.get("schema"),
        "schema_version": payload.get("schema_version"),
        "source_policy_version": payload.get("source_policy_version"),
        "agent_count": len(payload.get("agents", {})),
        "validation_check_count": len(payload.get("validation_checks", [])),
    }


def summarize_human_review_package(package: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(package, dict):
        return None
    return {
        "present": True,
        "schema": package.get("schema"),
        "risk_point_count": len(package.get("risk_points", [])),
        "suggested_actions": package.get("suggested_actions", []),
        "expense_review": package.get("expense_review", {}).get("summary"),
        "budget_review": package.get("budget_review", {}).get("summary"),
        "acceptance_review": package.get("acceptance_review", {}).get("summary"),
    }


def summarize_human_review(review: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(review, dict):
        return None
    return {
        "status": review.get("status"),
        "reviewer": review.get("reviewer"),
        "has_review": True,
        "rerun_required": bool(review.get("rerun_required")),
        "rerun_targets": review.get("rerun_targets", []),
        "review_notes": review.get("review_notes", []),
        "override_targets": sorted(review.get("overrides", {}).keys()) if isinstance(review.get("overrides"), dict) else [],
    }


def summarize_rerun_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    return {
        "rerun_targets": context.get("rerun_targets", []),
        "review_notes": context.get("review_notes", []),
        "has_supplemental_inputs": bool(context.get("supplemental_inputs")),
        "override_targets": sorted(context.get("overrides", {}).keys()) if isinstance(context.get("overrides"), dict) else [],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def write_pipeline_graph(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Report Pipeline Graph

```mermaid
flowchart LR
    A["build_shared_state"] --> S
    subgraph S["analysis_subgraph"]
        B["ExpenseInsightAgent"]
        C["BudgetVarianceAgent"]
        D["AcceptanceReviewAgent"]
        B --> M["merge_analysis_patches"]
        C --> M
        D --> M
    end
    S --> H["human_review_gate"]
    H --> R["route_after_human_review"]
    R -->|HUMAN_APPROVED| E["FinalReportAgent"]
    R -->|HUMAN_FEEDBACK no rerun| E
    R -->|HUMAN_FEEDBACK rerun_required| RR["rerun_router"]
    RR --> S
    R -->|HUMAN_REJECTED or WAITING_HUMAN| X["stop_pipeline"]
    E --> F["validate_report"]
    F --> G["write_outputs"]
```
""",
        encoding="utf-8",
    )


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return money_like(value)
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            key: to_jsonable(getattr(value, key))
            for key in getattr(value, "__dataclass_fields__", {})
        }
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


def money_like(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"
