from __future__ import annotations

import os
import sys
from pathlib import Path

from finance_agent.acceptance_rule_engine import (
    DEFAULT_OUTPUT as DEFAULT_CLASSIFICATION_OUTPUT,
)
from finance_agent.acceptance_rule_engine import (
    classify_vouchers,
    read_json,
    resolve_policy_path,
)
from finance_agent.acceptance_rule_engine import write_json as write_rule_json
from finance_agent.demo_data import build_demo_voucher_payload
from finance_agent.document_voucher_parser import main as cli_main
from finance_agent.document_voucher_parser import write_json
from finance_agent.report_pipeline import (
    DEFAULT_AGENT_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    ReportPipeline,
    run_console_human_review,
    write_text,
)
from finance_agent.report_models import PIPELINE_WAITING_HUMAN


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "voucher_records.json"


def build_default_classification() -> dict:
    voucher_payload = build_demo_voucher_payload()
    policy_path = resolve_policy_path(PROJECT_ROOT)
    return classify_vouchers(voucher_payload, read_json(policy_path))


def run_default_example() -> None:
    print("[main] Loading generated synthetic voucher demo (no real financial files).", flush=True)
    payload = build_demo_voucher_payload()
    write_json(payload, DEFAULT_OUTPUT)
    print(f"[main] Generated {payload['record_count']} synthetic voucher rows -> {DEFAULT_OUTPUT}", flush=True)
    policy_path = resolve_policy_path(PROJECT_ROOT)
    print(f"[main] Classifying vouchers with policy: {policy_path}", flush=True)
    classification = classify_vouchers(payload, read_json(policy_path))
    write_rule_json(classification, PROJECT_ROOT / DEFAULT_CLASSIFICATION_OUTPUT)
    print(
        f"[main] Classified {classification['source_record_count']} records -> {PROJECT_ROOT / DEFAULT_CLASSIFICATION_OUTPUT}",
        flush=True,
    )
    review_mode = os.getenv("REPORT_REVIEW_MODE", "interactive").lower()
    if review_mode not in {"interactive", "auto_approve"}:
        raise ValueError("REPORT_REVIEW_MODE must be either 'interactive' or 'auto_approve'.")

    print(f"[main] Starting report pipeline... review_mode={review_mode}", flush=True)
    pipeline = ReportPipeline(review_mode=review_mode)
    agent_outputs, report = pipeline.run(classification)
    write_rule_json(agent_outputs, PROJECT_ROOT / DEFAULT_AGENT_OUTPUT)
    print(f"Wrote {payload['record_count']} VoucherRecord rows to {DEFAULT_OUTPUT}")
    print(f"Wrote {classification['source_record_count']} classified records to {PROJECT_ROOT / DEFAULT_CLASSIFICATION_OUTPUT}")
    print(f"Wrote report agent outputs to {PROJECT_ROOT / DEFAULT_AGENT_OUTPUT}")
    if agent_outputs.get("pipeline_status") == PIPELINE_WAITING_HUMAN:
        if os.getenv("REPORT_CONSOLE_REVIEW", "1").lower() in {"1", "true", "yes", "on"}:
            agent_outputs, report = run_console_human_review(
                run_id=agent_outputs["run_id"],
                review_package=agent_outputs["human_review_package"],
                pipeline=pipeline,
                verbose_package=os.getenv("REPORT_REVIEW_VERBOSE", "0").lower() in {"1", "true", "yes", "on"},
            )
            write_rule_json(agent_outputs, PROJECT_ROOT / DEFAULT_AGENT_OUTPUT)
            print(f"Wrote report agent outputs to {PROJECT_ROOT / DEFAULT_AGENT_OUTPUT}")
        else:
            print("[main] Report pipeline is waiting for human review; final report was not generated yet.")
            print(f"[main] run_id: {agent_outputs.get('run_id')}")
            print("[main] Review package is included in the agent output JSON.")
            print("[main] Submit a review with submit_human_review(run_id, human_review), then resume the pipeline.")
            return

    if report:
        write_text(report, PROJECT_ROOT / DEFAULT_REPORT_OUTPUT)
        print(f"Wrote final report to {PROJECT_ROOT / DEFAULT_REPORT_OUTPUT}")
    else:
        print("[main] Final report was not generated.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_default_example()
    else:
        cli_main()
