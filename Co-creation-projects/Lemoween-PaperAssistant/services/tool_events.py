"""工具调用事件追踪"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ToolCallTracker:
    """收集 Agent 工具调用事件，供日志与前端展示"""

    def __init__(self, notes_workspace: Optional[str] = None) -> None:
        self._notes_workspace = notes_workspace
        self._events: list[dict[str, Any]] = []
        self._cursor = 0
        self._lock = Lock()
        self._event_sink: Optional[Callable[[dict[str, Any]], None]] = None

    def record(self, payload: dict[str, Any]) -> None:
        agent_name = str(payload.get("agent_name") or "unknown")
        tool_name = str(payload.get("tool_name") or "unknown")
        parameters = payload.get("parsed_parameters") or {}
        if not isinstance(parameters, dict):
            parameters = {}
        result_text = str(payload.get("result") or "")

        note_id = None
        if tool_name == "note":
            note_id = parameters.get("note_id") or self._extract_note_id(result_text)

        event = {
            "id": len(self._events) + 1,
            "agent": agent_name,
            "tool": tool_name,
            "parameters": parameters,
            "result": result_text[:500],
            "note_id": note_id,
        }
        with self._lock:
            self._events.append(event)

        logger.info("Tool call: agent=%s tool=%s note_id=%s",
                    agent_name, tool_name, note_id)

        if self._event_sink:
            self._event_sink(event)

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            new = self._events[self._cursor:]
            self._cursor = len(self._events)
        return new

    def set_event_sink(self, sink: Optional[Callable[[dict[str, Any]], None]]) -> None:
        self._event_sink = sink

    def as_dicts(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    @staticmethod
    def _extract_note_id(response: str) -> Optional[str]:
        if not response:
            return None
        match = re.search(r"ID:\s*([^\n]+)", response)
        return match.group(1).strip() if match else None