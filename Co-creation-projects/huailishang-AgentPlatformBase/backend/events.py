from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4


class EventLogger:
    """In-memory structured event logger for development."""

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []
        self._lock = Lock()

    def emit(
        self,
        event_type: str,
        *,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = {
            "event_id": uuid4().hex,
            "type": event_type,
            "agent_id": agent_id,
            "task_id": task_id,
            "payload": payload or {},
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self._events.append(event)
        return event

    def list_events(self, *, task_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        if task_id:
            events = [event for event in events if event.get("task_id") == task_id]
        return events[-limit:]


event_logger = EventLogger()
