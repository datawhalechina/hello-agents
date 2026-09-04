"""Unified Anthropic Messages API calls, prompt caching, and usage metrics."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import (
    CACHE_READ_COST_MULTIPLIER, INPUT_COST_PER_MILLION,
    PROMPT_CACHE_ENABLED, PROMPT_CACHE_TTL,
    TOKEN_USAGE_DIR, TRACE_FULL_PAYLOAD, client,
)
from .hooks import _coerce_input_value

CACHE_POLICY_VERSION = "v1"
_CACHE_STATE_LOCK = threading.Lock()
_CACHE_SUPPORTED: bool | None = None
_CACHE_TTL_SUPPORTED: bool | None = None
_USAGE_LOCK = threading.Lock()
_SESSION_CONTEXT: ContextVar[str | None] = ContextVar("llm_session", default=None)
_TRACE_CONTEXT: ContextVar[Any] = ContextVar("llm_trace_callback", default=None)


@contextmanager
def llm_context(session_id: str | None, trace_callback=None):
    """Propagate parent session metrics through nested synchronous LLM calls."""
    session_token = _SESSION_CONTEXT.set(session_id)
    trace_token = _TRACE_CONTEXT.set(trace_callback)
    try:
        yield
    finally:
        _SESSION_CONTEXT.reset(session_token)
        _TRACE_CONTEXT.reset(trace_token)


def current_llm_context() -> tuple[str | None, Any]:
    return _SESSION_CONTEXT.get(), _TRACE_CONTEXT.get()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump())
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def estimate_tokens(value: Any) -> int:
    """Cheap deterministic estimate used for diagnostics, not billing."""
    text = value if isinstance(value, str) else _canonical_json(value)
    return max(1, (len(text) + 3) // 4) if text else 0


def prompt_prefix_hash(model: str, stable_system: str, tools: list[dict]) -> str:
    payload = {
        "version": CACHE_POLICY_VERSION,
        "model": model,
        "stable_system": stable_system,
        "tools": tools,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:20]


def _cache_control() -> dict:
    value = {"type": "ephemeral"}
    with _CACHE_STATE_LOCK:
        ttl_available = _CACHE_TTL_SUPPORTED is not False
    if ttl_available and PROMPT_CACHE_TTL in {"5m", "1h"}:
        value["ttl"] = PROMPT_CACHE_TTL
    return value


def _system_blocks(stable: str, semi_stable: str, dynamic: str,
                   enable_cache: bool) -> str | list[dict]:
    sections = [section for section in (stable, semi_stable, dynamic) if section]
    if not enable_cache:
        return "\n\n".join(sections)
    blocks: list[dict] = []
    if stable:
        blocks.append({
            "type": "text",
            "text": stable,
            "cache_control": _cache_control(),
        })
    for section in (semi_stable, dynamic):
        if section:
            blocks.append({"type": "text", "text": section})
    return blocks


def _cache_is_available() -> bool:
    with _CACHE_STATE_LOCK:
        return _CACHE_SUPPORTED is not False


def _remember_cache_support(supported: bool) -> None:
    global _CACHE_SUPPORTED
    with _CACHE_STATE_LOCK:
        _CACHE_SUPPORTED = supported


def _cache_ttl_is_available() -> bool:
    with _CACHE_STATE_LOCK:
        return _CACHE_TTL_SUPPORTED is not False


def _remember_cache_ttl_support(supported: bool) -> None:
    global _CACHE_TTL_SUPPORTED
    with _CACHE_STATE_LOCK:
        _CACHE_TTL_SUPPORTED = supported


def reset_cache_support_for_tests() -> None:
    global _CACHE_SUPPORTED, _CACHE_TTL_SUPPORTED
    with _CACHE_STATE_LOCK:
        _CACHE_SUPPORTED = None
        _CACHE_TTL_SUPPORTED = None


def _is_ttl_compatibility_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    message = str(exc).lower()
    unsupported_terms = (
        "unsupported", "unknown", "unexpected", "extra inputs", "invalid",
        "not permitted", "unrecognized", "forbidden",
    )
    compatible_status = status in {400, 404, 422} or isinstance(exc, TypeError)
    return (compatible_status and "ttl" in message
            and any(term in message for term in unsupported_terms))


def _is_cache_compatibility_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    message = str(exc).lower()
    cache_terms = ("cache_control", "cache control", "prompt cache", "ttl")
    unsupported_terms = (
        "unsupported", "unknown", "unexpected", "extra inputs", "invalid",
        "not permitted", "unrecognized",
    )
    cache_field_error = (
        any(term in message for term in cache_terms)
        and any(term in message for term in (*unsupported_terms, "forbidden"))
    )
    system_shape_error = (
        "system" in message and any(term in message for term in (
            "string", "list", "array", "type", "object"
        ))
    )
    compatible_status = status in {400, 404, 422} or isinstance(exc, TypeError)
    return compatible_status and (cache_field_error or system_shape_error)


def _usage_value(usage: Any, name: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(name, 0) or 0)
    return int(getattr(usage, name, 0) or 0)


def usage_metrics(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    cache_creation = _usage_value(usage, "cache_creation_input_tokens")
    cache_read = _usage_value(usage, "cache_read_input_tokens")
    uncached_equivalent = input_tokens + cache_creation + cache_read
    saved_tokens = cache_read
    estimated_savings = (
        saved_tokens * INPUT_COST_PER_MILLION
        * max(0.0, 1.0 - CACHE_READ_COST_MULTIPLIER) / 1_000_000
        if INPUT_COST_PER_MILLION > 0 else None
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "cache_hit": cache_read > 0,
        "uncached_equivalent_input_tokens": uncached_equivalent,
        "estimated_saved_input_tokens": saved_tokens,
        "estimated_savings_usd": estimated_savings,
    }


def _persist_metric(metric: dict) -> None:
    try:
        TOKEN_USAGE_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).date().isoformat()
        path = TOKEN_USAGE_DIR / f"usage-{day}.jsonl"
        line = json.dumps(_json_safe(metric), ensure_ascii=False) + "\n"
        with _USAGE_LOCK:
            with path.open("a", encoding="utf-8") as output:
                output.write(line)
    except OSError:
        # Metrics must never make an agent request fail.
        return


def _normalize_messages(messages):
    """Coerce tool_use inputs that arrived as JSON strings back to dicts.

    Some Anthropic-compatible endpoints (e.g. Qwen) may serialize a
    tool_use's ``input`` as a JSON string in the response. Re-sending that
    string makes the server call ``.items()`` on it and reject the request
    with HTTP 400 ('str' object has no attribute 'items'). Normalize before
    dispatch so the wire payload always carries a parsed object.
    """
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                _normalize_tool_use_input(block)
        elif hasattr(content, "content"):
            # A single SDK content object (rare); normalize if it is a tool_use.
            _normalize_tool_use_input(content)
    return messages


def _normalize_tool_use_input(block) -> None:
    if block is None:
        return
    btype = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
    if btype != "tool_use":
        return
    inp = block.get("input") if isinstance(block, dict) else getattr(block, "input", None)
    if not isinstance(inp, str):
        return
    coerced = _coerce_input_value(inp)
    if isinstance(block, dict):
        block["input"] = coerced
    else:
        try:
            block.input = coerced
        except (AttributeError, TypeError):
            pass


def _emit(callback, event_type: str, payload: dict) -> None:
    if callback is None:
        return
    try:
        callback(event_type, payload)
    except Exception:
        return


def _response_summary(response: Any) -> dict:
    blocks = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            blocks.append({"type": "text", "preview": getattr(block, "text", "")[:2000]})
        elif block_type == "tool_use":
            blocks.append({
                "type": "tool_use",
                "id": getattr(block, "id", None),
                "name": getattr(block, "name", None),
            })
        else:
            blocks.append({"type": block_type or type(block).__name__})
    summary = {
        "stop_reason": getattr(response, "stop_reason", None),
        "content": blocks,
    }
    if TRACE_FULL_PAYLOAD:
        summary["response"] = response
    return summary


def call_message(*, model: str | Callable[[], str], stable_system: str,
                 semi_stable_system: str = "", dynamic_system: str = "",
                 messages: list, tools: list[dict] | None = None,
                 max_tokens: int, call_type: str,
                 session_id: str | None = None,
                 enable_cache: bool = True,
                 retry: Callable[[Callable[[], Any]], Any] | None = None,
                 trace_callback=None) -> Any:
    """Call Messages API with stable-prefix caching and durable usage metrics."""
    bound_session, bound_trace = current_llm_context()
    session_id = session_id or bound_session
    trace_callback = trace_callback or bound_trace
    tools = list(tools or [])
    messages = _normalize_messages(messages)
    request_id = uuid.uuid4().hex

    def resolve_model() -> str:
        return str(model() if callable(model) else model)

    active_model = resolve_model()
    cache_requested = bool(PROMPT_CACHE_ENABLED and enable_cache and stable_system)
    cache_active = cache_requested and _cache_is_available()
    attempt_count = 0
    started = time.perf_counter()

    # Slim tool descriptors – the web UI surfaces only name/description so the
    # trace payload stays readable instead of dumping the full JSON schema.
    tool_summaries = [
        {
            "name": tool.get("name", ""),
            "description": (tool.get("description", "") or "").strip()[:280],
        }
        for tool in tools
    ]
    summary = {
        "request_id": request_id,
        "call_type": call_type,
        "model": active_model,
        "message_count": len(messages),
        "messages": messages,
        "tools": tool_summaries,
        "tool_names": [tool["name"] for tool in tool_summaries],
    }
    if TRACE_FULL_PAYLOAD:
        summary["system"] = _system_blocks(stable_system, semi_stable_system,
                                           dynamic_system, cache_active)
    _emit(trace_callback, "llm_request", summary)

    def invoke(use_cache: bool):
        nonlocal active_model, attempt_count
        active_model = resolve_model()
        attempt_count += 1
        kwargs = {
            "model": active_model,
            "system": _system_blocks(stable_system, semi_stable_system,
                                     dynamic_system, use_cache),
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
        }
        return client.messages.create(**kwargs)

    def invoke_with_fallback():
        nonlocal cache_active
        while True:
            try:
                response = invoke(cache_active)
                if cache_active:
                    _remember_cache_support(True)
                return response
            except Exception as exc:
                if (cache_active and _cache_ttl_is_available()
                        and _is_ttl_compatibility_error(exc)):
                    _remember_cache_ttl_support(False)
                    _emit(trace_callback, "prompt_cache_ttl_disabled", {
                        "request_id": request_id,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
                    continue
                if cache_active and _is_cache_compatibility_error(exc):
                    cache_active = False
                    _remember_cache_support(False)
                    _emit(trace_callback, "prompt_cache_disabled", {
                        "request_id": request_id,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
                    continue
                raise

    try:
        response = retry(invoke_with_fallback) if retry else invoke_with_fallback()
    except Exception as exc:
        metric = {
            **summary,
            **usage_metrics(None),
            "model": active_model,
            "session_id": session_id,
            "prompt_prefix_hash": prompt_prefix_hash(
                active_model, stable_system, tools
            ),
            "attempt_count": attempt_count,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "cache_active": cache_active,
            "error": f"{type(exc).__name__}: {exc}",
        }
        _persist_metric(metric)
        _emit(trace_callback, "llm_error", metric)
        raise

    metric = {
        **summary,
        **usage_metrics(response),
        "model": active_model,
        "session_id": session_id,
        "prompt_prefix_hash": prompt_prefix_hash(active_model, stable_system, tools),
        "attempt_count": attempt_count,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "cache_active": cache_active,
        "stop_reason": getattr(response, "stop_reason", None),
        "error": None,
    }
    _persist_metric(metric)
    _emit(trace_callback, "llm_response", {
        "request_id": request_id,
        **_response_summary(response),
    })
    _emit(trace_callback, "llm_usage", metric)
    return response
