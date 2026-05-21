
import logging
import os
from functools import wraps
from typing import Any
from collections.abc import Callable

from hello_agents import HelloAgentsLLM
from ...settings import get_settings

logger = logging.getLogger(__name__)

def normalize_openai_compatible_chat_messages(messages: Any) -> Any:
    if not isinstance(messages, list):
        return messages
    out: list[Any] = []
    for m in messages:
        if not isinstance(m, dict):
            out.append(m)
            continue
        role = str(m.get("role") or "").strip().lower()
        content = m.get("content")
        if role == "summary":
            text = content if isinstance(content, str) else ("" if content is None else str(content))
            out.append({"role": "user", "content": ("[前文摘要]\n" + text).strip()})
            continue
        if role == "developer":
            text = content if isinstance(content, str) else ("" if content is None else str(content))
            nm = dict(m)
            nm["role"] = "system"
            nm["content"] = text
            out.append(nm)
            continue
        out.append(m)
    return out

def _patch_hello_agents_llm_openai_chat_roles() -> None:
    marker = "_papergraph_openai_role_normalize_applied"
    if getattr(HelloAgentsLLM, marker, False):
        return

    def _wrap(orig: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(orig)
        def inner(self: Any, *args: Any, **kwargs: Any) -> Any:
            if args and isinstance(args[0], list):
                args = (normalize_openai_compatible_chat_messages(args[0]),) + tuple(args[1:])
            elif isinstance(kwargs.get("messages"), list):
                kwargs = dict(kwargs)
                kwargs["messages"] = normalize_openai_compatible_chat_messages(kwargs["messages"])
            return orig(self, *args, **kwargs)

        return inner

    HelloAgentsLLM.invoke = _wrap(HelloAgentsLLM.invoke)
    if hasattr(HelloAgentsLLM, "invoke_with_tools"):
        HelloAgentsLLM.invoke_with_tools = _wrap(HelloAgentsLLM.invoke_with_tools)
    for _async_name in ("ainvoke", "async_invoke"):
        if hasattr(HelloAgentsLLM, _async_name):
            setattr(HelloAgentsLLM, _async_name, _wrap(getattr(HelloAgentsLLM, _async_name)))
    setattr(HelloAgentsLLM, marker, True)
    logger.debug("HelloAgentsLLM: patched invoke* for OpenAI-compatible message roles (summary→user)")

_patch_hello_agents_llm_openai_chat_roles()

def _patch_deepseek_disable_thinking() -> None:
    marker = "_papergraph_deepseek_thinking_disabled"
    if getattr(HelloAgentsLLM, marker, False):
        return

    import re as _re

    def _is_deepseek(llm_self: Any) -> bool:
        base = str(getattr(getattr(llm_self, "_adapter", None), "base_url", "") or "")
        return bool(_re.search(r"deepseek", base, _re.I))

    def _wrap(orig: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(orig)
        def inner(self: Any, *args: Any, **kwargs: Any) -> Any:
            if _is_deepseek(self):
                kwargs = dict(kwargs)
                extra = dict(kwargs.get("extra_body") or {})
                if "thinking" not in extra:
                    extra["thinking"] = {"type": "disabled"}
                kwargs["extra_body"] = extra
            return orig(self, *args, **kwargs)

        return inner

    HelloAgentsLLM.invoke = _wrap(HelloAgentsLLM.invoke)
    if hasattr(HelloAgentsLLM, "invoke_with_tools"):
        HelloAgentsLLM.invoke_with_tools = _wrap(HelloAgentsLLM.invoke_with_tools)
    for _async_name in ("ainvoke", "async_invoke"):
        if hasattr(HelloAgentsLLM, _async_name):
            setattr(HelloAgentsLLM, _async_name, _wrap(getattr(HelloAgentsLLM, _async_name)))
    setattr(HelloAgentsLLM, marker, True)
    logger.debug("HelloAgentsLLM: patched invoke* to disable thinking mode for DeepSeek")

_patch_deepseek_disable_thinking()

_llm_instance: HelloAgentsLLM | None = None

def coerce_hello_agents_llm_output_to_str(out: Any) -> str:
    if out is None:
        return ""
    if isinstance(out, str):
        return out
    for attr in ("content", "text"):
        v = getattr(out, attr, None)
        if isinstance(v, str):
            return v
    msg = getattr(out, "message", None)
    if msg is not None:
        c = getattr(msg, "content", None)
        if isinstance(c, str):
            return c
    choices = getattr(out, "choices", None)
    if isinstance(choices, list) and choices:
        m = getattr(choices[0], "message", None)
        if m is not None:
            c = getattr(m, "content", None)
            if isinstance(c, str):
                return c
    return str(out)

def _maybe_disable_proxy_for_llm(base_url: str) -> None:
    url = (base_url or "").strip()
    if not url:
        return

    disable = get_settings().llm_disable_proxy
    proxy_vars = ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"]
    has_proxy = any(str(os.getenv(k) or "").strip() for k in proxy_vars)
    if not has_proxy:
        return

    from urllib.parse import urlparse
    host = ""
    try:
        host = (urlparse(url).hostname or "").strip()
    except Exception:
        host = ""
    if not host:
        return

    def _append_no_proxy(*extra_hosts: str) -> None:
        to_add = [h for h in (host, *extra_hosts) if h and str(h).strip()]

        if "deepseek.com" in host:
            for h in ("deepseek.com", "*.deepseek.com"):
                if h not in to_add:
                    to_add.append(h)

        if "aihubmix.com" in host:
            for h in ("aihubmix.com", "*.aihubmix.com"):
                if h not in to_add:
                    to_add.append(h)
        for env_key in ("NO_PROXY", "no_proxy"):
            cur = str(os.getenv(env_key) or "").strip()
            parts = [p.strip() for p in cur.split(",") if p.strip()]
            seen = {p.lower() for p in parts}
            for h in to_add:
                hl = h.lower()
                if hl not in seen:
                    parts.append(h)
                    seen.add(hl)
            os.environ[env_key] = ",".join(parts)

    if disable:
        for k in proxy_vars:
            os.environ.pop(k, None)
        _append_no_proxy()
        return

    _append_no_proxy()

def is_llm_configured() -> bool:
    s = get_settings()
    key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or s.openai_api_key or "").strip()
    if not key:

        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    return bool(key)

def _sync_env_from_settings() -> None:
    s = get_settings()

    if not os.getenv("LLM_API_KEY") and not os.getenv("OPENAI_API_KEY") and os.getenv("AIHUBMIX_API_KEY"):
        os.environ["LLM_API_KEY"] = str(os.getenv("AIHUBMIX_API_KEY") or "").strip()
    if not os.getenv("LLM_BASE_URL") and not os.getenv("OPENAI_BASE_URL") and os.getenv("AIHUBMIX_BASE_URL"):
        os.environ["LLM_BASE_URL"] = str(os.getenv("AIHUBMIX_BASE_URL") or "").strip()
    if not os.getenv("LLM_MODEL_ID") and not os.getenv("OPENAI_MODEL") and os.getenv("AIHUBMIX_MODEL_ID"):
        os.environ["LLM_MODEL_ID"] = str(os.getenv("AIHUBMIX_MODEL_ID") or "").strip()

    if not os.getenv("LLM_API_KEY") and not os.getenv("OPENAI_API_KEY") and s.openai_api_key:
        os.environ["LLM_API_KEY"] = s.openai_api_key
    if not os.getenv("LLM_BASE_URL") and not os.getenv("OPENAI_BASE_URL") and s.openai_base_url:
        os.environ["LLM_BASE_URL"] = s.openai_base_url
    if not os.getenv("LLM_MODEL_ID") and not os.getenv("OPENAI_MODEL") and s.openai_model:
        os.environ["LLM_MODEL_ID"] = s.openai_model

def get_llm() -> HelloAgentsLLM:
    global _llm_instance
    if _llm_instance is None:

        _sync_env_from_settings()

        api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "")
        base_url = (os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "")
        model = (os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "")

        if not api_key:
            s = get_settings()
            api_key = s.openai_api_key
            if not base_url:
                base_url = s.openai_base_url
            if not model:
                model = s.openai_model

        if not api_key:
            raise RuntimeError("LLM 未配置：请设置 LLM_API_KEY（或在 backend/.env 中配置）")

        _maybe_disable_proxy_for_llm(base_url)

        kw = {}
        if model:
            kw["model"] = model
        if api_key:
            kw["api_key"] = api_key
        if base_url:
            kw["base_url"] = base_url

        logger.info("🔧 正在初始化 LLM...")
        logger.info("   Model: %s", model or "default")
        logger.info("   Base URL: %s", base_url or "default")

        _llm_instance = HelloAgentsLLM(**kw)
        logger.info("✅ LLM 已初始化")
        logger.info("   实际模型: %s", getattr(_llm_instance, "model", "") or "unknown")

        logger.info("   Provider: %s", getattr(_llm_instance, "provider", None) or "unknown")
    return _llm_instance
