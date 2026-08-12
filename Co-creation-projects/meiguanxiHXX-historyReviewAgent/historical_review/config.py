"""LLM 配置：OpenRouter（OpenAI 兼容）。"""

from __future__ import annotations

import os

from hello_agents import HelloAgentsLLM


def create_llm(
    *,
    temperature: float = 0.4,
    max_tokens: int | None = 4096,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
) -> HelloAgentsLLM:
    """
    OpenRouter：
        OPENROUTER_API_KEY / OPENROUTER_BASE_URL / OPENROUTER_MODEL
    或通用 LLM_* 变量。

    传入的 api_key / base_url / model / timeout 优先于环境变量（供 Web 等场景覆盖）。
    """
    resolved_key = (
        (api_key.strip() if api_key else None)
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("LLM_API_KEY")
    )
    resolved_base = (
        (base_url.strip() if base_url else None)
        or os.getenv("OPENROUTER_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or "https://openrouter.ai/api/v1"
    )
    resolved_model = (
        (model.strip() if model else None)
        or os.getenv("OPENROUTER_MODEL")
        or os.getenv("LLM_MODEL_ID")
        or "openai/gpt-4o-mini"
    )
    kwargs: dict = {
        "provider": "custom",
        "api_key": resolved_key,
        "base_url": resolved_base,
        "model": resolved_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if timeout is not None:
        kwargs["timeout"] = int(timeout)

    return HelloAgentsLLM(**kwargs)
