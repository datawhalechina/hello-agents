from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Configuration
from services.llm_resilience import (
    is_rate_limit_error,
    run_with_llm_retry,
    stream_with_llm_retry,
)


class RateLimitError(RuntimeError):
    pass


def retry_config() -> Configuration:
    return Configuration(
        llm_retry_attempts=2,
        llm_retry_base_delay=0,
        llm_retry_max_delay=0,
        llm_min_interval_seconds=0,
    )


class LlmResilienceTests(unittest.TestCase):
    def test_rate_limit_detection(self) -> None:
        self.assertTrue(is_rate_limit_error(RuntimeError("Error code: 429")))
        self.assertTrue(is_rate_limit_error(RuntimeError("您的账户已达到速率限制")))
        self.assertTrue(is_rate_limit_error(RuntimeError("{'code': '1302'}")))
        self.assertFalse(is_rate_limit_error(RuntimeError("connection timeout")))

    def test_run_retries_rate_limit_then_succeeds(self) -> None:
        calls = 0

        def call() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RateLimitError("OpenAI API failed: 429 code 1302")
            return "ok"

        result = run_with_llm_retry(call, retry_config(), operation="test")

        self.assertEqual(result, "ok")
        self.assertEqual(calls, 2)

    def test_run_raises_after_retry_exhausted(self) -> None:
        calls = 0

        def call() -> str:
            nonlocal calls
            calls += 1
            raise RateLimitError("rate limit 429")

        with self.assertRaises(RateLimitError):
            run_with_llm_retry(call, retry_config(), operation="test")

        self.assertEqual(calls, 3)

    def test_stream_retries_before_first_chunk(self) -> None:
        calls = 0

        def stream_factory():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RateLimitError("429 rate limit")
            return iter(["hello", " world"])

        text = "".join(
            stream_with_llm_retry(stream_factory, retry_config(), operation="test stream")
        )

        self.assertEqual(text, "hello world")
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
