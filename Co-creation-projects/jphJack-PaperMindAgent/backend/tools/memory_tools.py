"""Memory 工具：save_memory / load_memory，供 Agent 通过 Function Calling 操作长期记忆"""
from __future__ import annotations

from typing import Any

from backend.tools.base import Tool

# 懒加载长期记忆单例
_long_term = None


def _get_long_term():
    global _long_term
    if _long_term is None:
        from backend.memory.long_term import LongTermMemory
        _long_term = LongTermMemory()
    return _long_term


async def save_memory(content: str, memory_type: str = "knowledge", metadata: str = "") -> dict:
    """保存知识到长期记忆"""
    try:
        lt = _get_long_term()
        meta = {"source": "agent", "note": metadata} if metadata else {"source": "agent"}
        if memory_type == "gap":
            await lt.save_knowledge(content, {**meta, "type": "gap"})
        elif memory_type == "innovation":
            await lt.save_knowledge(content, {**meta, "type": "innovation"})
        else:
            await lt.save_knowledge(content, meta)
        return {"status": "saved", "memory_type": memory_type, "content_length": len(content)}
    except Exception as e:
        # 降级：长期记忆不可用不影响主流程
        return {"status": "failed", "error": str(e)}


async def load_memory(query: str, top_k: int = 5) -> dict:
    """从长期记忆检索相关知识"""
    try:
        lt = _get_long_term()
        results = await lt.load_relevant(query, top_k=top_k)
        return {"query": query, "memories": results}
    except Exception as e:
        return {"query": query, "memories": [], "error": str(e)}


save_memory_tool = Tool(
    name="save_memory",
    description="保存知识/Gap/创新点到长期记忆，供跨会话复用。memory_type 可选 gap/innovation/knowledge",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "要保存的内容"},
            "memory_type": {"type": "string", "enum": ["gap", "innovation", "knowledge"], "default": "knowledge"},
            "metadata": {"type": "string", "description": "附加说明，可选"},
        },
        "required": ["content"],
    },
    func=save_memory,
)

load_memory_tool = Tool(
    name="load_memory",
    description="从长期记忆语义检索相关知识/历史 Gap/创新点，用于创新点去重与知识复用",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索查询"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    func=load_memory,
)
