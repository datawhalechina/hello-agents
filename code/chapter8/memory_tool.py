"""独立的 MemoryTool 实现

基于 hello_agents Tool 基类，提供记忆管理功能。
使用内存存储，适合学习和演示用途。
"""

from typing import Dict, Any, List
from datetime import datetime

from hello_agents.tools import Tool, ToolParameter, ToolResponse
from memory import MemoryConfig, MemoryItem


class _MemoryTypeStore:
    """单种记忆类型的存储"""

    def __init__(self, name: str):
        self.name = name
        self.items: List[MemoryItem] = []

    def clear(self):
        self.items.clear()

    def __repr__(self):
        return f"MemoryTypeStore({self.name}, count={len(self.items)})"


class MemoryManager:
    """记忆管理器 — 组合各记忆类型组件"""

    def __init__(self, user_id: str, config: MemoryConfig, memory_types: List[str]):
        self.user_id = user_id
        self.config = config
        self.memory_types: Dict[str, _MemoryTypeStore] = {
            t: _MemoryTypeStore(t) for t in memory_types
        }

    def add_memory(self, content: str, memory_type: str, importance: float, metadata: dict = None, auto_classify: bool = False) -> str:
        item = MemoryItem(content=content, memory_type=memory_type, importance=importance, metadata=metadata or {})
        store = self.memory_types.get(memory_type)
        if store is None:
            raise ValueError(f"不支持的记忆类型: {memory_type}")
        store.items.append(item)
        return item.id

    def retrieve_memories(self, query: str, limit: int = 5, memory_types: List[str] = None, min_importance: float = 0.0) -> List[MemoryItem]:
        pools = [self.memory_types[t] for t in (memory_types or self.memory_types) if t in self.memory_types]
        candidates = [m for s in pools for m in s.items if m.importance >= min_importance]
        if query:
            q = query.lower()
            candidates.sort(key=lambda m: (q in m.content.lower(), m.importance), reverse=True)
        else:
            candidates.sort(key=lambda m: m.importance, reverse=True)
        return candidates[:limit]

    def get_memory_stats(self) -> Dict[str, Any]:
        by_type = {}
        for t, store in self.memory_types.items():
            if store.items:
                avg = sum(m.importance for m in store.items) / len(store.items)
            else:
                avg = 0.0
            by_type[t] = {"count": len(store.items), "avg_importance": avg}
        return {
            "total_memories": sum(len(s.items) for s in self.memory_types.values()),
            "memories_by_type": by_type,
            "enabled_types": list(self.memory_types.keys()),
        }

    def update_memory(self, memory_id: str, content: str = None, importance: float = None, metadata: dict = None) -> bool:
        for store in self.memory_types.values():
            for m in store.items:
                if m.id == memory_id or m.id.startswith(memory_id):
                    if content is not None:
                        m.content = content
                    if importance is not None:
                        m.importance = importance
                    if metadata:
                        m.metadata.update(metadata)
                    m.updated_at = datetime.now()
                    return True
        return False

    def remove_memory(self, memory_id: str) -> bool:
        for store in self.memory_types.values():
            for i, m in enumerate(store.items):
                if m.id == memory_id or m.id.startswith(memory_id):
                    store.items.pop(i)
                    return True
        return False

    def forget_memories(self, strategy: str = "importance_based", threshold: float = 0.2, max_age_days: int = 30) -> int:
        removed = 0
        now = datetime.now()
        for store in self.memory_types.values():
            before = len(store.items)
            if strategy == "importance_based":
                store.items = [m for m in store.items if m.importance >= threshold]
            elif strategy == "time_based":
                store.items = [m for m in store.items if (now - m.created_at).days <= max_age_days]
            elif strategy == "capacity_based":
                store.items.sort(key=lambda m: m.importance, reverse=True)
                store.items = store.items[:max(1, int(threshold))]
            removed += before - len(store.items)
        return removed

    def consolidate_memories(self, from_type: str = "working", to_type: str = "episodic", importance_threshold: float = 0.7) -> int:
        src = self.memory_types.get(from_type)
        dst = self.memory_types.get(to_type)
        if src is None or dst is None:
            return 0
        to_move = [m for m in src.items if m.importance >= importance_threshold]
        for m in to_move:
            m.memory_type = to_type
            m.metadata["consolidated_from"] = from_type
            dst.items.append(m)
        src.items = [m for m in src.items if m.importance < importance_threshold]
        return len(to_move)

    def clear_all_memories(self):
        for store in self.memory_types.values():
            store.clear()


