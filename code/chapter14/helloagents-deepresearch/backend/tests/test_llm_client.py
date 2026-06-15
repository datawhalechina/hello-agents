from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.llm_client import (
    BaseLLMClient,
    CachedLLMClient,
    LLMClientResponse,
    ReplayLLMClient,
)


class CountingLLMClient(BaseLLMClient):
    model = "counting"

    def __init__(self) -> None:
        self.calls = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        self.calls += 1
        return LLMClientResponse(
            content=f"response {self.calls}",
            model=self.model,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        self.calls += 1
        yield f"stream {self.calls}"


class CachedLLMClientTests(unittest.TestCase):
    def test_same_prompt_hits_cache_after_first_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapped = CountingLLMClient()
            client = CachedLLMClient(wrapped, tmpdir)
            messages = [{"role": "user", "content": "hello"}]

            first = client.chat(messages, operation="unit-test")
            second = client.chat(messages, operation="unit-test")

            self.assertEqual(first.content, "response 1")
            self.assertEqual(second.content, "response 1")
            self.assertEqual(wrapped.calls, 1)
            self.assertFalse(first.metadata["cache_hit"])
            self.assertTrue(second.metadata["cache_hit"])
            self.assertEqual(len(list(Path(tmpdir).glob("*.json"))), 1)

    def test_different_operation_uses_different_cache_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapped = CountingLLMClient()
            client = CachedLLMClient(wrapped, tmpdir)
            messages = [{"role": "user", "content": "hello"}]

            client.chat(messages, operation="planner")
            client.chat(messages, operation="reporter")

            self.assertEqual(wrapped.calls, 2)
            self.assertEqual(len(list(Path(tmpdir).glob("*.json"))), 2)

    def test_read_only_cache_hit_reuses_existing_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages = [{"role": "user", "content": "private prompt"}]
            writer = CountingLLMClient()
            CachedLLMClient(writer, tmpdir).chat(messages, operation="unit-test")
            reader = CountingLLMClient()

            response = CachedLLMClient(
                reader,
                tmpdir,
                mode="read_only",
            ).chat(messages, operation="unit-test")

            self.assertEqual(response.content, "response 1")
            self.assertEqual(reader.calls, 0)
            self.assertTrue(response.metadata["cache_hit"])

    def test_read_only_cache_miss_does_not_create_directory_or_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "missing-cache"
            wrapped = CountingLLMClient()
            client = CachedLLMClient(wrapped, cache_dir, mode="read_only")

            response = client.chat(
                [{"role": "user", "content": "private prompt"}],
                operation="unit-test",
            )

            self.assertEqual(response.content, "response 1")
            self.assertEqual(wrapped.calls, 1)
            self.assertFalse(response.metadata["cache_hit"])
            self.assertFalse(cache_dir.exists())

    def test_read_write_cache_persists_full_response_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = CachedLLMClient(CountingLLMClient(), tmpdir)

            client.chat(
                [{"role": "user", "content": "private prompt"}],
                operation="unit-test",
            )

            cache_path = next(Path(tmpdir).glob("*.json"))
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["content"], "response 1")

    def test_schema_v2_log_remains_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy-run.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "llm_response": [
                            {
                                "content": "legacy response",
                                "model": "legacy-model",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = ReplayLLMClient(path, strict=False)

            response = client.chat(
                [{"role": "user", "content": "not persisted"}],
                operation="legacy-test",
            )

        self.assertEqual(response.content, "legacy response")
        self.assertEqual(response.model, "legacy-model")
        self.assertTrue(response.metadata["replay"])


if __name__ == "__main__":
    unittest.main()
