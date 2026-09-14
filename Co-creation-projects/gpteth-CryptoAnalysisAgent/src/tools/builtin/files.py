"""Read / write / edit files inside the workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text


class FileTool(Tool):
    def __init__(self, root: str):
        super().__init__(
            name="file_operation",
            description=(
                "工作空间内的文件操作。action 取 read / write / edit / list。"
                "路径相对于工作空间根目录，禁止访问工作空间之外的文件。"
            ),
        )
        self.root = Path(os.path.abspath(root)).resolve()

    def _resolve(self, rel: str) -> Path:
        target = (self.root / (rel or "")).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("路径超出工作空间范围")
        return target

    def run(self, parameters: Dict[str, Any]) -> str:
        action = str(parameters.get("action") or "read").strip().lower()
        path = first_text(parameters, "path")
        try:
            if action == "list":
                target = self._resolve(path or ".")
                if not target.exists():
                    return f"路径不存在: {path or '.'}"
                if target.is_file():
                    return f"文件 {path} ({target.stat().st_size} bytes)"
                names = sorted(os.listdir(target))[:200]
                return "\n".join(names) or "(空目录)"
            if not path:
                return "错误: 请提供 path"
            target = self._resolve(path)
            if action == "read":
                if not target.is_file():
                    return f"文件不存在: {path}"
                text = target.read_text(encoding="utf-8")
                if len(text) > 20000:
                    text = text[:20000] + "\n…(truncated)"
                return text
            if action == "write":
                content = first_text(parameters, "content")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"已写入 {path} ({len(content)} 字符)"
            if action == "edit":
                old = first_text(parameters, "old_string")
                new = first_text(parameters, "new_string")
                if not target.is_file():
                    return f"文件不存在: {path}"
                text = target.read_text(encoding="utf-8")
                if old not in text:
                    return "未找到要替换的文本"
                target.write_text(text.replace(old, new, 1), encoding="utf-8")
                return f"已更新 {path}"
            return f"未知 action: {action}，可用 read/write/edit/list"
        except Exception as exc:
            return f"文件操作失败: {exc}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="read / write / edit / list", required=True),
            ToolParameter(name="path", type="string", description="相对工作空间的路径", required=False),
            ToolParameter(name="content", type="string", description="write 时的完整内容", required=False),
            ToolParameter(name="old_string", type="string", description="edit 时要替换的原文", required=False),
            ToolParameter(name="new_string", type="string", description="edit 时的新文本", required=False),
        ]
