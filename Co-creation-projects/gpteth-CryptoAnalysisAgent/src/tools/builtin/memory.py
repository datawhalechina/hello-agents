"""Memory search / write tools."""

from __future__ import annotations

from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text
from ...memory.store import MemoryStore


class MemoryTool(Tool):
    def __init__(self, memory: MemoryStore):
        super().__init__(
            name="memory",
            description=(
                "记忆管理。action=search 搜索；action=add 写入今日记忆；"
                "action=update_longterm 追加长期记忆 MEMORY.md；action=list 列出记忆文件。"
            ),
        )
        self.memory = memory

    def run(self, parameters: Dict[str, Any]) -> str:
        action = str(parameters.get("action") or "search").strip().lower()
        if action == "search":
            keyword = first_text(parameters, "keyword", "query", "content")
            if not keyword:
                return "请提供 keyword"
            results = self.memory.search(keyword)
            if not results:
                return f"未找到与「{keyword}」相关的记忆"
            parts = []
            for item in results:
                for match in item["matches"]:
                    parts.append(f"**{item['source']}** 行 {match['start_line']}-{match['end_line']}:\n{match['content']}")
            return "\n\n".join(parts[:12])
        if action == "add":
            content = first_text(parameters, "content")
            if not content:
                return "请提供 content"
            category = str(parameters.get("category") or "").strip() or None
            self.memory.append_daily(content, category=category)
            return "已写入今日记忆"
        if action == "update_longterm":
            content = first_text(parameters, "content")
            if not content:
                return "请提供 content"
            self.memory.append_longterm(content)
            return "已更新长期记忆 MEMORY.md"
        if action == "list":
            files = self.memory.list_files()
            if not files:
                return "暂无记忆文件"
            return "\n".join(f"- {f['name']} ({f['type']}, {f['size']} bytes)" for f in files)
        return "未知 action，可用 search / add / update_longterm / list"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="search / add / update_longterm / list", required=True),
            ToolParameter(name="keyword", type="string", description="搜索关键词", required=False),
            ToolParameter(name="content", type="string", description="要写入的记忆", required=False),
            ToolParameter(name="category", type="string", description="preference / decision / entity / fact", required=False),
        ]
