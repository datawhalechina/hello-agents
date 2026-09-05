from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from finance_agent.acceptance_rule_engine import classify_vouchers, read_json
from finance_agent.demo_data import build_demo_voucher_payload
from finance_agent.report_langgraph_pipeline import ReportPipeline
from finance_agent.report_llm import MockLLMClient
from finance_agent.report_models import HUMAN_APPROVED, HUMAN_FEEDBACK, HUMAN_REJECTED, PIPELINE_WAITING_HUMAN
from finance_agent.report_state_pipeline import (
    build_effective_outputs,
    build_human_review_package,
    build_rerun_context,
    route_after_human_review,
)
from finance_agent.report_pipeline import prompt_human_review


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_POLICY_PATH = PROJECT_ROOT / "config" / "demo_acceptance_policy.json"


class HumanReviewPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = {
            "REPORT_STATE_MYSQL_ENABLED": os.environ.get("REPORT_STATE_MYSQL_ENABLED"),
            "REPORT_STATE_FILE_SNAPSHOT_FALLBACK": os.environ.get("REPORT_STATE_FILE_SNAPSHOT_FALLBACK"),
            "REPORT_CONSOLE_LOG": os.environ.get("REPORT_CONSOLE_LOG"),
            "REPORT_CHECKPOINT_BACKEND": os.environ.get("REPORT_CHECKPOINT_BACKEND"),
        }
        os.environ["REPORT_STATE_MYSQL_ENABLED"] = "0"
        os.environ["REPORT_STATE_FILE_SNAPSHOT_FALLBACK"] = "1"
        os.environ["REPORT_CONSOLE_LOG"] = "0"
        os.environ["REPORT_CHECKPOINT_BACKEND"] = "memory"
        self.classification = classify_vouchers(build_demo_voucher_payload(), read_json(DEMO_POLICY_PATH))

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_auto_approve_pipeline_runs_to_final_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload, report = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="auto_approve",
            ).run(self.classification)

        self.assertTrue(report.strip())
        self.assertEqual(payload["human_review"]["status"], HUMAN_APPROVED)
        self.assertIn("effective_outputs", payload)

    def test_interactive_pipeline_stops_waiting_human(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload, report = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            ).run(self.classification)
            snapshot_path = Path(tmp) / "state_snapshots" / "03_human_review_gate.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["pipeline_status"], PIPELINE_WAITING_HUMAN)
        self.assertEqual(report, "")
        self.assertIn("human_review_package", payload)
        self.assertEqual(snapshot["status"], PIPELINE_WAITING_HUMAN)
        self.assertIn("runtime_state", snapshot["state"])

    def test_review_routes_and_effective_outputs_are_overlay_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload, _ = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            ).run(self.classification)
            snapshot = json.loads((Path(tmp) / "state_snapshots" / "03_human_review_gate.json").read_text(encoding="utf-8"))
            state_payload = snapshot["state"]["runtime_state"]

        self.assertIn("human_review_package", state_payload)
        self.assertEqual(payload["pipeline_status"], PIPELINE_WAITING_HUMAN)

        # Rehydrate enough for pure state helpers through the saved runtime payload.
        from finance_agent.report_state_pipeline import restore_runtime_state

        state = restore_runtime_state(state_payload)
        package = build_human_review_package(state)
        self.assertIn("editable_policy", package)

        original_acceptance = state.acceptance_output
        state.human_review = {
            "status": HUMAN_FEEDBACK,
            "review_notes": ["请在最终报告中说明预算基准缺失。"],
            "overrides": {"AcceptanceReviewAgent": {"narrative": "人工备注层"}},
            "rerun_required": False,
            "rerun_targets": [],
        }
        state.pipeline_status = HUMAN_FEEDBACK
        effective = build_effective_outputs(state)
        self.assertIs(state.acceptance_output, original_acceptance)
        self.assertEqual(
            effective["effective_outputs"]["AcceptanceReviewAgent"]["human_override"]["narrative"],
            "人工备注层",
        )
        self.assertEqual(route_after_human_review(state), "final_report_agent")

        state.human_review = {
            "status": HUMAN_FEEDBACK,
            "review_notes": ["重跑预算分析。"],
            "overrides": {},
            "rerun_required": True,
            "rerun_targets": ["BudgetVarianceAgent"],
        }
        state.pipeline_status = HUMAN_FEEDBACK
        rerun_context = build_rerun_context(state)
        self.assertEqual(rerun_context["rerun_targets"], ["BudgetVarianceAgent"])
        self.assertEqual(route_after_human_review(state), "rerun_router")

        state.human_review = {"status": HUMAN_REJECTED}
        state.pipeline_status = HUMAN_REJECTED
        self.assertEqual(route_after_human_review(state), "stop_pipeline")

    def test_resume_from_waiting_state_after_human_approval(self) -> None:
        from finance_agent.report_state_pipeline import restore_runtime_state

        with tempfile.TemporaryDirectory() as tmp:
            _, waiting_report = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            ).run(self.classification)
            snapshot = json.loads((Path(tmp) / "state_snapshots" / "03_human_review_gate.json").read_text(encoding="utf-8"))
            state = restore_runtime_state(snapshot["state"]["runtime_state"])
            state.step_no = int(snapshot["step_no"]) + 1
            state.human_review = {
                "status": HUMAN_APPROVED,
                "reviewer": "unit-test",
                "review_notes": ["通过。"],
                "overrides": {},
                "rerun_required": False,
                "rerun_targets": [],
            }
            state.pipeline_status = HUMAN_APPROVED
            payload, final_report = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            ).resume_from_state(state)

        self.assertEqual(waiting_report, "")
        self.assertTrue(final_report.strip())
        self.assertEqual(payload["human_review"]["reviewer"], "unit-test")

    def test_checkpoint_resume_with_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            )
            waiting_payload, waiting_report = pipeline.run(self.classification)
            final_payload, final_report = pipeline.resume_with_human_review(
                waiting_payload["run_id"],
                {
                    "status": HUMAN_APPROVED,
                    "reviewer": "checkpoint-test",
                    "review_notes": ["checkpoint resume approved"],
                    "overrides": {},
                    "rerun_required": False,
                    "rerun_targets": [],
                },
            )

        self.assertEqual(waiting_payload["pipeline_status"], PIPELINE_WAITING_HUMAN)
        self.assertEqual(waiting_report, "")
        self.assertTrue(final_report.strip())
        self.assertEqual(final_payload["human_review"]["reviewer"], "checkpoint-test")

    def test_checkpoint_resume_rejects_without_final_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            )
            waiting_payload, _ = pipeline.run(self.classification)
            final_payload, final_report = pipeline.resume_with_human_review(
                waiting_payload["run_id"],
                {
                    "status": HUMAN_REJECTED,
                    "reviewer": "checkpoint-test",
                    "review_notes": ["reject"],
                    "overrides": {},
                    "rerun_required": False,
                    "rerun_targets": [],
                },
            )

        self.assertEqual(final_report, "")
        self.assertFalse(final_payload["final_report"]["generated"])

    def test_checkpoint_resume_rerun_returns_to_human_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="interactive",
            )
            waiting_payload, _ = pipeline.run(self.classification)
            rerun_payload, rerun_report = pipeline.resume_with_human_review(
                waiting_payload["run_id"],
                {
                    "status": HUMAN_FEEDBACK,
                    "reviewer": "checkpoint-test",
                    "review_notes": ["rerun budget"],
                    "overrides": {},
                    "rerun_required": True,
                    "rerun_targets": ["BudgetVarianceAgent"],
                },
            )

        self.assertEqual(rerun_report, "")
        self.assertEqual(rerun_payload["pipeline_status"], PIPELINE_WAITING_HUMAN)
        self.assertIn("human_review_package", rerun_payload)

    def test_console_prompt_builds_all_human_review_statuses(self) -> None:
        package = {"schema": "HumanReviewPackage"}

        approved = prompt_human_review(package, input_func=iter_input(["1"]), reviewer="tester")
        self.assertEqual(approved["status"], HUMAN_APPROVED)
        self.assertFalse(approved["rerun_required"])

        feedback_no_rerun = prompt_human_review(
            package,
            input_func=iter_input(["2", "note A;note B", '{"BudgetVarianceAgent": {"narrative": "manual"}}']),
            reviewer="tester",
        )
        self.assertEqual(feedback_no_rerun["status"], HUMAN_FEEDBACK)
        self.assertFalse(feedback_no_rerun["rerun_required"])
        self.assertEqual(feedback_no_rerun["review_notes"], ["note A", "note B"])

        feedback_rerun = prompt_human_review(
            package,
            input_func=iter_input(["3", "rerun budget", "{}", "2,3"]),
            reviewer="tester",
        )
        self.assertEqual(feedback_rerun["status"], HUMAN_FEEDBACK)
        self.assertTrue(feedback_rerun["rerun_required"])
        self.assertEqual(feedback_rerun["rerun_targets"], ["BudgetVarianceAgent", "AcceptanceReviewAgent"])

        rejected = prompt_human_review(package, input_func=iter_input(["4", "reject"]), reviewer="tester")
        self.assertEqual(rejected["status"], HUMAN_REJECTED)
        self.assertFalse(rejected["rerun_required"])



def iter_input(values: list[str]):
    iterator = iter(values)

    def input_func(_prompt: str) -> str:
        return next(iterator)

    return input_func


if __name__ == "__main__":
    unittest.main()
