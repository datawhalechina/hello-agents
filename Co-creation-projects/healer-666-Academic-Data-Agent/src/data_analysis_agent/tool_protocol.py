"""Local structured tool response protocol."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ToolStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class ToolErrorCode:
    INVALID_PARAM = "INVALID_PARAM"
    EXECUTION_ERROR = "EXECUTION_ERROR"


@dataclass
class ToolResponse:
    status: ToolStatus
    text: str
    data: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict[str, str]] = None
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "status": self.status.value,
            "text": self.text,
            "data": self.data,
        }
        if self.error_info:
            payload["error"] = self.error_info
        if self.context:
            payload["context"] = self.context
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def success(cls, text: str, data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None):
        return cls(status=ToolStatus.SUCCESS, text=text, data=data or {}, context=context)

    @classmethod
    def partial(cls, text: str, data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None):
        return cls(status=ToolStatus.PARTIAL, text=text, data=data or {}, context=context)

    @classmethod
    def error(cls, code: str, message: str, context: Optional[Dict[str, Any]] = None):
        return cls(
            status=ToolStatus.ERROR,
            text=message,
            data={},
            error_info={"code": code, "message": message},
            context=context,
        )
