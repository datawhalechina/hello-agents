from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from finance_agent.acceptance_rule_engine import classify_vouchers, read_json
from finance_agent.demo_data import build_demo_voucher_payload
from finance_agent.material_mcp_client import scan_material_folder_via_mcp
from finance_agent.report_agents import AcceptanceReviewAgent
from finance_agent.report_llm import MockLLMClient
from finance_agent.report_models import ReportPipelineState
from finance_agent.report_state_pipeline import build_agent_input, build_shared_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_POLICY_PATH = PROJECT_ROOT / "config" / "demo_acceptance_policy.json"


class MaterialMCPScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = {
            "MATERIAL_ROOT": os.environ.get("MATERIAL_ROOT"),
            "MATERIAL_SCAN_MAX_FILES": os.environ.get("MATERIAL_SCAN_MAX_FILES"),
            "REPORT_CHECKPOINT_BACKEND": os.environ.get("REPORT_CHECKPOINT_BACKEND"),
            "REPORT_STATE_MYSQL_ENABLED": os.environ.get("REPORT_STATE_MYSQL_ENABLED"),
            "REPORT_CONSOLE_LOG": os.environ.get("REPORT_CONSOLE_LOG"),
        }
        os.environ["REPORT_CHECKPOINT_BACKEND"] = "memory"
        os.environ["REPORT_STATE_MYSQL_ENABLED"] = "0"
        os.environ["REPORT_CONSOLE_LOG"] = "0"

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_mcp_scan_returns_read_only_file_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voucher001_contract.pdf").write_text("not parsed", encoding="utf-8")
            (root / "voucher001_invoice.pdf").write_text("not parsed", encoding="utf-8")
            os.environ["MATERIAL_ROOT"] = str(root)

            result = scan_material_folder_via_mcp()

        self.assertTrue(result["available"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["file_count"], 2)
        hits = {item["file_name"]: item["material_keyword_hits"] for item in result["files"]}
        self.assertIn("contract", hits["voucher001_contract.pdf"])
        self.assertIn("invoice", hits["voucher001_invoice.pdf"])
        self.assertTrue(result["policy"]["does_not_parse_file_content"])

    def test_acceptance_agent_input_receives_material_scan_from_mcp(self) -> None:
        classification = classify_vouchers(build_demo_voucher_payload(), read_json(DEMO_POLICY_PATH))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voucher001_bank_receipt.png").write_text("not parsed", encoding="utf-8")
            os.environ["MATERIAL_ROOT"] = str(root)
            state = ReportPipelineState(
                classification=classification,
                records=classification["records"],
                budget_payload=None,
                agent_run_dir=root,
            )
            build_shared_state(state)

            input_json = build_agent_input(AcceptanceReviewAgent(MockLLMClient()), state, {})

        scan = input_json["calculated_data"]["material_folder_scan"]
        self.assertTrue(scan["available"])
        self.assertEqual(scan["file_count"], 1)
        self.assertEqual(scan["files"][0]["file_name"], "voucher001_bank_receipt.png")
        self.assertIn("bank_receipt", scan["files"][0]["material_keyword_hits"])
        self.assertIn("material_name_matching_policy", input_json["calculated_data"])


if __name__ == "__main__":
    unittest.main()
