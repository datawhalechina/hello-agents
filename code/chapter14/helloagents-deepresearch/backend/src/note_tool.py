"""Local markdown note tool used by the deep research workflow."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse


class NoteTool(Tool):
    """Create, read, and update markdown notes in a workspace directory."""

    def __init__(self, workspace: str = "./notes") -> None:
        super().__init__(
            name="note",
            description="Create, read, and update local markdown research notes.",
        )
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="create, read, or update"),
            ToolParameter(name="note_id", type="string", description="Existing note id", required=False),
            ToolParameter(name="title", type="string", description="Note title", required=False),
            ToolParameter(name="content", type="string", description="Markdown note content", required=False),
            ToolParameter(name="note_type", type="string", description="Note category", required=False),
            ToolParameter(name="tags", type="array", description="Note tags", required=False),
            ToolParameter(name="task_id", type="integer", description="Related task id", required=False),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        action = str(parameters.get("action") or "").strip().lower()

        if action == "create":
            return self._create(parameters)
        if action == "read":
            return self._read(parameters)
        if action == "update":
            return self._update(parameters)

        return ToolResponse.error(
            code="INVALID_ACTION",
            message="action must be one of: create, read, update",
        )

    def _create(self, parameters: dict[str, Any]) -> ToolResponse:
        note_id = str(parameters.get("note_id") or self._new_note_id(parameters)).strip()
        path = self._path_for(note_id)
        title = str(parameters.get("title") or note_id).strip()
        content = str(parameters.get("content") or "").strip()
        text = self._render_note(title, content, parameters)
        path.write_text(text, encoding="utf-8")

        return ToolResponse.success(
            text=f"✅ 笔记已创建\nID: {note_id}\nPath: {path}",
            data={"note_id": note_id, "path": str(path), "action": "create"},
        )

    def _read(self, parameters: dict[str, Any]) -> ToolResponse:
        note_id = str(parameters.get("note_id") or "").strip()
        if not note_id:
            return ToolResponse.error(code="MISSING_NOTE_ID", message="note_id is required")

        path = self._path_for(note_id)
        if not path.exists():
            return ToolResponse.error(code="NOT_FOUND", message=f"note not found: {note_id}")

        return ToolResponse.success(
            text=path.read_text(encoding="utf-8"),
            data={"note_id": note_id, "path": str(path), "action": "read"},
        )

    def _update(self, parameters: dict[str, Any]) -> ToolResponse:
        note_id = str(parameters.get("note_id") or "").strip()
        if not note_id:
            return ToolResponse.error(code="MISSING_NOTE_ID", message="note_id is required")

        path = self._path_for(note_id)
        title = str(parameters.get("title") or note_id).strip()
        content = str(parameters.get("content") or "").strip()
        text = self._render_note(title, content, parameters)
        path.write_text(text, encoding="utf-8")

        return ToolResponse.success(
            text=f"✅ 笔记已更新\nID: {note_id}\nPath: {path}",
            data={"note_id": note_id, "path": str(path), "action": "update"},
        )

    def _path_for(self, note_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", note_id)
        workspace_root = self.workspace.resolve()
        path = (self.workspace / f"{safe_id}.md").resolve()
        if path != workspace_root and workspace_root not in path.parents:
            raise ValueError(f"Invalid note_id: {note_id}")
        return path

    def _new_note_id(self, parameters: dict[str, Any]) -> str:
        title = str(parameters.get("title") or "note").strip().lower()
        slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", title).strip("-")[:48]
        suffix = uuid4().hex[:8]
        return f"{slug or 'note'}-{suffix}"

    def _render_note(self, title: str, content: str, parameters: dict[str, Any]) -> str:
        tags = parameters.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]

        metadata = [
            "---",
            f"title: {title}",
            f"note_type: {parameters.get('note_type') or ''}",
            f"task_id: {parameters.get('task_id') or ''}",
            f"tags: {', '.join(str(tag) for tag in tags)}",
            f"updated_at: {datetime.now().isoformat(timespec='seconds')}",
            "---",
            "",
        ]
        return "\n".join(metadata) + content + "\n"
