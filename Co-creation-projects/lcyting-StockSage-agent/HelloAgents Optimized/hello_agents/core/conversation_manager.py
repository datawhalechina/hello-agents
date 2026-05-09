"""对话管理器 — 多对话生命周期管理"""

import json
import os
from typing import Optional, Dict, Any, List

from .message import Message
from .conversation import Conversation


class ConversationManager:
    """管理多个对话、分支、持久化、自动截断"""

    def __init__(
        self,
        max_conversations: int = 50,
        max_messages_per_conversation: int = 100,
    ):
        self.conversations: Dict[str, Conversation] = {}
        self.active_conversation_id: Optional[str] = None
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation

    # ── 对话生命周期 ──

    def create_conversation(
        self,
        name: str = "",
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        conv = Conversation(name=name, system_prompt=system_prompt, metadata=metadata)
        self.conversations[conv.conversation_id] = conv
        self.active_conversation_id = conv.conversation_id

        if len(self.conversations) > self.max_conversations:
            oldest = min(self.conversations.values(), key=lambda c: c.updated_at)
            del self.conversations[oldest.conversation_id]

        return conv

    def delete_conversation(self, conv_id: str) -> bool:
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            if self.active_conversation_id == conv_id:
                self.active_conversation_id = next(iter(self.conversations), None)
            return True
        return False

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        return self.conversations.get(conv_id)

    def list_conversations(self) -> List[Conversation]:
        return sorted(
            self.conversations.values(), key=lambda c: c.updated_at, reverse=True
        )

    # ── 激活 ──

    def set_active(self, conv_id: str) -> bool:
        if conv_id in self.conversations:
            self.active_conversation_id = conv_id
            return True
        return False

    def get_active(self) -> Optional[Conversation]:
        if self.active_conversation_id:
            return self.conversations.get(self.active_conversation_id)
        return None

    # ── 分支 ──

    def fork_conversation(
        self, conv_id: str, at_message_id: str, new_name: str = ""
    ) -> Optional[Conversation]:
        conv = self.conversations.get(conv_id)
        if not conv:
            return None
        branch = conv.fork(at_message_id, new_name)
        self.conversations[branch.conversation_id] = branch
        self.active_conversation_id = branch.conversation_id
        return branch

    # ── 消息操作 ──

    def add_message(
        self, conv_id: str, content: str, role: str, **kwargs
    ) -> Optional[Message]:
        if conv_id not in self.conversations:
            return None
        conv = self.conversations[conv_id]
        msg = Message(content=content, role=role, conversation_id=conv_id, **kwargs)
        conv.add_message(msg)

        if len(conv.messages) > self.max_messages_per_conversation:
            excess = len(conv.messages) - self.max_messages_per_conversation
            conv.messages = conv.messages[excess:]

        return msg

    def delete_message(self, conv_id: str, message_id: str) -> bool:
        conv = self.conversations.get(conv_id)
        if not conv:
            return False
        before = len(conv.messages)
        conv.messages = [m for m in conv.messages if m.message_id != message_id]
        return len(conv.messages) < before

    def edit_message(self, conv_id: str, message_id: str, new_content: str) -> bool:
        conv = self.conversations.get(conv_id)
        if not conv:
            return False
        msg = conv.get_message_by_id(message_id)
        if not msg:
            return False
        msg.content = new_content
        return True

    # ── 持久化 ──

    def save_to_json(self, path: str) -> None:
        data = {
            "active_conversation_id": self.active_conversation_id,
            "conversations": [conv.to_dict() for conv in self.conversations.values()],
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, path: str) -> "ConversationManager":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        mgr = cls()
        for conv_data in data.get("conversations", []):
            conv = Conversation.from_dict(conv_data)
            mgr.conversations[conv.conversation_id] = conv
        mgr.active_conversation_id = data.get("active_conversation_id")
        return mgr

    # ── 清理 ──

    def clear_all(self) -> None:
        self.conversations.clear()
        self.active_conversation_id = None
