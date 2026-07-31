from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Protocol

from finance_agent.llm_strategies import resolve_response_format_strategy
from finance_agent.report_constants import PROJECT_ROOT

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - handled at runtime with a clear error.
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime with a clear error.
    OpenAI = None


class LLMClient(Protocol):
    def generate(self, agent_name: str, system_prompt: str, input_json: dict[str, Any], output_format: str) -> str:
        ...


class HelloAgentsLLM:
    """
    OpenAI-compatible LLM client for the finance-agent pipeline.

    It follows the common SDK pattern: load .env, pass api_key/base_url to the
    OpenAI client, and call chat.completions.create().
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        load_project_env()
        if OpenAI is None:
            raise RuntimeError("Missing dependency: install openai with `python -m pip install -r requirements.txt`.")

        self.model = model or os.getenv("LLM_MODEL_ID")
        api_key = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        provider = os.getenv("LLM_PROVIDER")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        max_retries = max_retries if max_retries is not None else int(os.getenv("LLM_SDK_MAX_RETRIES", "0"))
        self.json_response_format = os.getenv("LLM_JSON_RESPONSE_FORMAT", "json_schema").lower()
        self.response_format_strategy = resolve_response_format_strategy(provider, self.model, base_url)
        self.max_attempts = max(1, int(os.getenv("LLM_MAX_ATTEMPTS", "3")))
        self.retry_base_delay = max(0.0, float(os.getenv("LLM_RETRY_BASE_DELAY", "2")))
        self.retry_max_delay = max(self.retry_base_delay, float(os.getenv("LLM_RETRY_MAX_DELAY", "8")))
        self.retry_jitter = max(0.0, float(os.getenv("LLM_RETRY_JITTER", "0.5")))

        if not api_key:
            raise RuntimeError("Missing LLM API key. Set LLM_API_KEY or OPENAI_API_KEY, or run with --mock-llm for local testing.")
        if api_key in {"your_api_key", "your_api_key_here", "sk-your_api_key_here"}:
            raise RuntimeError("The .env file still contains a placeholder API key. Replace LLM_API_KEY with your real key.")
        if not base_url:
            raise RuntimeError("Missing LLM base URL. Set LLM_BASE_URL in .env.")

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)

    def generate(self, agent_name: str, system_prompt: str, input_json: dict[str, Any], output_format: str) -> str:
        user_content = json.dumps(input_json, ensure_ascii=False, indent=2)
        messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        try:
            request_kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "stream": True,
            }
            if output_format == "json":
                response_formats = self._json_response_formats(agent_name, input_json)
            else:
                response_formats = [None]
            return self._create_chat_completion(request_kwargs, agent_name, response_formats)
        except Exception as exc:
            raise RuntimeError(f"{agent_name} LLM call failed: {exc}") from exc

    def _create_chat_completion(
        self,
        request_kwargs: dict[str, Any],
        agent_name: str,
        response_formats: list[dict[str, Any] | None],
    ) -> str:
        last_error: Exception | None = None
        for response_format in response_formats:
            if response_format is None:
                request_kwargs.pop("response_format", None)
            else:
                request_kwargs["response_format"] = response_format
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = self.client.chat.completions.create(**request_kwargs)
                    chunks: list[str] = []
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content or ""
                        chunks.append(content)
                    return "".join(chunks)
                except Exception as exc:
                    last_error = exc
                    if self.response_format_strategy.should_fallback_response_format(exc):
                        print(
                            f"[llm] {agent_name} strategy={self.response_format_strategy.name} "
                            f"response_format={response_format_name(response_format)} unavailable; trying fallback.",
                            flush=True,
                        )
                        break
                    if not is_retryable_llm_error(exc) or attempt >= self.max_attempts:
                        raise
                    delay = self._retry_delay(attempt)
                    print(
                        f"[llm] {agent_name} transient LLM error on attempt {attempt}/{self.max_attempts}: "
                        f"{type(exc).__name__} - {short_error(exc)}. Retrying in {delay:.2f}s.",
                        flush=True,
                    )
                    time.sleep(delay)
            else:
                continue
            if last_error is not None and not self.response_format_strategy.should_fallback_response_format(last_error):
                raise last_error
        raise last_error or RuntimeError(f"{agent_name} LLM call failed without an error detail.")

    def _retry_delay(self, failed_attempt: int) -> float:
        delay = min(self.retry_base_delay * (2 ** (failed_attempt - 1)), self.retry_max_delay)
        if self.retry_jitter:
            delay += random.uniform(-self.retry_jitter, self.retry_jitter)
        return max(0.0, delay)

    def _json_response_formats(self, agent_name: str, input_json: dict[str, Any]) -> list[dict[str, Any] | None]:
        return self.response_format_strategy.json_response_formats(
            agent_name=agent_name,
            input_json=input_json,
            configured_format=self.json_response_format,
            schema=build_agent_output_schema(input_json),
        )


def build_agent_output_schema(input_json: dict[str, Any]) -> dict[str, Any]:
    contract = input_json.get("output_contract", {})
    required_keys = contract.get("required_top_level_keys") if isinstance(contract, dict) else None
    required = [key for key in required_keys or ["agent", "status"] if isinstance(key, str)]
    properties: dict[str, Any] = {
        "agent": {"type": "string"},
        "status": {"type": "string"},
        "narrative": {"type": "string"},
        "key_findings": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ]
        },
        "preparation_focus": {"type": "string"},
        "next_input": {"type": "object", "additionalProperties": True},
        "data": {"type": "object", "additionalProperties": True},
    }
    for key in required:
        properties.setdefault(key, {})
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": True,
    }


def is_retryable_llm_error(exc: Exception) -> bool:
    status_code = error_status_code(exc)
    if status_code is not None:
        if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
            return True
        if 400 <= status_code < 500:
            return False

    message = str(exc).lower()
    non_retryable_markers = [
        "api key",
        "authentication",
        "unauthorized",
        "forbidden",
        "insufficient quota",
        "billing",
        "model not found",
        "invalid_request",
        "invalid parameter",
        "unsupported",
        "response_format",
    ]
    if any(marker in message for marker in non_retryable_markers):
        return False

    retryable_markers = [
        "connection",
        "connecterror",
        "connectionerror",
        "timeout",
        "timed out",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "connection reset",
        "connection aborted",
        "read error",
        "network",
        "winerror 10061",
    ]
    return any(marker in message for marker in retryable_markers)


def error_status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None


def short_error(exc: Exception, limit: int = 180) -> str:
    message = str(exc).replace("\n", " ").strip()
    if len(message) <= limit:
        return message
    return f"{message[:limit]}..."


def response_format_name(response_format: dict[str, Any] | None) -> str:
    if response_format is None:
        return "none"
    return str(response_format.get("type", "unknown"))


OpenAICompatibleLLMClient = HelloAgentsLLM


def load_project_env(env_path: Path | None = None) -> None:
    if load_dotenv is None:
        raise RuntimeError("Missing dependency: install python-dotenv with `python -m pip install -r requirements.txt`.")

    candidates = [env_path] if env_path else [PROJECT_ROOT / ".env", Path.cwd() / ".env"]
    for candidate in candidates:
        if candidate and candidate.exists():
            load_dotenv(candidate, override=False)


class MockLLMClient:
    """Test-only client so the pipeline can be verified without network credentials."""

    def generate(self, agent_name: str, system_prompt: str, input_json: dict[str, Any], output_format: str) -> str:
        if output_format == "markdown":
            return input_json.get("draft_report", "# Mock Report\n\nNo draft_report provided.")
        payload = {
            "agent": agent_name,
            "status": "mocked",
            "narrative": input_json.get("deterministic_narrative", "本节点已基于确定性计算结果生成说明。"),
            "data": input_json.get("calculated_data", {}),
            "next_input": input_json.get("next_input", input_json.get("calculated_data", {})),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
