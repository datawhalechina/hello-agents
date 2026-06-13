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
    def test_sensitive_inputs_are_stored_as_hashes(self) -> None:
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
                response={"content": "safe response", "model": "fake"},
                parsed_action={"action": None, "raw": "safe response"},
            )
            run_logger.record_tool_result(
                tool_name="search",
                input_payload={"query": secret},
                result={"results": []},
            )

            raw_log = run_logger.path.read_text(encoding="utf-8")
            payload = json.loads(raw_log)

        self.assertNotIn(secret, raw_log)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(len(payload["user_input"]["sha256"]), 64)
        self.assertEqual(len(payload["messages"][0]["messages"]["sha256"]), 64)
        self.assertEqual(len(payload["messages"][0]["tools"]["sha256"]), 64)
        self.assertEqual(
            payload["tool_result"][0]["input_hash"],
            payload["tool_result"][0]["input"]["sha256"],
        )

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
