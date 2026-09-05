from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from finance_agent.acceptance_rule_engine import read_json, write_json
from finance_agent.report_agents import (
    AcceptanceReviewAgent,
    AgentNode,
    BudgetVarianceAgent,
    ExpenseInsightAgent,
    FinalReportAgent,
    run_agent_node,
)
from finance_agent.report_calculations import (
    add_amount_ratios,
    build_expense_insights,
    build_shared_calculated_context,
    build_shared_input_summary,
    calculate_acceptance_review,
    calculate_budget_variance,
    percent_str,
    require_shared_context,
    sum_amount,
    summarize_by,
    summarize_fund_destination,
)
from finance_agent.report_constants import (
    DEFAULT_AGENT_OUTPUT,
    DEFAULT_AGENT_RUN_DIR,
    DEFAULT_CLASSIFICATION_INPUT,
    DEFAULT_REPORT_OUTPUT,
    PROJECT_ROOT,
    REQUIRED_CALCULATED_DATA_KEYS,
    REQUIRED_ROW_KEYS,
)
from finance_agent.report_io import (
    camel_to_snake,
    extract_agent_data,
    normalize_agent_output,
    parse_llm_json,
    save_agent_run,
    validate_calculated_data,
    write_text,
)
from finance_agent.report_llm import LLMClient, MockLLMClient, OpenAICompatibleLLMClient
from finance_agent.report_models import (
    HUMAN_APPROVED,
    HUMAN_FEEDBACK,
    HUMAN_REJECTED,
    PIPELINE_WAITING_HUMAN,
    AgentRunRecord,
    ReportContext,
    ReportPipelineState,
    SharedCalculatedContext,
)
from finance_agent.report_rendering import (
    build_deterministic_report,
    render_acceptance_review,
    render_budget_variance,
    render_category_table,
    render_fund_destination,
    render_risk_suggestions,
)
from finance_agent.report_langgraph_pipeline import ReportPipeline
from finance_agent.report_state_pipeline import (
    build_effective_outputs,
    build_human_review_package,
    build_report_context,
    build_rerun_context,
    build_shared_state,
    human_review_gate,
    rerun_router,
    run_acceptance_agent,
    run_budget_agent,
    run_expense_agent,
    run_final_report_agent,
    run_state_agent,
    route_after_human_review,
    state_agent_outputs,
    submit_human_review,
    validate_report,
    write_outputs,
)

