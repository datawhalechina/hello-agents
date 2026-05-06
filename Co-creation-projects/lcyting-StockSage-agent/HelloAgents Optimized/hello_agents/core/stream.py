"""流式输出事件系统"""

from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass, field

StreamEventType = Literal[
    "text",
    "thought",
    "action",
    "observation",
    "tool_call",
    "tool_result",
    "status",
    "error",
    "done",
]


@dataclass
class StreamEvent:
    event_type: StreamEventType
    content: str
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def text(cls, content: str) -> "StreamEvent":
        return cls(event_type="text", content=content)

    @classmethod
    def thought(cls, content: str) -> "StreamEvent":
        return cls(event_type="thought", content=content)

    @classmethod
    def action(cls, content: str, **metadata) -> "StreamEvent":
        return cls(event_type="action", content=content, metadata=metadata)

    @classmethod
    def observation(cls, content: str, **metadata) -> "StreamEvent":
        return cls(event_type="observation", content=content, metadata=metadata)

    @classmethod
    def tool_call(cls, tool_name: str, parameters: str) -> "StreamEvent":
        return cls(
            event_type="tool_call",
            content=f"[TOOL_CALL:{tool_name}:{parameters}]",
            metadata={"tool_name": tool_name, "parameters": parameters},
        )

    @classmethod
    def tool_result(cls, tool_name: str, result: str) -> "StreamEvent":
        return cls(
            event_type="tool_result", content=result, metadata={"tool_name": tool_name}
        )

    @classmethod
    def status(cls, content: str, **metadata) -> "StreamEvent":
        return cls(event_type="status", content=content, metadata=metadata)

    @classmethod
    def error(cls, content: str) -> "StreamEvent":
        return cls(event_type="error", content=content)

    @classmethod
    def done(cls, full_response: str) -> "StreamEvent":
        return cls(event_type="done", content=full_response)
