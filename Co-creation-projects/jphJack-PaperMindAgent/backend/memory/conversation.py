"""会话级对话记忆：维护单次会话的消息列表与中间状态"""
from __future__ import annotations

from typing import Any


class ConversationMemory:
    """单次会话的对话记忆

    - messages：对话消息列表，每条形如 {role, content}
    - intermediate：七步链路中间产物（如已解析论文数、已抽取记录等）
    """

    def __init__(self) -> None:
        # 对话消息列表，每条 {role: str, content: str}
        self._messages: list[dict] = []
        # 中间状态存储，key -> value
        self._intermediate: dict[str, Any] = {}

    def add(self, role: str, content: str) -> None:
        """添加一条对话消息（role: system/user/assistant/tool 等）"""
        self._messages.append({"role": role, "content": content})

    def add_system(self, content: str) -> None:
        """添加 system 消息，插入到列表开头（保证 system 始终在前）"""
        # 若已存在 system 消息，则将新的 system 插入到所有 system 之后、其他消息之前
        insert_idx = 0
        for i, msg in enumerate(self._messages):
            if msg.get("role") == "system":
                insert_idx = i + 1
            else:
                break
        self._messages.insert(insert_idx, {"role": "system", "content": content})

    def get_messages(self) -> list[dict]:
        """返回全部消息（浅拷贝，避免外部直接修改内部状态）"""
        return list(self._messages)

    def get_recent(self, n: int = 10) -> list[dict]:
        """返回最近 n 条消息，防止上下文过长

        注意：system 消息始终保留在最前，以保证系统提示不被截断
        """
        if n <= 0 or not self._messages:
            return []
        # 分离 system 消息与其他消息
        system_msgs = [m for m in self._messages if m.get("role") == "system"]
        non_system = [m for m in self._messages if m.get("role") != "system"]
        # 取非 system 消息的最近 n 条
        recent_non_system = non_system[-n:] if n < len(non_system) else non_system
        return system_msgs + recent_non_system

    def add_intermediate(self, key: str, value: Any) -> None:
        """存储中间状态（七步链路中间产物，如已解析论文数、已抽取记录等）"""
        self._intermediate[key] = value

    def get_intermediate(self, key: str, default: Any = None) -> Any:
        """读取中间状态，不存在则返回 default"""
        return self._intermediate.get(key, default)

    def clear(self) -> None:
        """清空对话消息与中间状态"""
        self._messages.clear()
        self._intermediate.clear()
