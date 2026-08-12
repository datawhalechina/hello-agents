"""Step 8: 上下文工程 — 对话压缩、Token 管理、多轮连贯性"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class ContextManager:
    """对话上下文管理器：压缩历史、控制 Token 用量、保持连贯性"""

    def __init__(self, max_tokens: int = 4000, summary_trigger: int = 3000):
        self.max_tokens = max_tokens        # 上下文最大 token 数
        self.summary_trigger = summary_trigger  # 触发压缩的阈值
        self.turns: List[Dict] = []          # 对话轮次
        self.summary: str = ""               # 压缩后的摘要
        self.total_turns = 0

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """简单 Token 估算：中文 ~1.5 字/token，英文 ~4 字/token"""
        chinese = sum(1 for c in text if '一' <= c <= '鿿')
        other = len(text) - chinese
        return int(chinese / 1.5 + other / 4)

    def add_turn(self, role: str, content: str):
        """添加一轮对话"""
        self.total_turns += 1
        turn = {
            "id": self.total_turns,
            "role": role,
            "content": content,
            "tokens": self._estimate_tokens(content),
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        self.turns.append(turn)

        # 检查是否需要压缩
        total = sum(t["tokens"] for t in self.turns)
        if total > self.summary_trigger:
            self._compress()

    def _compress(self):
        """压缩早期对话为摘要"""
        if len(self.turns) <= 4:
            return  # 保留最近 4 轮

        # 取最早的 60% 轮次进行压缩
        split = max(1, int(len(self.turns) * 0.6))
        old_turns = self.turns[:split]
        recent = self.turns[split:]

        # 生成摘要
        lines = []
        for t in old_turns:
            role_label = "用户" if t["role"] == "user" else "助手"
            snippet = t["content"][:200].replace("\n", " ")
            lines.append(f"[{role_label}]: {snippet}")

        new_summary = "对话历史摘要:\n" + "\n".join(lines)
        if self.summary:
            self.summary = self.summary[:500] + "\n...\n" + new_summary
        else:
            self.summary = new_summary

        # 限制摘要长度
        while self._estimate_tokens(self.summary) > 1500:
            # Drop the earliest part of the summary string by splitting on lines
            lines = self.summary.split('\n')
            if len(lines) <= 2:
                # If there are only a couple lines left, we must chop strings carefully or discard
                self.summary = ""
                break
            else:
                self.summary = "对话历史摘要:\n" + "\n".join(lines[2:])

        self.turns = recent

    def get_context(self, system_prompt: str = "",
                    current_query: str = "") -> str:
        """构建当前上下文字符串"""
        parts = []

        # 压缩摘要
        if self.summary:
            parts.append(f"## 历史对话摘要\n{self.summary[:2000]}")

        # 最近对话
        if self.turns:
            parts.append("## 最近对话")
            for t in self.turns[-8:]:  # 最近 8 轮
                role_label = "用户" if t["role"] == "user" else "助手"
                content = t["content"]
                if self._estimate_tokens(content) > 500:
                    content = content[:500] + "..."
                parts.append(f"### {role_label}\n{content}")

        return "\n\n".join(parts)

    def get_stats(self) -> str:
        """获取上下文使用统计"""
        total = sum(t["tokens"] for t in self.turns)
        summary_tokens = self._estimate_tokens(self.summary) if self.summary else 0
        return (f"上下文: {len(self.turns)} 活跃轮次, "
                f"约 {total} tokens 活跃 + {summary_tokens} tokens 摘要, "
                f"总计 {self.total_turns} 轮对话")

    def clear(self):
        self.turns = []
        self.summary = ""
        self.total_turns = 0


# ===== 上下文感知的 System Prompt 构建器 =====

def build_context_aware_prompt(
    ctx: ContextManager,
    base_prompt: str,
    user_query: str,
    memory_context: str = "",
    kb_context: str = "",
) -> str:
    """构建完整上下文感知的系统消息"""

    parts = [base_prompt]

    # 对话上下文
    context_str = ctx.get_context()
    if context_str:
        parts.append(f"\n## 当前对话上下文\n{context_str}")

    # 记忆上下文
    if memory_context:
        parts.append(f"\n## 用户记忆\n{memory_context}")

    # 知识库上下文
    if kb_context:
        parts.append(f"\n## 相关知识\n{kb_context}")

    return "\n".join(parts)


# 全局单例
_ctx_instance: Optional[ContextManager] = None


def get_context() -> ContextManager:
    global _ctx_instance
    if _ctx_instance is None:
        _ctx_instance = ContextManager()
    return _ctx_instance


# ===== 工具函数 =====

def context_stats(query: str = "") -> str:
    """查看当前上下文使用统计"""
    return get_context().get_stats()


def context_clear(query: str = "") -> str:
    """清空上下文（开始新会话）"""
    get_context().clear()
    return "上下文已清空，开始新会话。"


def context_summarize(query: str = "") -> str:
    """手动触发上下文压缩"""
    ctx = get_context()
    ctx._compress()
    return ctx.get_stats()
