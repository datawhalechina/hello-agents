"""LLM 调用辅助：指数退避重试与错误分类。"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from hello_agents import HelloAgentsLLM

from .errors import LLMCallError
from .logging_utils import get_logger

logger = get_logger("llm")


def invoke_with_retry(
    llm: HelloAgentsLLM,
    messages: Sequence[dict[str, str]],
    *,
    temperature: float | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    sleep_func: Callable[[float], None] = time.sleep,
) -> Any:
    """带指数退避的同步 LLM 调用（最多 1 次初始调用 + 2 次重试）。

    Args:
        llm: ``HelloAgentsLLM`` 实例。
        messages: OpenAI 格式消息列表。
        temperature: 采样温度；为 None 时使用实例默认值。
        max_attempts: 最大尝试次数，默认 3（即重试 2 次）。
        base_delay: 首次重试等待秒数，之后按 2 倍递增（1s、2s）。
        sleep_func: 休眠函数，便于测试注入。

    Returns:
        ``LLMResponse`` 对象（含 content / usage / latency_ms）。

    Raises:
        LLMCallError: 所有尝试均失败时抛出，保留最后一次错误信息。
    """
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            kwargs = {"temperature": temperature} if temperature is not None else {}
            return llm.invoke(list(messages), **kwargs)
        except Exception as exc:  # noqa: BLE001 - 上游异常类型多样，统一包装
            last_error = exc
            if attempt >= max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "LLM 调用失败（第 %s/%s 次），%.1fs 后重试：%s",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            sleep_func(delay)

    raise LLMCallError(f"LLM 调用失败（已重试 {max_attempts - 1} 次）：{last_error}") from last_error


def is_timeout_error(exc: BaseException) -> bool:
    """判断异常是否属于超时。"""
    text = f"{type(exc).__name__} {exc}".lower()
    return "timeout" in text or "timed out" in text


def is_rate_limit_error(exc: BaseException) -> bool:
    """判断异常是否属于上游限流。"""
    text = f"{type(exc).__name__} {exc}".lower()
    return "rate limit" in text or "429" in text or "too many requests" in text
