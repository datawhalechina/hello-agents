"""记忆 API 路由"""
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

from ..workspace.manager import WorkspaceManager

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryEntry(BaseModel):
    """记忆条目"""
    date: str
    filename: str
    content: str
    preview: str
    category: Optional[str] = None


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    memories: List[MemoryEntry]
    total: int


class MemoryStatsResponse(BaseModel):
    """记忆统计响应"""
    total_files: int
    daily_files: int
    total_size: int
    categories: Dict[str, int]


class MemoryCaptureRequest(BaseModel):
    """记忆捕获请求"""
    content: str
    category: str = "fact"  # preference/decision/entity/fact


class MemoryCaptureResponse(BaseModel):
    """记忆捕获响应"""
    status: str
    message: str
    category: str


class MemoryCleanupResponse(BaseModel):
    """记忆清理响应"""
    status: str
    deleted: List[str]
    message: str


# 全局 workspace 实例（由 main.py 在启动时设置）
_workspace: Optional[WorkspaceManager] = None


def set_workspace(ws: WorkspaceManager):
    """设置全局 workspace 实例"""
    global _workspace
    _workspace = ws


def get_workspace() -> WorkspaceManager:
    """获取 workspace 实例"""
    if _workspace is None:
        ws = WorkspaceManager(os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace"))
        ws.ensure_workspace_exists()
        set_workspace(ws)
    return _workspace


def get_preview(content: str, max_length: int = 100) -> str:
    """获取内容预览"""
    # 移除 markdown 标记，获取纯文本预览
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:max_length] + ('...' if len(line) > max_length else '')
    return '(空)'


# ==================== 静态路由（必须在 /{filename} 之前）====================


@router.get("/list", response_model=MemoryListResponse)
async def list_memories(
    category: Optional[str] = Query(None, description="按分类过滤"),
    ws: WorkspaceManager = Depends(get_workspace)
):
    """获取每日记忆列表（支持分类过滤）

    Args:
        category: 分类标签（preference/decision/entity/fact），可选
    """
    import re

    memories = []

    if os.path.exists(ws.memory_path):
        files = sorted(
            [f for f in os.listdir(ws.memory_path) if f.endswith('.md')],
            reverse=True  # 最新的在前面
        )

        for filename in files:
            filepath = os.path.join(ws.memory_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 如果指定了分类，检查是否包含该分类的标签
            if category:
                pattern = rf'\[{category}\]'
                if not re.search(pattern, content, re.IGNORECASE):
                    continue

            # 从文件名提取日期 (YYYY-MM-DD.md)
            date = filename.replace('.md', '')

            memories.append(MemoryEntry(
                date=date,
                filename=filename,
                content=content,
                preview=get_preview(content),
                category=category
            ))

    return MemoryListResponse(memories=memories, total=len(memories))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(ws: WorkspaceManager = Depends(get_workspace)):
    """获取记忆统计"""
    import re

    total_files = 0
    daily_files = 0
    total_size = 0
    categories = {
        "preference": 0,
        "decision": 0,
        "entity": 0,
        "fact": 0,
    }

    # 统计每日记忆
    if os.path.exists(ws.memory_path):
        for filename in os.listdir(ws.memory_path):
            if filename.endswith('.md'):
                filepath = os.path.join(ws.memory_path, filename)
                total_files += 1
                daily_files += 1
                total_size += os.path.getsize(filepath)

                # 统计各分类标签数量
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                for cat in categories:
                    pattern = rf'\[{cat}\]'
                    count = len(re.findall(pattern, content, re.IGNORECASE))
                    categories[cat] += count

    # 统计长期记忆
    longterm_path = ws.get_config_path("MEMORY")
    if os.path.exists(longterm_path):
        total_files += 1
        total_size += os.path.getsize(longterm_path)

    return MemoryStatsResponse(
        total_files=total_files,
        daily_files=daily_files,
        total_size=total_size,
        categories=categories
    )


@router.post("/today")
async def add_to_today(content: str, ws: WorkspaceManager = Depends(get_workspace)):
    """添加内容到今日记忆"""
    ws.append_to_daily_memory(content)
    return {"status": "ok", "message": "已添加到今日记忆"}


@router.post("/capture", response_model=MemoryCaptureResponse)
async def capture_memory(
    request: MemoryCaptureRequest,
    ws: WorkspaceManager = Depends(get_workspace)
):
    """手动添加记忆（带分类）"""
    # 验证分类
    valid_categories = ["preference", "decision", "entity", "fact"]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分类: {request.category}，有效值: {valid_categories}"
        )

    # 检查重复
    if ws.check_duplicate_memory(request.content, threshold=0.7):
        return MemoryCaptureResponse(
            status="skipped",
            message="记忆已存在，跳过",
            category=request.category
        )

    # 存储记忆
    ws.append_classified_memory(request.content, request.category)

    return MemoryCaptureResponse(
        status="ok",
        message=f"已添加 [{request.category}] 记忆",
        category=request.category
    )


@router.post("/cleanup", response_model=MemoryCleanupResponse)
async def cleanup_memories(
    days: int = Query(30, description="保留天数"),
    ws: WorkspaceManager = Depends(get_workspace)
):
    """清理过期记忆"""
    deleted = ws.cleanup_old_memories(days)

    return MemoryCleanupResponse(
        status="ok",
        deleted=deleted,
        message=f"已清理 {len(deleted)} 个过期记忆文件"
    )


# ==================== 动态路由（必须放在最后）====================


@router.get("/{filename}")
async def get_memory(filename: str, ws: WorkspaceManager = Depends(get_workspace)):
    """获取指定日期的记忆内容"""
    if not filename.endswith('.md'):
        filename += '.md'

    filepath = os.path.join(ws.memory_path, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"记忆文件 {filename} 不存在")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "filename": filename,
        "date": filename.replace('.md', ''),
        "content": content
    }
