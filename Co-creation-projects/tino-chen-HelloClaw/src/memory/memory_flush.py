"""Memory Flush 管理器 - 在上下文压缩前提醒 Agent 保存记忆"""

from datetime import datetime
from typing import Optional, Tuple


class MemoryFlushManager:
    """Memory Flush 管理器

    在上下文即将压缩前，触发一个静默回合，提醒 Agent 保存记忆。
    这样可以防止有价值的上下文在压缩时丢失。
    """

    def __init__(
        self,
        context_window: int = 128000,
        compression_threshold: float = 0.8,
        soft_threshold_tokens: int = 4000,
        enabled: bool = True,
    ):
        """初始化 Memory Flush 管理器

        Args:
            context_window: 上下文窗口大小
            compression_threshold: 压缩阈值（比例）
            soft_threshold_tokens: 软阈值 token 数（在压缩点之前触发 flush）
            enabled: 是否启用 flush 功能
        """
        self.context_window = context_window
        self.compression_threshold = compression_threshold
        self.soft_threshold_tokens = soft_threshold_tokens
        self.enabled = enabled

        # 记录是否已经触发过 flush（每个会话只触发一次）
        self._flush_triggered = False

    def should_trigger_flush(self, current_tokens: int) -> bool:
        """判断是否应该触发 flush

        Args:
            current_tokens: 当前 token 数

        Returns:
            是否应该触发 flush
        """
        if not self.enabled or self._flush_triggered:
            return False

        # 计算触发点：压缩阈值 - 软阈值
        trigger_point = (
            self.context_window * self.compression_threshold
            - self.soft_threshold_tokens
        )

        if current_tokens >= trigger_point:
            self._flush_triggered = True
            return True

        return False

    def get_flush_prompt(self) -> str:
        """获取 flush 提示词

        Returns:
            静默回合的提示词
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return f"""Pre-compaction memory flush.

The conversation context is about to be compressed. Please save any important memories now.

Guidelines:
- Use memory_add to save notable facts, decisions, or user preferences to memory/{today}.md
- Use memory_update_longterm for information that should persist across all sessions
- Focus on information that would be valuable for future conversations

If nothing important needs to be stored, reply with exactly: [SILENT]"""

    def is_silent_response(self, response: str) -> bool:
        """判断是否是静默响应

        Args:
            response: Agent 的响应

        Returns:
            是否是静默响应（不需要返回给用户）
        """
        return response.strip() == "[SILENT]"

    def reset(self):
        """重置 flush 状态（新会话时调用）"""
        self._flush_triggered = False

    def get_status(self) -> dict:
        """获取当前状态

        Returns:
            状态信息字典
        """
        trigger_point = (
            self.context_window * self.compression_threshold
            - self.soft_threshold_tokens
        )
        return {
            "enabled": self.enabled,
            "context_window": self.context_window,
            "compression_threshold": self.compression_threshold,
            "soft_threshold_tokens": self.soft_threshold_tokens,
            "trigger_point": int(trigger_point),
            "flush_triggered": self._flush_triggered,
        }
