"""Bounded regeneration after business validation failures only."""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def validate_with_retry(
    validate: Callable[[], T],
    regenerate: Callable[[ValueError], None],
    agent: str | Callable[[ValueError], str],
    *,
    max_retries: int = 2,
) -> T:
    """Validate, regenerating at most twice by default; generation errors propagate.

    The caller retains current outputs and replaces only the failed agent's output
    in regenerate. Each invocation owns its retry budget. Only ValueError raised
    by validate is retried; regenerate failures immediately leave this module.
    Validation messages and agent names must be safe for CLI display.
    """
    if max_retries < 0:
        raise ValueError("max_retries 不能为负数")
    for attempt in range(max_retries + 1):
        try:
            return validate()
        except ValueError as exc:
            name = agent(exc) if callable(agent) else agent
            if attempt == max_retries:
                raise ValueError(
                    f"{name} 校验失败（{max_retries + 1} 次尝试，"
                    f"重新生成 {max_retries} 次已耗尽）：{exc}"
                ) from exc
            print(
                f"节点 {name} 校验失败，重新执行 {attempt + 1}/{max_retries}",
                flush=True,
            )
            error = exc
        # Keep generation outside the validation exception handler: it is not retryable.
        regenerate(error)
    raise AssertionError("unreachable")
