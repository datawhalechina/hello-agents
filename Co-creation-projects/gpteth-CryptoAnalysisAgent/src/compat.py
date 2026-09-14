"""Compatibility helpers for hello-agents 1.0 ToolResponse protocol."""

import inspect
from typing import Any, Dict

from hello_agents import SimpleAgent
from hello_agents.core.config import Config


def tool_text(result: Any) -> str:
    """Extract LLM-readable text from a tool result (str or ToolResponse)."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    return getattr(result, "text", None) or str(result)


def to_tool_response(result: Any):
    """Convert a string tool result into ToolResponse when the runtime requires it."""
    if result is None or isinstance(result, str):
        try:
            from hello_agents.tools.response import ToolResponse
        except ImportError:
            return result or ""
        return ToolResponse.success(text=result or "")
    return result


def wrap_tool(tool):
    """Make a string-returning Tool compatible with hello-agents 1.0 run_with_timing()."""
    if getattr(tool, "_compat_wrapped", False):
        return tool
    original_run = tool.run

    def wrapped(parameters):
        return to_tool_response(original_run(parameters))

    tool.run = wrapped
    tool._compat_wrapped = True
    return tool


def wrap_tools(*tools):
    for tool in tools:
        wrap_tool(tool)
    return tools


def make_simple_agent(**kwargs) -> SimpleAgent:
    """Construct SimpleAgent, dropping kwargs unsupported by older hello-agents."""
    params = inspect.signature(SimpleAgent.__init__).parameters
    if "config" in params and "config" not in kwargs:
        try:
            kwargs["config"] = Config(
                skills_enabled=False,
                todowrite_enabled=False,
                devlog_enabled=False,
                subagent_enabled=False,
            )
        except TypeError:
            pass
    filtered = {k: v for k, v in kwargs.items() if k in params}
    return SimpleAgent(**filtered)


def first_text(parameters: Dict[str, Any], *keys: str, default: str = "") -> str:
    """Read the first non-empty parameter among keys, falling back to `input`."""
    for key in (*keys, "input"):
        value = parameters.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default
