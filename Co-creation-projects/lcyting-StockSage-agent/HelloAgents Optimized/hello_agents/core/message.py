"""消息系统"""

import uuid
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system", "tool"]


class Message(BaseModel):
    """消息类"""

    content: str
    role: MessageRole
    message_id: str = ""
    conversation_id: str = ""
    parent_id: Optional[str] = None
    branch_point: bool = False
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(
            content=content,
            role=role,
            message_id=kwargs.get("message_id", uuid.uuid4().hex[:12]),
            conversation_id=kwargs.get("conversation_id", ""),
            parent_id=kwargs.get("parent_id"),
            branch_point=kwargs.get("branch_point", False),
            timestamp=kwargs.get("timestamp", datetime.now()),
            metadata=kwargs.get("metadata", {}),
        )

    def to_dict(self, full: bool = False) -> Dict[str, Any]:
        if full:
            return {
                "role": self.role,
                "content": self.content,
                "message_id": self.message_id,
                "conversation_id": self.conversation_id,
                "parent_id": self.parent_id,
                "branch_point": self.branch_point,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "metadata": self.metadata,
            }
        return {"role": self.role, "content": self.content}

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
