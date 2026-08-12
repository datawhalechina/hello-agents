"""用于收集和暴露工具调用事件的实用程序。"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from models import SummaryState, TodoItem

logger = logging.getLogger(__name__)


@dataclass
class ToolCallEvent:
    """工具调用事件的内部表示。"""

    id: int
    agent: str
    tool: str
    raw_parameters: str
    parsed_parameters: dict[str, Any]
    result: str
    task_id: int | None
    note_id: str | None


class ToolCallTracker:
    """收集工具调用事件并将其转换为 SSE 负载。"""

    def __init__(self, notes_workspace: str | None) -> None:
        self._notes_workspace = notes_workspace
        self._events: list[ToolCallEvent] = []
        self._cursor = 0
        self._lock = Lock()
        self._event_sink: Callable[[dict[str, Any]], None] | None = None

    def record(self, payload: dict[str, Any]) -> None:
        """
        记录模型工具调用情况，便于日志与前端展示。
        
        Args:
            payload: 工具调用事件负载，包含工具名、参数和结果。
        """
        agent_name = str(payload.get("agent_name") or "unknown")
        tool_name = str(payload.get("tool_name") or "unknown")
        raw_parameters = str(payload.get("raw_parameters") or "")
        parsed_parameters = payload.get("parsed_parameters") or {}
        result_text = str(payload.get("result") or "")

        if not isinstance(parsed_parameters, dict):
            parsed_parameters = {}

        task_id = self._infer_task_id(parsed_parameters)
        note_id: str | None = None

        if tool_name == "note":
            note_id = parsed_parameters.get("note_id")
            if note_id is None:
                note_id = self._extract_note_id(result_text)

        event = ToolCallEvent(
            id=len(self._events) + 1,
            agent=agent_name,
            tool=tool_name,
            raw_parameters=raw_parameters,
            parsed_parameters=parsed_parameters,
            result=result_text,
            task_id=task_id,
            note_id=note_id,
        )

        with self._lock:
            self._events.append(event)

        logger.info(
            "Tool call recorded: agent=%s tool=%s task_id=%s note_id=%s parsed_parameters=%s",
            agent_name,
            tool_name,
            task_id,
            note_id,
            parsed_parameters,
        )

        sink = self._event_sink
        if sink:
            sink(self._build_payload(event, step=None))

    # ------------------------------------------------------------------
    # 排放助手
    # ------------------------------------------------------------------
    def drain(self, state: SummaryState, *, step: int | None = None) -> list[dict[str, Any]]:
        """
        提取尚未消费的工具调用事件，并同步任务的 note_id。
        
        此方法是线程安全的，会移除已提取的事件，避免重复处理。
        同时会检查 note 工具的调用，更新任务状态中的 note_id。
        
        Args:
            state: 当前研究状态。
            step: 可选的步骤编号，附加到返回的事件中。
            
        Returns:
            准备发送给前端的事件字典列表。
        """
        with self._lock:
            if self._cursor >= len(self._events):
                return []
            new_events = self._events[self._cursor :]
            self._cursor = len(self._events)

        if state.todo_items:
            for event in new_events:
                task_id = event.task_id
                note_id = event.note_id
                if task_id is None or not note_id:
                    continue
                self._attach_note_to_task(state.todo_items, task_id, note_id)

        payloads: list[dict[str, Any]] = []
        for event in new_events:
            payload = self._build_payload(event, step=step)
            payloads.append(payload)

        return payloads

    def reset(self) -> None:
        """
        重置当前已记录的工具调用事件。
        
        该方法会清空内部事件列表并重置游标，用于在同一
        Tracker 实例上复用时避免跨任务/会话的事件泄漏。
        """
        with self._lock:
            self._events.clear()
            self._cursor = 0
    def as_dicts(self) -> list[dict[str, Any]]:
        """
        暴露原始事件的快照以实现向后兼容性。
        
        Returns:
            包含所有工具调用事件的字典列表。
        """
        with self._lock:
            return [
                {
                    "id": event.id,
                    "agent": event.agent,
                    "tool": event.tool,
                    "raw_parameters": event.raw_parameters,
                    "parsed_parameters": event.parsed_parameters,
                    "result": event.result,
                    "task_id": event.task_id,
                    "note_id": event.note_id,
                }
                for event in self._events
            ]

    def set_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        """
        注册一个回调以获取即时工具事件通知。
        
        Args:
            sink: 接收事件字典的回调函数。
        """
        self._event_sink = sink

    def _build_payload(self, event: ToolCallEvent, step: int | None) -> dict[str, Any]:
        payload = {
            "type": "tool_call",
            "event_id": event.id,
            "agent": event.agent,
            "tool": event.tool,
            "parameters": event.parsed_parameters,
            "result": event.result,
            "task_id": event.task_id,
            "note_id": event.note_id,
        }
        if event.note_id and self._notes_workspace:
            note_path = Path(self._notes_workspace) / f"{event.note_id}.md"
            payload["note_path"] = str(note_path)
        if step is not None:
            payload["step"] = step
        return payload

    # ------------------------------------------------------------------
    # 内部助手
    # ------------------------------------------------------------------
    def _attach_note_to_task(self, tasks: list[TodoItem], task_id: int, note_id: str) -> None:
        """使用笔记元数据更新匹配的 TODO 项目。"""
        for task in tasks:
            if task.id != task_id:
                continue

            if task.note_id != note_id:
                task.note_id = note_id
                if self._notes_workspace:
                    task.note_path = str(Path(self._notes_workspace) / f"{note_id}.md")
            elif task.note_path is None and self._notes_workspace:
                task.note_path = str(Path(self._notes_workspace) / f"{note_id}.md")
            break

    def _infer_task_id(self, parameters: dict[str, Any]) -> int | None:
        """尝试从工具参数推断 task_id。"""
        if not parameters:
            return None

        if "task_id" in parameters:
            try:
                return int(parameters["task_id"])
            except (TypeError, ValueError):
                pass

        tags = parameters.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                match = re.search(r"task_(\d+)", str(tag))
                if match:
                    return int(match.group(1))

        title = parameters.get("title")
        if isinstance(title, str):
            match = re.search(r"任务\s*(\d+)", title)
            if match:
                return int(match.group(1))

        return None

    def _extract_note_id(self, response: str) -> str | None:
        if not response:
            return None

        match = re.search(r"ID:\s*([^\n]+)", response)
        if match:
            return match.group(1).strip()
        return None