__all__ = [
    "AcceptanceReviewAgent",
    "AgentNode",
    "AgentRunRecord",
    "BudgetVarianceAgent",
    "DEFAULT_AGENT_OUTPUT",
    "DEFAULT_AGENT_RUN_DIR",
    "DEFAULT_CLASSIFICATION_INPUT",
    "DEFAULT_REPORT_OUTPUT",
    "ExpenseInsightAgent",
    "FinalReportAgent",
    "LLMClient",
    "MockLLMClient",
    "OpenAICompatibleLLMClient",
    "PROJECT_ROOT",
    "REQUIRED_CALCULATED_DATA_KEYS",
    "REQUIRED_ROW_KEYS",
    "ReportContext",
    "ReportPipeline",
    "ReportPipelineState",
    "SharedCalculatedContext",
    "add_amount_ratios",
    "build_arg_parser",
    "build_deterministic_report",
    "build_effective_outputs",
    "build_expense_insights",
    "build_human_review_package",
    "build_report_context",
    "build_rerun_context",
    "build_shared_calculated_context",
    "build_shared_input_summary",
    "build_shared_state",
    "calculate_acceptance_review",
    "calculate_budget_variance",
    "camel_to_snake",
    "extract_agent_data",
    "human_review_gate",
    "main",
    "normalize_agent_output",
    "parse_llm_json",
    "percent_str",
    "read_json",
    "render_acceptance_review",
    "render_budget_variance",
    "render_category_table",
    "render_fund_destination",
    "render_risk_suggestions",
    "require_shared_context",
    "rerun_router",
    "run_acceptance_agent",
    "run_agent_node",
    "run_budget_agent",
    "run_expense_agent",
    "run_final_report_agent",
    "run_state_agent",
    "route_after_human_review",
    "save_agent_run",
    "state_agent_outputs",
    "submit_human_review",
    "prompt_human_review",
    "run_console_human_review",
    "sum_amount",
    "summarize_by",
    "summarize_fund_destination",
    "validate_calculated_data",
    "validate_report",
    "write_json",
    "write_outputs",
    "write_text",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LLM-backed multi-agent finance acceptance report pipeline.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_CLASSIFICATION_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--agent-output", type=Path, default=DEFAULT_AGENT_OUTPUT)
    parser.add_argument("--agent-run-dir", type=Path, default=DEFAULT_AGENT_RUN_DIR)
    parser.add_argument("--budget", type=Path, default=None, help="Optional budget baseline JSON.")
    parser.add_argument("--mock-llm", action="store_true", help="Use test-only mock LLM client instead of calling a real LLM.")
    parser.add_argument("--review-mode", choices=["interactive", "auto_approve"], default="interactive")
    parser.add_argument(
        "--no-console-review",
        action="store_true",
        help="Stop at WAITING_HUMAN without prompting in the console.",
    )
    parser.add_argument(
        "--verbose-review-package",
        action="store_true",
        help="Print the full human_review_package JSON in the console.",
    )
    return parser


def print_human_review_package(package: dict[str, Any], *, verbose: bool = False) -> None:
    print("\n[human-review] Full review package:", flush=True)
    print(json.dumps(package, ensure_ascii=False, indent=2), flush=True)


def print_review_section(title: str, section: dict[str, Any]) -> None:
    summary = section.get("summary", {}) if isinstance(section, dict) else {}
    risk_points = section.get("risk_points", []) if isinstance(section, dict) else []
    missing_items = section.get("missing_items", []) if isinstance(section, dict) else []
    print(f"  {title}:", flush=True)
    print(f"    status: {section.get('status', '-') if isinstance(section, dict) else '-'}", flush=True)
    print(f"    summary: {json.dumps(summary, ensure_ascii=False)}", flush=True)
    if risk_points:
        print(f"    risk_count: {len(risk_points)}", flush=True)
    if isinstance(missing_items, list):
        print(f"    missing_item_count: {len(missing_items)}", flush=True)


def prompt_human_review(
    package: dict[str, Any],
    *,
    input_func: Callable[[str], str] = input,
    reviewer: str = "console",
    verbose_package: bool = False,
) -> dict[str, Any]:
    print_human_review_package(package, verbose=verbose_package)
    print(
        "\n[human-review] Choose an action:\n"
        "  1. 直接通过\n"
        "  2. 补充反馈但不重跑\n"
        "  3. 补充反馈并要求重跑\n"
        "  4. 拒绝终止",
        flush=True,
    )
    choice = prompt_choice(input_func)
    if choice == "1":
        return {
            "status": HUMAN_APPROVED,
            "reviewer": reviewer,
            "review_notes": [],
            "overrides": {},
            "rerun_required": False,
            "rerun_targets": [],
        }
    if choice == "2":
        return {
            "status": HUMAN_FEEDBACK,
            "reviewer": reviewer,
            "review_notes": prompt_review_notes(input_func),
            "overrides": prompt_json_object(input_func, "请输入 overrides JSON，留空则为 {}: "),
            "rerun_required": False,
            "rerun_targets": [],
        }
    if choice == "3":
        return {
            "status": HUMAN_FEEDBACK,
            "reviewer": reviewer,
            "review_notes": prompt_review_notes(input_func),
            "overrides": prompt_json_object(input_func, "请输入 overrides JSON，留空则为 {}: "),
            "rerun_required": True,
            "rerun_targets": prompt_rerun_targets(input_func),
        }
    return {
        "status": HUMAN_REJECTED,
        "reviewer": reviewer,
        "review_notes": prompt_review_notes(input_func),
        "overrides": {},
        "rerun_required": False,
        "rerun_targets": [],
    }


def prompt_choice(input_func: Callable[[str], str]) -> str:
    valid = {"1", "2", "3", "4"}
    while True:
        choice = input_func("[human-review] 输入选项 1/2/3/4: ").strip()
        if choice in valid:
            return choice
        print("[human-review] 无效选项，请输入 1、2、3 或 4。", flush=True)


def prompt_review_notes(input_func: Callable[[str], str]) -> list[str]:
    raw = input_func("[human-review] 请输入审批意见，多个意见用分号 ; 分隔，留空则无: ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(";") if item.strip()]


def prompt_json_object(input_func: Callable[[str], str], message: str) -> dict[str, Any]:
    while True:
        raw = input_func(message).strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"[human-review] JSON 解析失败: {exc}", flush=True)
            continue
        if isinstance(value, dict):
            return value
        print("[human-review] 请输入 JSON object，例如 {\"BudgetVarianceAgent\": {\"narrative\": \"...\"}}。", flush=True)


def prompt_rerun_targets(input_func: Callable[[str], str]) -> list[str]:
    allowed = {
        "1": "ExpenseInsightAgent",
        "2": "BudgetVarianceAgent",
        "3": "AcceptanceReviewAgent",
        "ExpenseInsightAgent": "ExpenseInsightAgent",
        "BudgetVarianceAgent": "BudgetVarianceAgent",
        "AcceptanceReviewAgent": "AcceptanceReviewAgent",
    }
    print(
        "[human-review] 可重跑 Agent:\n"
        "  1. ExpenseInsightAgent\n"
        "  2. BudgetVarianceAgent\n"
        "  3. AcceptanceReviewAgent",
        flush=True,
    )
    while True:
        raw = input_func("[human-review] 请输入重跑目标，多个用逗号分隔，例如 2,3: ").strip()
        targets = [allowed[item.strip()] for item in raw.split(",") if item.strip() in allowed]
        targets = list(dict.fromkeys(targets))
        if targets:
            return targets
        print("[human-review] 至少选择一个有效重跑目标。", flush=True)


def run_console_human_review(
    *,
    run_id: str,
    review_package: dict[str, Any],
    pipeline: ReportPipeline,
    input_func: Callable[[str], str] = input,
    reviewer: str = "console",
    verbose_package: bool = False,
) -> tuple[dict[str, Any], str]:
    current_run_id = run_id
    current_package = review_package
    while True:
        human_review = prompt_human_review(
            current_package,
            input_func=input_func,
            reviewer=reviewer,
            verbose_package=verbose_package,
        )
        if pipeline.use_langgraph_interrupt:
            agent_outputs, report = pipeline.resume_with_human_review(current_run_id, human_review)
        else:
            state = submit_human_review(current_run_id, human_review)
            agent_outputs, report = pipeline.resume_from_state(state)
        if agent_outputs.get("pipeline_status") != PIPELINE_WAITING_HUMAN:
            return agent_outputs, report
        current_run_id = agent_outputs["run_id"]
        current_package = agent_outputs["human_review_package"]
        print("[human-review] Rerun completed; another human review is required.", flush=True)


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    print(f"[report] Loading classification input: {args.input}", flush=True)
    budget_payload = read_json(args.budget) if args.budget else None
    if args.budget:
        print(f"[report] Loaded budget baseline: {args.budget}", flush=True)
    else:
        print("[report] No budget baseline provided.", flush=True)
    if args.mock_llm:
        print("[report] Using mock LLM client; no network request will be made.", flush=True)
    else:
        print("[report] Using configured real LLM client.", flush=True)
    llm_client: LLMClient = MockLLMClient() if args.mock_llm else OpenAICompatibleLLMClient()
    pipeline = ReportPipeline(
        budget_payload=budget_payload,
        llm_client=llm_client,
        agent_run_dir=args.agent_run_dir,
        review_mode=args.review_mode,
    )
    print("[report] Starting report pipeline...", flush=True)
    agent_outputs, report = pipeline.run(read_json(args.input))
    if agent_outputs.get("pipeline_status") == PIPELINE_WAITING_HUMAN:
        write_json(agent_outputs, args.agent_output)
        if args.no_console_review:
            print(f"[report] Waiting for human review. run_id={agent_outputs.get('run_id')}", flush=True)
            print(f"[report] Review package written to {args.agent_output}", flush=True)
            return
        agent_outputs, report = run_console_human_review(
            run_id=agent_outputs["run_id"],
            review_package=agent_outputs["human_review_package"],
            pipeline=pipeline,
            verbose_package=args.verbose_review_package,
        )
    write_json(agent_outputs, args.agent_output)
    if report:
        write_text(report, args.output)
        print(f"Wrote report to {args.output}")
    else:
        print("[report] Final report was not generated.", flush=True)
    print(f"Wrote agent outputs to {args.agent_output}")
    print(f"Wrote per-agent runs to {args.agent_run_dir}")


if __name__ == "__main__":
    main()
