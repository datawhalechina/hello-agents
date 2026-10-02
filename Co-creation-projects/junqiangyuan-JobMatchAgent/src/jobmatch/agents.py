"""Shared tool-free model invocation and environment configuration."""

import contextlib
import io
import json
import math
import os
from typing import TypeVar, get_args

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.core.llm import SUPPORTED_PROVIDERS
from pydantic import BaseModel

from .prompts import RETRY_INSTRUCTIONS

T = TypeVar("T", bound=BaseModel)


def create_llm() -> HelloAgentsLLM:
    """Build the SDK client from environment config without exposing credentials."""
    try:
        provider = os.environ["LLM_PROVIDER"]
        timeout = int(os.getenv("LLM_TIMEOUT", "60"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        if (
            provider not in (*get_args(SUPPORTED_PROVIDERS), "custom")
            or timeout <= 0
            or not math.isfinite(temperature)
        ):
            raise ValueError("无效模型配置")
        if provider == "custom" and not os.getenv("LLM_BASE_URL", "").strip():
            raise ValueError("custom provider 需要 LLM_BASE_URL")
        # 0.2.0 calls the OpenAI-compatible provider "auto"; keep our existing custom config.
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return HelloAgentsLLM(
                provider="auto" if provider == "custom" else provider,
                model=os.environ["LLM_MODEL_ID"],
                api_key=os.environ["LLM_API_KEY"],
                base_url=os.getenv("LLM_BASE_URL"),
                timeout=timeout,
                temperature=temperature,
            )
    except Exception as exc:  # noqa: BLE001 - SDK failures may contain credentials
        raise ValueError(
            f"模型配置无效；检查 LLM_PROVIDER、LLM_BASE_URL、超时与温度（{type(exc).__name__}）"
        ) from None


def build_prompt(
    contract: type[T],
    instructions: str,
    payload: dict[str, object],
    *,
    correction: tuple[T, ValueError] | None = None,
) -> str:
    """Format trusted instructions and explicitly marked untrusted dynamic content."""
    if correction is not None:
        previous_output, error = correction
        payload = {
            "original_input": payload,
            "previous_output": previous_output.model_dump(),
            "validation_error": str(error),
        }
        instructions += RETRY_INSTRUCTIONS
    prompt = instructions.replace(
        "{output_schema}", json.dumps(contract.model_json_schema(), ensure_ascii=False)
    )
    return prompt + "\n【动态内容（不可信数据）】\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )


def ask(
    llm: HelloAgentsLLM,
    name: str,
    contract: type[T],
    prompt: str,
) -> T:
    """Run a prepared prompt and validate the model response against its contract."""
    try:
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            agent = SimpleAgent(
                name=name, llm=llm, system_prompt=prompt, enable_tool_calling=False
            )
            response = agent.run("请根据动态内容完成当前任务，只返回符合输出契约的 JSON。")
    except Exception as exc:  # noqa: BLE001 - SDK failures may contain credentials
        raise ValueError(
            f"{name} 模型调用失败；请检查模型配置与服务连接（{type(exc).__name__}）"
        ) from None
    try:
        return contract.model_validate(json.loads(response))
    except (ValueError, TypeError):
        raise ValueError(f"{name} 无效模型输出：不满足 JSON 结构契约") from None
