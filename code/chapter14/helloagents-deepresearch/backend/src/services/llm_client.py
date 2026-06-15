"""Unified LLM client facade for the internship agent."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from hello_agents import HelloAgentsLLM
from hello_agents.core.llm_response import LLMResponse

from services.agent_parser import parse_agent_output
from services.llm_resilience import get_current_llm_operation
from services.run_log import RunLogger, load_run_log


Message = dict[str, Any]


@dataclass
class LLMClientResponse:
    """Normalized response returned by all local LLM clients."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    reasoning_content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
            "reasoning_content": self.reasoning_content,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LLMClientResponse":
        """Create a normalized response from cached JSON data."""

        return cls(
            content=str(payload.get("content") or ""),
            model=str(payload.get("model") or "unknown"),
            usage=dict(payload.get("usage") or {}),
            latency_ms=int(payload.get("latency_ms") or 0),
            reasoning_content=payload.get("reasoning_content"),
            tool_calls=list(payload.get("tool_calls") or []),
            metadata=dict(payload.get("metadata") or {}),
        )


class BaseLLMClient(ABC):
    """Small local interface every model client must implement."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        """Return a complete response for the given messages."""

    @abstractmethod
    def stream_chat(
        self,
        messages: list[Message],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        """Yield streamed response chunks for the given messages."""


class RealLLMClient(BaseLLMClient):
    """Production LLM client backed by HelloAgentsLLM."""

    def __init__(self, llm: HelloAgentsLLM) -> None:
        self._llm = llm
        self.model = llm.model

    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        if tools:
            raw_response = self._llm.invoke_with_tools(
                messages,
                tools,
                tool_choice=tool_choice,
                **kwargs,
            )
            return _response_from_tool_result(raw_response, model=self.model)

        raw_response = self._llm.invoke(messages, **kwargs)
        return _response_from_invoke_result(raw_response, model=self.model)

    def stream_chat(
        self,
        messages: list[Message],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        yield from self._llm.stream_invoke(messages, **kwargs)


class FakeLLMClient(BaseLLMClient):
    """Deterministic no-network LLM for local development and tests."""

    model = "fake-llm"

    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        return LLMClientResponse(
            content=self._response_for(operation),
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    def stream_chat(
        self,
        messages: list[Message],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        yield self._response_for(operation)

    def _response_for(self, operation: str) -> str:
        operation_text = operation.lower()
        if "planner" in operation_text:
            return (
                '{"tasks": ['
                '{"title": "岗位搜索", "intent": "搜索符合用户画像的实习岗位", '
                '"query": "Java 后端 实习 招聘 校招 投递 官网 BOSS直聘 实习僧"}, '
                '{"title": "JD要求分析", "intent": "分析目标岗位的 JD 和技能要求", '
                '"query": "Java 后端 实习生 招聘 JD 岗位要求 Spring Boot MySQL"}, '
                '{"title": "简历优化建议", "intent": "根据 JD 给出简历和项目优化建议", '
                '"query": "Java 后端实习 简历优化 项目经历 JD匹配"}'
                ']}'
            )
        if "job extraction" in operation_text:
            return (
                '{"jobs": [{'
                '"company": "示例科技", '
                '"title": "Java 后端实习生", '
                '"location": "上海", '
                '"source_url": "https://www.zhipin.com/job_detail/fake.html", '
                '"source_title": "示例科技 Java 后端实习生招聘", '
                '"requirements": ["Spring Boot", "MySQL"], '
                '"responsibilities": ["参与后端接口开发"], '
                '"tech_stack": ["Java", "Redis"], '
                '"duration": "2026 暑期", '
                '"deadline": "未确认", '
                '"match_score": 82, '
                '"match_reason": "城市和技术栈与用户画像匹配", '
                '"resume_advice": ["突出 Spring Boot 项目和接口开发经验"], '
                '"risks": ["截止日期未确认，需点开来源核验"]'
                '}]}'
            )
        if "summarizer" in operation_text:
            return (
                "## 任务总结\n\n"
                "### 关键信息\n\n"
                "- Fake LLM 已基于测试上下文生成岗位线索摘要。\n\n"
                "### 岗位/JD线索\n\n"
                "- 示例科技 Java 后端实习生，需点开来源核验。\n\n"
                "### 投递渠道\n\n"
                "- 优先使用招聘平台或公司官网人工投递。\n\n"
                "### 简历/项目建议\n\n"
                "- 突出 Spring Boot、MySQL、Redis 和项目职责。\n\n"
                "### 下一步建议\n\n"
                "- 打开来源核验岗位状态、城市和截止日期。"
            )
        if "reporter" in operation_text:
            return (
                "# 找实习行动报告\n\n"
                "## 1. 结论：今天优先投递\n\n"
                "1. **Java 后端实习生**（示例科技，上海）\n"
                "- 来源：[示例科技 Java 后端实习生招聘](https://www.zhipin.com/job_detail/fake.html)\n\n"
                "## 2. 推荐理由\n\n"
                "- 技术栈与 Spring Boot、MySQL、Redis 背景匹配。\n\n"
                "## 3. 简历修改清单\n\n"
                "- 强化后端接口、数据库和项目职责描述，不编造经历。\n\n"
                "## 4. 7 天投递计划\n\n"
                "- 今天：打开来源核验并人工投递。\n"
                "- 3 天内：围绕 JD 修改简历。\n"
                "- 7 天内：复盘投递状态并跟进。\n\n"
                "## 5. 风险与待确认项\n\n"
                "- 截止日期、岗位开放状态和城市要求需点开来源确认。\n\n"
                "## 6. 附录：来源与搜索诊断\n\n"
                "- Fake LLM 模式仅用于开发测试，真实投递前必须核验来源。"
            )
        return "Fake LLM response"


class DryRunLLMClient(FakeLLMClient):
    """Dry-run LLM that returns deterministic responses without any network calls."""

    model = "dry-run-llm"

    def _response_for(self, operation: str) -> str:
        response = super()._response_for(operation)
        if "reporter" in operation.lower():
            return response.replace(
                "- Fake LLM 模式仅用于开发测试，真实投递前必须核验来源。",
                "- Dry-run 模式未调用真实模型或搜索，真实投递前必须核验来源。",
            )
        return response


class CachedLLMClient(BaseLLMClient):
    """Local JSON cache wrapper for repeated LLM prompts."""

    def __init__(
        self,
        wrapped: BaseLLMClient,
        cache_dir: str | Path,
        *,
        mode: Literal["read_only", "read_write"] = "read_write",
    ) -> None:
        self._wrapped = wrapped
        self.cache_dir = Path(cache_dir)
        self.mode = mode
        if self.mode == "read_write":
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = getattr(wrapped, "model", "cached-llm")

    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        params = {"tool_choice": tool_choice, **kwargs} if tools else dict(kwargs)
        request_hash = build_request_hash(
            messages,
            tools=tools,
            operation=operation,
            params=params,
            stream=False,
        )
        cached = self._read_cached(request_hash)
        if cached:
            cached.metadata.update({"cache_hit": True, "request_hash": request_hash})
            return cached

        response = self._wrapped.chat(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            operation=operation,
            **kwargs,
        )
        response.metadata.update({"cache_hit": False, "request_hash": request_hash})
        if self.mode == "read_write":
            self._write_cached(request_hash, response)
        return response

    def stream_chat(
        self,
        messages: list[Message],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        request_hash = build_request_hash(
            messages,
            tools=None,
            operation=operation,
            params=kwargs,
            stream=True,
        )
        cached = self._read_cached(request_hash)
        if cached:
            yield cached.content
            return

        chunks: list[str] = []
        for chunk in self._wrapped.stream_chat(messages, operation=operation, **kwargs):
            chunks.append(chunk)
            yield chunk

        response = LLMClientResponse(
            content="".join(chunks),
            model=str(getattr(self._wrapped, "model", self.model)),
            metadata={"cache_hit": False, "request_hash": request_hash},
        )
        if self.mode == "read_write":
            self._write_cached(request_hash, response)

    def _read_cached(self, request_hash: str) -> LLMClientResponse | None:
        path = self.cache_dir / f"{request_hash}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return LLMClientResponse.from_dict(payload)

    def _write_cached(self, request_hash: str, response: LLMClientResponse) -> None:
        path = self.cache_dir / f"{request_hash}.json"
        path.write_text(
            json.dumps(response.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ReplayLLMClient(BaseLLMClient):
    """LLM client that replays responses from a previous run log."""

    model = "replay-llm"

    def __init__(self, log_path: str | Path, *, strict: bool = True) -> None:
        if not log_path:
            raise ValueError("LLM_REPLAY_LOG is required when LLM_MODE=replay")
        payload = load_run_log(log_path, require_replay=True)
        self._responses = list(payload.get("llm_response") or [])
        self._cursor = 0
        self.strict = strict

    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        operation: str = "llm",
        **kwargs: Any,
    ) -> LLMClientResponse:
        params = {"tool_choice": tool_choice, **kwargs} if tools else dict(kwargs)
        request_hash = build_request_hash(
            messages,
            tools=tools,
            operation=operation,
            params=params,
            stream=False,
        )
        return self._next_response(operation=operation, request_hash=request_hash)

    def stream_chat(
        self,
        messages: list[Message],
        *,
        operation: str = "llm",
        **kwargs: Any,
    ) -> Iterator[str]:
        request_hash = build_request_hash(
            messages,
            tools=None,
            operation=operation,
            params=kwargs,
            stream=True,
        )
        response = self._next_response(operation=operation, request_hash=request_hash)
        yield response.content

    def _next_response(self, *, operation: str, request_hash: str) -> LLMClientResponse:
        if self._cursor >= len(self._responses):
            raise RuntimeError("Replay log has no remaining LLM responses")

        payload = self._responses[self._cursor]
        self._cursor += 1
        expected_hash = payload.get("request_hash")
        if self.strict and expected_hash and expected_hash != request_hash:
            raise RuntimeError(
                f"Replay request hash mismatch for {operation}: "
                f"expected {expected_hash}, got {request_hash}"
            )

        response = LLMClientResponse.from_dict(payload)
        response.metadata.update({"replay": True, "request_hash": request_hash})
        return response


class HelloAgentsCompatibleLLM:
    """Adapter exposing the methods expected by hello_agents.SimpleAgent."""

    def __init__(
        self,
        client: BaseLLMClient,
        *,
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.last_call_stats = None
        self._run_logger: RunLogger | None = None

    def set_run_logger(self, run_logger: RunLogger | None) -> None:
        """Attach the per-run JSON logger."""

        self._run_logger = run_logger

    def invoke(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        call_kwargs = self._call_kwargs(kwargs)
        result = self.client.chat(messages, **call_kwargs)
        self._record_llm_call(
            messages=messages,
            tools=None,
            result=result,
            params={k: v for k, v in call_kwargs.items() if k != "operation"},
            stream=False,
        )
        return LLMResponse(
            content=result.content,
            model=result.model or self.model,
            usage=result.usage,
            latency_ms=result.latency_ms,
            reasoning_content=result.reasoning_content,
        )

    def stream_invoke(self, messages: list[Message], **kwargs: Any) -> Iterator[str]:
        call_kwargs = self._call_kwargs(kwargs)
        chunks: list[str] = []
        for chunk in self.client.stream_chat(messages, **call_kwargs):
            chunks.append(chunk)
            yield chunk
        result = LLMClientResponse(
            content="".join(chunks),
            model=self.model,
            metadata={"stream": True},
        )
        self._record_llm_call(
            messages=messages,
            tools=None,
            result=result,
            params={k: v for k, v in call_kwargs.items() if k != "operation"},
            stream=True,
        )

    def invoke_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        tool_choice: str | dict[str, Any] = "auto",
        **kwargs: Any,
    ) -> Any:
        call_kwargs = self._call_kwargs(kwargs)
        result = self.client.chat(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            **call_kwargs,
        )
        self._record_llm_call(
            messages=messages,
            tools=tools,
            result=result,
            params={
                "tool_choice": tool_choice,
                **{k: v for k, v in call_kwargs.items() if k != "operation"},
            },
            stream=False,
        )
        return _to_tool_response(result)

    def _call_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        call_kwargs = dict(kwargs)
        call_kwargs.setdefault("operation", get_current_llm_operation())
        call_kwargs.setdefault("temperature", self.temperature)
        if self.max_tokens is not None:
            call_kwargs.setdefault("max_tokens", self.max_tokens)
        return call_kwargs

    def _record_llm_call(
        self,
        *,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        result: LLMClientResponse,
        params: dict[str, Any],
        stream: bool,
    ) -> None:
        if not self._run_logger:
            return

        operation = get_current_llm_operation()
        request_hash = str(
            result.metadata.get("request_hash")
            or build_request_hash(
                messages,
                tools=tools,
                operation=operation,
                params=params,
                stream=stream,
            )
        )
        self._run_logger.record_llm(
            operation=operation,
            request_hash=request_hash,
            messages=messages,
            tools=tools,
            response=result.to_dict(),
            parsed_action=parse_agent_output(result.content),
        )


def _response_from_invoke_result(raw_response: Any, *, model: str) -> LLMClientResponse:
    content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
    usage = _usage_to_dict(getattr(raw_response, "usage", {}))
    latency_ms = int(getattr(raw_response, "latency_ms", 0) or 0)
    reasoning_content = getattr(raw_response, "reasoning_content", None)
    raw_model = str(getattr(raw_response, "model", model) or model)
    return LLMClientResponse(
        content=content,
        model=raw_model,
        usage=usage,
        latency_ms=latency_ms,
        reasoning_content=reasoning_content,
    )


def _response_from_tool_result(raw_response: Any, *, model: str) -> LLMClientResponse:
    choice = _first_choice(raw_response)
    message = getattr(choice, "message", None)
    if isinstance(choice, dict):
        message = choice.get("message")

    content = _get_value(message, "content") or ""
    tool_calls = [_normalize_tool_call(item) for item in (_get_value(message, "tool_calls") or [])]
    usage = _usage_to_dict(getattr(raw_response, "usage", {}))
    return LLMClientResponse(
        content=str(content),
        model=str(getattr(raw_response, "model", model) or model),
        usage=usage,
        tool_calls=[item for item in tool_calls if item],
    )


def _to_tool_response(result: LLMClientResponse) -> Any:
    message = SimpleNamespace(
        content=result.content,
        tool_calls=[_tool_call_namespace(item) for item in result.tool_calls],
    )
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(
        choices=[choice],
        usage=SimpleNamespace(
            prompt_tokens=result.usage.get("prompt_tokens", 0),
            completion_tokens=result.usage.get("completion_tokens", 0),
            total_tokens=result.usage.get("total_tokens", 0),
        ),
    )


def _tool_call_namespace(tool_call: dict[str, Any]) -> Any:
    function = tool_call.get("function") or {}
    return SimpleNamespace(
        id=tool_call.get("id") or "call_0",
        type=tool_call.get("type") or "function",
        function=SimpleNamespace(
            name=function.get("name") or "",
            arguments=function.get("arguments") or "{}",
        ),
    )


def _normalize_tool_call(raw_tool_call: Any) -> dict[str, Any]:
    function = _get_value(raw_tool_call, "function") or {}
    return {
        "id": _get_value(raw_tool_call, "id") or "call_0",
        "type": _get_value(raw_tool_call, "type") or "function",
        "function": {
            "name": _get_value(function, "name") or "",
            "arguments": _get_value(function, "arguments") or "{}",
        },
    }


def _first_choice(raw_response: Any) -> Any:
    choices = getattr(raw_response, "choices", None)
    if choices is None and isinstance(raw_response, dict):
        choices = raw_response.get("choices")
    if choices:
        return choices[0]
    return {}


def _get_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _usage_to_dict(usage: Any) -> dict[str, int]:
    if isinstance(usage, dict):
        return {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def build_request_hash(
    messages: list[Message],
    *,
    tools: list[dict[str, Any]] | None,
    operation: str,
    params: dict[str, Any],
    stream: bool,
) -> str:
    """Build a stable cache/replay key for an LLM request."""

    material = {
        "messages": messages,
        "tools": tools or [],
        "operation": operation,
        "params": params,
        "stream": stream,
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
