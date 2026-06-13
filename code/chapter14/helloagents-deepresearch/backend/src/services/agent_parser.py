"""Parser helpers for logging agent-style LLM outputs."""

from __future__ import annotations

import json
import re
from typing import Any


TOOL_CALL_PATTERN = re.compile(
    r"\[TOOL_CALL:(?P<tool>[^:]+):(?P<body>[^\]]+)\]",
    re.IGNORECASE,
)


def parse_agent_output(text: str) -> dict[str, Any]:
    """Parse common Thought/Action/Final patterns from an LLM response."""

    raw = text or ""
    parsed: dict[str, Any] = {
        "thought": _extract_section(raw, "Thought", ("Action", "Final")),
        "action": None,
        "action_input": None,
        "final": _extract_section(raw, "Final", ()),
        "raw": raw,
    }

    action = _extract_line(raw, "Action")
    action_input = _extract_section(raw, "Action Input", ("Observation", "Final"))
    if action:
        parsed["action"] = action
        parsed["action_input"] = _parse_payload(action_input)

    tool_call = TOOL_CALL_PATTERN.search(raw)
    if tool_call:
        parsed["action"] = tool_call.group("tool").strip()
        parsed["action_input"] = _parse_payload(tool_call.group("body"))

    return parsed


def _extract_line(text: str, label: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip() or None


def _extract_section(text: str, label: str, stop_labels: tuple[str, ...]) -> str | None:
    stop_pattern = "|".join(re.escape(item) for item in stop_labels)
    if stop_pattern:
        pattern = rf"(?is){re.escape(label)}\s*:\s*(.*?)(?=^\s*(?:{stop_pattern})\s*:|\Z)"
    else:
        pattern = rf"(?is){re.escape(label)}\s*:\s*(.*)\Z"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _parse_payload(value: str | None) -> Any:
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    return clean
