"""DeepSeek LLM 客户端：基于 HelloAgents 框架的 HelloAgentsLLM 实现

PaperMind 的多 Agent 编排构建在 HelloAgents 框架之上：
- LLM 调用统一走框架的 HelloAgentsLLM（OpenAI 兼容适配器，自动适配 DeepSeek）
- chat() 返回与 OpenAI SDK ChatCompletion 兼容的对象，ToolLoop 等既有调用方无需改动
"""
import asyncio
import logging
from typing import Any, Optional

from hello_agents import HelloAgentsLLM

from backend.config import settings

logger = logging.getLogger(__name__)


class _ShimMessage:
    """把 HelloAgentsLLM 的文本响应包装为 OpenAI ChatCompletion.message 形状"""

    def __init__(self, content: str, reasoning_content: Optional[str] = None) -> None:
        self.role = "assistant"
        self.content = content
        self.reasoning_content = reasoning_content
        self.tool_calls = None


class _ShimChoice:
    def __init__(self, message: _ShimMessage) -> None:
        self.message = message
        self.finish_reason = "stop"
        self.index = 0


class ChatCompletionShim:
    """无工具调用的文本响应适配：兼容 response.choices[0].message.content 访问方式"""

    def __init__(self, llm_response: Any) -> None:
        self.choices = [
            _ShimChoice(
                _ShimMessage(
                    content=getattr(llm_response, "content", "") or "",
                    reasoning_content=getattr(llm_response, "reasoning_content", None),
                )
            )
        ]
        self.model = getattr(llm_response, "model", settings.DEEPSEEK_MODEL)
        self.usage = getattr(llm_response, "usage", None)
        self.id = "papermind-hello-agents"


class DeepSeekClient:
    """DeepSeek 异步客户端：底层由 HelloAgents 框架的 HelloAgentsLLM 驱动

    HelloAgentsLLM 基于 OpenAI 兼容适配器访问 DeepSeek，
    chat() 对外保持与 OpenAI SDK ChatCompletion 兼容的返回形状。
    """

    def __init__(self) -> None:
        # 框架 LLM：模型/密钥/地址来自项目配置，适配器自动识别 DeepSeek
        self.llm = HelloAgentsLLM(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
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
        """调用 Chat Completions，返回模型回复（ChatCompletion 兼容对象）

        有工具时走框架 ainvoke_with_tools（返回原生 ChatCompletion）；
        无工具时走框架 ainvoke，包装为兼容形状。
        单次调用失败时按指数退避重试 max_retries 次。
        max_tokens: 显式设置输出 token 上限，None 用 API 默认值（4096）。
        """
        kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        last_exc: Optional[Exception] = None
        total_attempts = self.max_retries + 1  # 初次调用 + 重试次数
        for attempt in range(total_attempts):
            try:
                if tools:
                    # Function Calling：框架返回原生 ChatCompletion（含 tool_calls）
                    response = await self.llm.ainvoke_with_tools(
                        messages=messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        **kwargs,
                    )
                    return response

                # 纯文本：框架返回 LLMResponse，包装为 ChatCompletion 兼容形状
                response = await self.llm.ainvoke(messages=messages, **kwargs)
                return ChatCompletionShim(response)
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
