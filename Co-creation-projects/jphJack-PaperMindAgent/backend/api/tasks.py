"""异步任务管理器：维护内存中任务状态与进度事件，供 SSE 推送使用

任务状态机：pending → running → completed / failed
每个任务附带一个 asyncio.Event 通知器，add_event / update_task 时触发，
SSE 生成器据此感知新事件到达，避免忙轮询。
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 合法的任务状态
TASK_STATUSES = ("pending", "running", "completed", "failed")


class TaskManager:
    """内存级任务管理器（单进程内有效）

    任务状态 dict 结构：
        {
            "task_id": str,
            "folder_path": str,
            "status": "pending" | "running" | "completed" | "failed",
            "progress": float,            # 整体进度 0-1
            "current_stage": str | None,  # 当前步骤 stage
            "result": dict | None,        # 完成后的最终结果 {markdown, report, evaluation}
            "error": str | None,          # 失败时的错误信息
            "events": list[dict],         # 进度事件历史
            "created_at": str,            # ISO 时间戳
            "updated_at": str,            # ISO 时间戳
        }
    """

    def __init__(self) -> None:
        self._tasks: dict[str, dict] = {}
        # 每个任务一个通知器，用于 SSE 生成器等待新事件
        self._notifiers: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------ #
    # 任务生命周期
    # ------------------------------------------------------------------ #

    def create_task(
        self,
        folder_path: Optional[str] = None,
        paper_ids: Optional[list[str]] = None,
        research_direction: Optional[str] = None,
    ) -> str:
        """创建新任务，返回 task_id（uuid）

        Args:
            folder_path: 待分析的 PDF 文件夹路径（与 paper_ids 二选一）
            paper_ids: 上传论文 ID 列表（与 folder_path 二选一）
            research_direction: 用户研究方向（可选）

        Returns:
            新生成的 task_id
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        self._tasks[task_id] = {
            "task_id": task_id,
            "folder_path": folder_path or "",
            "paper_ids": paper_ids or [],
            "research_direction": research_direction or "",
            "status": "pending",
            "progress": 0.0,
            "current_stage": None,
            "result": None,
            "error": None,
            "events": [],
            "created_at": now,
            "updated_at": now,
        }
        self._notifiers[task_id] = asyncio.Event()
        logger.info(
            "创建任务: task_id=%s, folder=%s, paper_ids=%d, direction=%s",
            task_id, folder_path or "N/A", len(paper_ids or []),
            "有" if research_direction else "无",
        )
        return task_id

    def update_task(self, task_id: str, **kwargs: Any) -> None:
        """更新任务状态字段（任意关键字参数）

        Args:
            task_id: 任务 ID
            **kwargs: 需更新的字段，如 status / progress / current_stage / result / error
        """
        task = self._tasks.get(task_id)
        if task is None:
            logger.warning("更新任务失败：task_id=%s 不存在", task_id)
            return
        task.update(kwargs)
        task["updated_at"] = datetime.now().isoformat()
        # 触发通知器，唤醒等待中的 SSE 生成器
        self._notify(task_id)

    def add_event(self, task_id: str, event: dict) -> None:
        """追加进度事件到任务事件历史

        Args:
            task_id: 任务 ID
            event: 进度事件 dict，含 {stage, status, message, progress, payload}
        """
        task = self._tasks.get(task_id)
        if task is None:
            logger.warning("添加事件失败：task_id=%s 不存在", task_id)
            return
        task["events"].append(event)
        task["updated_at"] = datetime.now().isoformat()
        # 触发通知器
        self._notify(task_id)

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务完整状态 dict，不存在返回 None"""
        return self._tasks.get(task_id)

    def get_events(self, task_id: str) -> list[dict]:
        """获取任务进度事件列表，不存在返回空列表"""
        task = self._tasks.get(task_id)
        if task is None:
            return []
        return task.get("events", [])

    def get_notifier(self, task_id: str) -> Optional[asyncio.Event]:
        """获取任务的通知器（供 SSE 生成器 await），不存在返回 None"""
        return self._notifiers.get(task_id)

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #

    def _notify(self, task_id: str) -> None:
        """触发任务通知器，唤醒等待中的 SSE 生成器"""
        notifier = self._notifiers.get(task_id)
        if notifier is not None:
            notifier.set()


# 模块级单例，供路由与后台任务共享
task_manager = TaskManager()
