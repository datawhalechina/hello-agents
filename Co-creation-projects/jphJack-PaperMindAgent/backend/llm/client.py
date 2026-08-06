"""DeepSeek LLM 客户端：基于 OpenAI 兼容接口（DeepSeek 兼容 OpenAI API）"""
import asyncio
import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek 异步客户端，封装 OpenAI 兼容的 Chat Completions 接口"""

    def __init__(self) -> None:
        # DeepSeek 兼容 OpenAI API，直接复用 AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        self.model = settings.DEEPSEEK_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self.max_retries = settings.TOOL_MAX_RETRIES

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
    ) -> Any:
        """调用 Chat Completions，返回模型回复（ChatCompletion 对象）

        单次调用失败时按指数退避重试 max_retries 次。
        max_tokens: 显式设置输出 token 上限，None 用 API 默认值（4096）。
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        last_exc: Optional[Exception] = None
        total_attempts = self.max_retries + 1  # 初次调用 + 重试次数
        for attempt in range(total_attempts):
            try:
                # 显式超时控制，确保单次调用不会无限挂起
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=self.timeout,
                )
                return response
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "DeepSeek 调用失败 (attempt=%d/%d): %s",
                    attempt + 1,
                    total_attempts,
                    exc,
                )
                if attempt < self.max_retries:
                    # 指数退避：1s, 2s, 4s ...
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)

        raise RuntimeError(
            f"DeepSeek 调用失败，已重试 {self.max_retries} 次"
        ) from last_exc
