"""统一 LLM 接入：Ollama 与在线 OpenAI 兼容 API 共用一套配置。"""

from __future__ import annotations

import logging
from typing import Any

from hello_agents import HelloAgentsLLM

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import trace_service

logger = logging.getLogger(__name__)


class TracingHelloAgentsLLM(HelloAgentsLLM):
    """在每轮模型输出后记录推理说明与工具决策，补齐 ReAct 思考链路。"""

    def invoke_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_choice: str | dict = "auto",
        **kwargs: Any,
    ) -> Any:
        response = super().invoke_with_tools(messages, tools, tool_choice, **kwargs)
        trace_id = trace_service.current_trace_id.get()
        if not trace_id or not settings.trace_enabled:
            return response
        try:
            message = response.choices[0].message
            tool_calls = [
                {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                }
                for call in (message.tool_calls or [])
            ]
            parts = []
            content = (message.content or "").strip()
            if content:
                parts.append(f"模型说明：{content}")
            decision = ", ".join(item["name"] for item in tool_calls) or "直接回复"
            parts.append(f"工具决策：{decision}")
            with SessionLocal() as db:
                trace_service.add_step(
                    db,
                    trace_id,
                    "thought",
                    thought="\n".join(parts),
                    tool_input={"tool_calls": tool_calls} if tool_calls else None,
                )
                db.commit()
        except Exception:
            logger.warning("记录模型思考步骤失败", exc_info=True)
        return response


def build_llm() -> HelloAgentsLLM:
    """按 .env 配置构造 LLM，业务代码不感知具体服务商。"""
    return TracingHelloAgentsLLM(
        model=settings.llm_model_id,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )
