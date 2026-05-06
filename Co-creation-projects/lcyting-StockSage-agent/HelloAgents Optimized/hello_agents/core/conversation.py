"""对话管理 — Conversation 与 ConversationManager"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from .message import Message


class Conversation:
    """单条对话线，管理一条从根到叶的消息链"""

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        name: str = "",
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.conversation_id: str = conversation_id or uuid.uuid4().hex[:12]
        self.name: str = name
        self.system_prompt: Optional[str] = system_prompt
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = self.created_at
        self.messages: List[Message] = []
        self.metadata: Dict[str, Any] = metadata or {}

    def add_message(self, message: Message) -> Message:
        message.conversation_id = self.conversation_id
        if self.messages:
            message.parent_id = self.messages[-1].message_id
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def get_messages(
        self, start: Optional[int] = None, end: Optional[int] = None
    ) -> List[Message]:
        return self.messages[start:end]

    def get_last_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        for m in self.messages:
            if m.message_id == message_id:
                return m
        return None

    def fork(self, at_message_id: str, new_name: str = "") -> "Conversation":
        target_idx = -1
        for i, m in enumerate(self.messages):
            if m.message_id == at_message_id:
                target_idx = i
                break
        if target_idx == -1:
            raise ValueError(f"消息 {at_message_id} 不存在")

        new_conv = Conversation(
            name=new_name or f"{self.name} (分支)",
            system_prompt=self.system_prompt,
            metadata={**self.metadata, "forked_from": self.conversation_id},
        )

        for i, m in enumerate(self.messages[: target_idx + 1]):
            if i == target_idx:
                fork_msg = m.model_copy(deep=True)
                fork_msg.branch_point = True
                fork_msg.conversation_id = new_conv.conversation_id
                fork_msg.parent_id = (
                    new_conv.messages[-1].message_id if new_conv.messages else None
                )
                new_conv.messages.append(fork_msg)
            else:
                copied = m.model_copy(deep=True)
                copied.conversation_id = new_conv.conversation_id
                copied.parent_id = (
                    new_conv.messages[-1].message_id if new_conv.messages else None
                )
                new_conv.messages.append(copied)

        return new_conv

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict(full=True) for m in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        conv = cls(
            conversation_id=data["conversation_id"],
            name=data.get("name", ""),
            system_prompt=data.get("system_prompt"),
            metadata=data.get("metadata", {}),
        )
        conv.created_at = datetime.fromisoformat(data["created_at"])
        conv.updated_at = datetime.fromisoformat(data["updated_at"])
        for md in data.get("messages", []):
            conv.messages.append(
                Message(
                    content=md["content"],
                    role=md["role"],
                    message_id=md.get("message_id", ""),
                    conversation_id=md.get("conversation_id", conv.conversation_id),
                    parent_id=md.get("parent_id"),
                    branch_point=md.get("branch_point", False),
                    timestamp=datetime.fromisoformat(md["timestamp"])
                    if md.get("timestamp")
                    else None,
                    metadata=md.get("metadata", {}),
                )
            )
        return conv

    def to_llm_messages(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def __len__(self) -> int:
        return len(self.messages)

    def __str__(self) -> str:
        return f"Conversation(id={self.conversation_id}, name={self.name}, messages={len(self.messages)})"
