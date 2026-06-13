from __future__ import annotations

import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.llm_client import BaseLLMClient, CachedLLMClient, LLMClientResponse


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


if __name__ == "__main__":
    unittest.main()
