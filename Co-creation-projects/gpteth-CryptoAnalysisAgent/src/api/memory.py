"""Memory HTTP API."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .deps import get_memory, get_workspace

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCaptureRequest(BaseModel):
    content: str
    category: str = "fact"


@router.get("/list")
def list_memories(category: Optional[str] = Query(None)):
    memory = get_memory()
    workspace = get_workspace()
    items = []
    if os.path.isdir(workspace.memory_path):
        files = sorted(
            [f for f in os.listdir(workspace.memory_path) if f.endswith(".md")],
            reverse=True,
        )
        for filename in files:
            content = memory.load_daily(filename) or ""
            if category and f"[{category}]" not in content.lower():
                continue
            preview = next((line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")), "(空)")
            items.append({
                "date": filename.replace(".md", ""),
                "filename": filename,
                "content": content,
                "preview": preview[:120],
            })
    return {"memories": items, "total": len(items)}


@router.get("/longterm")
def get_longterm():
    content = get_workspace().load_config("MEMORY") or ""
    return {"filename": "MEMORY.md", "content": content}


@router.put("/longterm")
def update_longterm(body: MemoryCaptureRequest):
    get_memory().append_longterm(body.content)
    return {"status": "ok", "message": "已更新长期记忆"}


@router.post("/capture")
def capture(body: MemoryCaptureRequest):
    get_memory().append_daily(body.content, category=body.category)
    return {"status": "ok", "message": "已添加到今日记忆", "category": body.category}


@router.post("/cleanup")
def cleanup(days: int = Query(30)):
    deleted = get_memory().cleanup(days)
    return {"status": "ok", "deleted": deleted, "message": f"已清理 {len(deleted)} 个文件"}


@router.get("/{filename}")
def get_memory_file(filename: str):
    if filename == "MEMORY.md":
        return get_longterm()
    content = get_memory().load_daily(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="记忆文件不存在")
    return {"filename": filename if filename.endswith(".md") else f"{filename}.md", "content": content}
