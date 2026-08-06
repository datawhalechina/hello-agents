"""Memory 管理器：组合会话记忆与长期记忆"""
from __future__ import annotations

from backend.memory.conversation import ConversationMemory
from backend.memory.long_term import LongTermMemory


class MemoryManager:
    """统一管理会话级对话记忆与长期知识记忆

    - conversation：当前会话的对话记忆（每次 new_session 替换）
    - long_term：跨会话的长期知识记忆（单例，全生命周期共享）
    """

    def __init__(self) -> None:
        # 长期记忆跨会话共享，懒加载内部依赖
        self._long_term: LongTermMemory = LongTermMemory()
        # 初始化首个会话记忆
        self._conversation: ConversationMemory = ConversationMemory()

    @property
    def conversation(self) -> ConversationMemory:
        """当前会话记忆"""
        return self._conversation

    @property
    def long_term(self) -> LongTermMemory:
        """长期知识记忆"""
        return self._long_term

    def new_session(self) -> ConversationMemory:
        """创建新的会话记忆（替换当前会话）

        Returns:
            新创建的 ConversationMemory 实例
        """
        self._conversation = ConversationMemory()
        return self._conversation
