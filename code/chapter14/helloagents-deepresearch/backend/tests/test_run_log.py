from __future__ import annotations

import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.run_log import RunLogger, load_run_log


class RunLoggerTests(unittest.TestCase):
    def test_metadata_log_omits_all_sensitive_run_content(self) -> None:
        secret = "student@example.com 13800138000"
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="privacy",
                log_dir=tmpdir,
                user_input=secret,
            )
            run_logger.record_llm(
                operation="planner",
                request_hash="request-hash",
                messages=[{"role": "user", "content": secret}],
                tools=[{"name": "private-tool", "token": secret}],
                response={
                    "content": secret,
                    "model": "fake",
                    "usage": {"total_tokens": 7},
                    "latency_ms": 12,
                    "reasoning_content": secret,
                    "tool_calls": [{"arguments": secret}],
                    "metadata": {"provider_payload": secret},
                },
                parsed_action={"action": "search", "raw": secret},
            )
            run_logger.record_tool_result(
                tool_name="search",
                input_payload={"query": secret},
                result={"results": [{"content": secret}]},
            )
            run_logger.set_final_answer(f"report: {secret}")
            run_logger.set_error(RuntimeError(secret))

            raw_log = run_logger.path.read_text(encoding="utf-8")
            payload = json.loads(raw_log)

        self.assertNotIn(secret, raw_log)
        self.assertEqual(payload["schema_version"], 3)
        self.assertEqual(payload["log_level"], "metadata")
        self.assertEqual(len(payload["user_input"]["sha256"]), 64)
        self.assertEqual(len(payload["messages"][0]["messages"]["sha256"]), 64)
        self.assertEqual(len(payload["messages"][0]["tools"]["sha256"]), 64)
        self.assertEqual(payload["llm_response"][0]["model"], "fake")
        self.assertEqual(payload["llm_response"][0]["usage"], {"total_tokens": 7})
        self.assertEqual(payload["llm_response"][0]["latency_ms"], 12)
        self.assertEqual(len(payload["llm_response"][0]["response"]["sha256"]), 64)
        self.assertEqual(
            len(payload["parsed_action"][0]["parsed_action"]["sha256"]),
            64,
        )
        self.assertEqual(
            payload["tool_result"][0]["input_hash"],
            payload["tool_result"][0]["input"]["sha256"],
        )
        self.assertEqual(len(payload["tool_result"][0]["result"]["sha256"]), 64)
        self.assertEqual(len(payload["final_answer"]["sha256"]), 64)
        self.assertEqual(payload["error"]["type"], "RuntimeError")
        self.assertEqual(len(payload["error"]["sha256"]), 64)

    def test_full_log_retains_replay_content_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="full",
                log_dir=tmpdir,
                user_input="private input",
                level="full",
            )
            run_logger.record_llm(
                operation="planner",
                request_hash="request-hash",
                messages=[{"role": "user", "content": "private input"}],
                tools=None,
                response={"content": "full response", "model": "fake"},
                parsed_action={"raw": "full response"},
            )
            run_logger.record_tool_result(
                tool_name="search",
                input_payload={"query": "private input"},
                result={"content": "full search result"},
            )
            run_logger.set_final_answer("full report")
            run_logger.set_error("full error")
            payload = load_run_log(run_logger.path, require_replay=True)

        self.assertEqual(payload["schema_version"], 3)
        self.assertEqual(payload["log_level"], "full")
        self.assertIn("WARNING", payload["privacy_notice"])
        self.assertEqual(payload["llm_response"][0]["content"], "full response")
        self.assertEqual(payload["parsed_action"][0]["raw"], "full response")
        self.assertEqual(payload["tool_result"][0]["result"]["content"], "full search result")
        self.assertEqual(payload["final_answer"], "full report")
        self.assertEqual(payload["error"], "full error")

    def test_off_log_does_not_create_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="off",
                log_dir=tmpdir,
                user_input="private input",
                level="off",
            )
            run_logger.record_tool_result(
                tool_name="search",
                input_payload={"query": "private input"},
                result={"content": "private result"},
            )
            run_logger.set_final_answer("private report")

            self.assertFalse(run_logger.enabled)
            self.assertFalse(run_logger.path.exists())

    def test_metadata_log_is_rejected_for_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="metadata",
                log_dir=tmpdir,
                user_input="test",
            )

            with self.assertRaisesRegex(ValueError, "LLM_RUN_LOG_LEVEL=full"):
                load_run_log(run_logger.path, require_replay=True)

    def test_schema_v2_log_is_accepted_for_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy.json"
            path.write_text(
                json.dumps({"schema_version": 2, "llm_response": []}),
                encoding="utf-8",
            )

            payload = load_run_log(path, require_replay=True)

        self.assertEqual(payload["schema_version"], 2)

    def test_write_failure_disables_logging_without_raising(self) -> None:
        with patch.object(Path, "mkdir", side_effect=PermissionError("read only")):
            run_logger = RunLogger(
                run_id="disabled",
                log_dir="unwritable",
                user_input="test",
            )
            run_logger.set_error("still safe")

        self.assertFalse(run_logger.enabled)

    def test_concurrent_updates_keep_valid_complete_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_logger = RunLogger(
                run_id="concurrent",
                log_dir=tmpdir,
                user_input="test",
                level="full",
            )

            def record(index: int) -> None:
                run_logger.record_tool_result(
                    tool_name="search",
                    input_payload={"query": f"query-{index}"},
                    result={"index": index},
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(record, range(40)))

            payload = load_run_log(run_logger.path)

        self.assertEqual(len(payload["tool_result"]), 40)
        self.assertEqual(
            sorted(item["result"]["index"] for item in payload["tool_result"]),
            list(range(40)),
        )


if __name__ == "__main__":
    unittest.main()
