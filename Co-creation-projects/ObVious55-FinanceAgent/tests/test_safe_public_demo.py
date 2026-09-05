from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from finance_agent.acceptance_rule_engine import classify_vouchers, read_json, resolve_policy_path
from finance_agent.demo_data import build_demo_voucher_payload
from finance_agent.report_langgraph_pipeline import ReportPipeline
from finance_agent.report_llm import MockLLMClient
from main import build_default_classification


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SafePublicDemoTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_demo_payload_is_fixed_and_clearly_synthetic(self) -> None:
        payload = build_demo_voucher_payload()

        self.assertEqual(payload["schema"], "SyntheticVoucherRecordCollection")
        self.assertEqual(payload["record_count"], 8)
        self.assertEqual(
            sum(Decimal(record["expense_amount"]) for record in payload["records"]),
            Decimal("218750.00"),
        )
        self.assertTrue(all(record["record_id"].startswith("DEMO-") for record in payload["records"]))
        self.assertTrue(all(record["voucher_no"].startswith("DEMO-V-2026-") for record in payload["records"]))
        self.assertTrue(all(record["project_code"] == "DEMO-PROJECT-001" for record in payload["records"]))
        self.assertTrue(all(record["fund_owner"] == "示例负责人" for record in payload["records"]))
        self.assertTrue(all(record["parse_warnings"] == [] for record in payload["records"]))

    def test_policy_path_defaults_to_public_demo_and_allows_private_override(self) -> None:
        old_value = os.environ.pop("FINANCE_ACCEPTANCE_POLICY", None)
        try:
            default_path = resolve_policy_path(PROJECT_ROOT)
            self.assertEqual(default_path, PROJECT_ROOT / "config" / "demo_acceptance_policy.json")

            with tempfile.TemporaryDirectory() as tmp:
                private_policy = Path(tmp) / "private-policy.json"
                private_policy.write_text("{}", encoding="utf-8")
                os.environ["FINANCE_ACCEPTANCE_POLICY"] = str(private_policy)
                self.assertEqual(resolve_policy_path(PROJECT_ROOT), private_policy.resolve())
        finally:
            if old_value is None:
                os.environ.pop("FINANCE_ACCEPTANCE_POLICY", None)
            else:
                os.environ["FINANCE_ACCEPTANCE_POLICY"] = old_value

    def test_generated_demo_runs_through_rule_and_report_pipeline_offline(self) -> None:
        classification = classify_vouchers(
            build_demo_voucher_payload(),
            read_json(PROJECT_ROOT / "config" / "demo_acceptance_policy.json"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            payload, report = ReportPipeline(
                llm_client=MockLLMClient(),
                agent_run_dir=Path(tmp),
                review_mode="auto_approve",
            ).run(classification)

        self.assertEqual(classification["source_record_count"], 8)
        self.assertEqual(classification["summary"]["total_expense_amount"], "218750.00")
        self.assertEqual(payload["final_report"]["agent"], "FinalReportAgent")
        self.assertIn("科研项目经费使用及验收准备分析报告", report)

    def test_default_classification_uses_generated_demo(self) -> None:
        classification = build_default_classification()

        self.assertEqual(classification["source_record_count"], 8)
        self.assertEqual(classification["policy_version"], "public_demo_acceptance_v1.0")
        self.assertTrue(all(record["record_id"].startswith("DEMO-") for record in classification["records"]))


if __name__ == "__main__":
    unittest.main()