class MemoryTool(Tool):
    """记忆管理工具

    支持四种记忆类型：working（工作记忆）、episodic（情景记忆）、
    semantic（语义记忆）、perceptual（感知记忆）。

    所有数据存储在内存中，进程结束后清空。
    """

    def __init__(
        self,
        user_id: str = "default_user",
        memory_config: MemoryConfig = None,
        memory_types: List[str] = None,
    ):
        super().__init__(
            name="memory",
            description="记忆管理工具，支持添加、搜索、摘要、统计、更新、删除、遗忘、整合等操作",
        )
        self.memory_config = memory_config or MemoryConfig()
        self.memory_types = memory_types or ["working", "episodic", "semantic", "perceptual"]
        self.memory_manager = MemoryManager(
            user_id=user_id,
            config=self.memory_config,
            memory_types=self.memory_types,
        )

    def run(self, parameters) -> str:
        if isinstance(parameters, str):
            parameters = {"action": parameters}
        action = parameters.get("action")
        if not action:
            return "缺少 action 参数"

        kwargs = {k: v for k, v in parameters.items() if k != "action"}
        handler = {
            "add": self._add,
            "search": self._search,
            "summary": self._summary,
            "stats": self._stats,
            "update": self._update,
            "remove": self._remove,
            "forget": self._forget,
            "consolidate": self._consolidate,
            "clear_all": self._clear_all,
        }.get(action)

        if handler is None:
            return f"不支持的操作: {action}"

        try:
            resp = handler(**kwargs)
            return resp.text
        except Exception as e:
            return f"执行错误: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="action", type="string", description="操作类型", required=True)]

    # ── 内部实现 ──────────────────────────────────────────────

    def _add(self, content: str = "", memory_type: str = "working", importance: float = 0.5, **metadata) -> ToolResponse:
        mid = self.memory_manager.add_memory(content=content, memory_type=memory_type, importance=importance, metadata=metadata)
        return ToolResponse.success(text=f"记忆已添加 (ID: {mid[:8]}..., 类型: {memory_type})", data={"id": mid})

    def _search(self, query: str = "", memory_type: str = None, limit: int = 5, min_importance: float = 0.0, **_) -> ToolResponse:
        types = [memory_type] if memory_type else None
        results = self.memory_manager.retrieve_memories(query=query, limit=limit, memory_types=types, min_importance=min_importance)
        if not results:
            return ToolResponse.success(text=f"未找到与 '{query}' 相关的记忆", data={"results": []})
        lines = [f"找到 {len(results)} 条相关记忆:"]
        for i, m in enumerate(results, 1):
            label = {"working": "工作", "episodic": "情景", "semantic": "语义", "perceptual": "感知"}.get(m.memory_type, m.memory_type)
            preview = m.content[:80] + ("..." if len(m.content) > 80 else "")
            lines.append(f"{i}. [{label}] {preview} (重要性: {m.importance:.2f})")
        return ToolResponse.success(text="\n".join(lines), data={"results": [m.to_dict() for m in results]})

    def _summary(self, limit: int = 5, **_) -> ToolResponse:
        stats = self.memory_manager.get_memory_stats()
        parts = ["记忆系统摘要", f"总记忆数: {stats['total_memories']}"]
        for t, ts in stats["memories_by_type"].items():
            if ts["count"]:
                label = {"working": "工作", "episodic": "情景", "semantic": "语义", "perceptual": "感知"}.get(t, t)
                parts.append(f"  {label}: {ts['count']} 条 (平均重要性: {ts['avg_importance']:.2f})")
        all_items = sorted(
            [m for s in self.memory_manager.memory_types.values() for m in s.items],
            key=lambda m: m.importance, reverse=True,
        )
        if all_items:
            parts.append(f"\n重要记忆 (前 {min(limit, len(all_items))} 条):")
            for i, m in enumerate(all_items[:limit], 1):
                preview = m.content[:60] + ("..." if len(m.content) > 60 else "")
                parts.append(f"  {i}. {preview} (重要性: {m.importance:.2f})")
        return ToolResponse.success(text="\n".join(parts))

    def _stats(self) -> ToolResponse:
        stats = self.memory_manager.get_memory_stats()
        return ToolResponse.success(
            text=f"记忆统计\n总记忆数: {stats['total_memories']}\n启用类型: {', '.join(stats['enabled_types'])}",
            data=stats,
        )

    def _update(self, memory_id: str, content: str = None, importance: float = None, **_) -> ToolResponse:
        ok = self.memory_manager.update_memory(memory_id, content=content, importance=importance)
        return ToolResponse.success(text="记忆已更新") if ok else ToolResponse.error(code="NOT_FOUND", message="未找到指定记忆")

    def _remove(self, memory_id: str, **_) -> ToolResponse:
        ok = self.memory_manager.remove_memory(memory_id)
        return ToolResponse.success(text="记忆已删除") if ok else ToolResponse.error(code="NOT_FOUND", message="未找到指定记忆")

    def _forget(self, strategy: str = "importance_based", threshold: float = 0.2, max_age_days: int = 30, **_) -> ToolResponse:
        count = self.memory_manager.forget_memories(strategy=strategy, threshold=threshold, max_age_days=max_age_days)
        return ToolResponse.success(text=f"已遗忘 {count} 条记忆 (策略: {strategy})")

    def _consolidate(self, from_type: str = "working", to_type: str = "episodic", importance_threshold: float = 0.6, **_) -> ToolResponse:
        count = self.memory_manager.consolidate_memories(from_type=from_type, to_type=to_type, importance_threshold=importance_threshold)
        return ToolResponse.success(text=f"已整合 {count} 条记忆 ({from_type} → {to_type})")

    def _clear_all(self) -> ToolResponse:
        total = sum(len(s.items) for s in self.memory_manager.memory_types.values())
        self.memory_manager.clear_all_memories()
        return ToolResponse.success(text=f"已清空所有记忆 (共 {total} 条)")
