"""Lightweight resilience helpers for LLM rate limits."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from config import Configuration

logger = logging.getLogger(__name__)

T = TypeVar("T")

RATE_LIMIT_MARKERS = (
    "429",
    "rate limit",
    "速率限制",
    "code 1302",
    "code': '1302",
    'code": "1302',
)

# Process-local throttling is intentional for the local single-user app: it
# reduces 429s across planner/summarizer/reporter calls. For multi-user
# deployment, split this by provider/base_url/api key.
_THROTTLE_LOCK = threading.Lock()
_LAST_LLM_CALL_AT = 0.0


def is_rate_limit_error(exc: BaseException) -> bool:
    """Return True when an exception looks like an LLM provider rate limit."""

    message = f"{exc} {repr(exc)}".lower()
    return any(marker.lower() in message for marker in RATE_LIMIT_MARKERS)


def run_with_llm_retry(
    call: Callable[[], T],
    config: Configuration,
    *,
    operation: str = "llm call",
) -> T:
    """Run a non-streaming LLM call with narrow 429 retry handling."""

    attempts = max(0, int(config.llm_retry_attempts))

    for attempt_index in range(attempts + 1):
        try:
            _respect_min_interval(config)
            return call()
        except Exception as exc:
            if not is_rate_limit_error(exc) or attempt_index >= attempts:
                raise

            delay = _retry_delay(config, attempt_index + 1)
            logger.warning(
                "%s hit LLM rate limit; retrying in %.1fs (%d/%d)",
                operation,
                delay,
                attempt_index + 1,
                attempts,
            )
            _sleep(delay)

    raise RuntimeError("unreachable llm retry state")


def stream_with_llm_retry(
    stream_factory: Callable[[], Iterator[str]],
    config: Configuration,
    *,
    operation: str = "llm stream",
) -> Iterator[str]:
    """Yield a streaming LLM response, retrying 429s before any chunk is emitted."""

    attempts = max(0, int(config.llm_retry_attempts))

    for attempt_index in range(attempts + 1):
        emitted_any = False
        try:
            _respect_min_interval(config)
            for chunk in stream_factory():
                emitted_any = True
                yield chunk
            return
        except Exception as exc:
            if (
                emitted_any
                or not is_rate_limit_error(exc)
                or attempt_index >= attempts
            ):
                raise

            delay = _retry_delay(config, attempt_index + 1)
            logger.warning(
                "%s hit LLM rate limit before streaming; retrying in %.1fs (%d/%d)",
                operation,
                delay,
                attempt_index + 1,
                attempts,
            )
            _sleep(delay)


def _respect_min_interval(config: Configuration) -> None:
    """Apply a simple process-local interval between LLM calls."""

    interval = max(0.0, float(config.llm_min_interval_seconds))
    if interval <= 0:
        return

    global _LAST_LLM_CALL_AT
    with _THROTTLE_LOCK:
        now = time.monotonic()
        wait_for = interval - (now - _LAST_LLM_CALL_AT)
        if wait_for > 0:
            _sleep(wait_for)
        _LAST_LLM_CALL_AT = time.monotonic()


def _retry_delay(config: Configuration, retry_number: int) -> float:
    base_delay = max(0.0, float(config.llm_retry_base_delay))
    max_delay = max(0.0, float(config.llm_retry_max_delay))
    delay = base_delay * max(1, retry_number)
    return min(delay, max_delay) if max_delay > 0 else delay


def _sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
