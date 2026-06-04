from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.search_diagnostics import persist_search_diagnostics


class SearchDiagnosticsPersistenceTests(unittest.TestCase):
    def test_persist_search_diagnostics_writes_json_file(self) -> None:
        diagnostics = [
            {
                "task_id": 1,
                "backend": "duckduckgo",
                "query": "Java 后端 实习",
                "counts": {"raw": 2, "reliable": 1, "filtered": 1},
                "rejected_samples": [
                    {
                        "title": "Spring Boot 教程",
                        "url": "https://example.com/blog",
                        "reason": "tutorial_or_blog",
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = persist_search_diagnostics(
                run_id="run_test",
                diagnostics=diagnostics,
                base_dir=Path(tmp),
            )

            self.assertIsNotNone(path)
            payload = json.loads(Path(path or "").read_text(encoding="utf-8"))

        self.assertEqual(payload["run_id"], "run_test")
        self.assertEqual(payload["diagnostics"][0]["task_id"], 1)
        self.assertEqual(payload["diagnostics"][0]["counts"]["reliable"], 1)


if __name__ == "__main__":
    unittest.main()
