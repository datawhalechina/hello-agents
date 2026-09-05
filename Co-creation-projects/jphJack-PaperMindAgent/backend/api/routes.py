"""FastAPI 路由：分析任务提交、SSE 进度推送、报告查询、健康检查、论文上传与管理

后台分析用 asyncio.create_task 启动，不阻塞 API 响应；
SSE 用 sse_starlette.EventSourceResponse，从 task_manager 事件历史推送。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.agents.report_agent import ReportAgent
from backend.api.tasks import task_manager
from backend.config import settings
from backend.evaluator.evaluator import Evaluator
from backend.llm.client import DeepSeekClient
from backend.memory.manager import MemoryManager
from backend.orchestrator.workflow import WorkflowOrchestrator
from backend.storage.paper_library import compute_paper_id, get_paper_library
from backend.tools.registry import build_default_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["paper-innovation"])


# ---------------------------------------------------------------------- #
# 请求模型
# ---------------------------------------------------------------------- #

class AnalyzeRequest(BaseModel):
    """POST /api/analyze 请求体"""
    folder_path: Optional[str] = Field(default=None, description="待分析的 PDF 文件夹路径（与 paper_ids 二选一）")
    paper_ids: Optional[list[str]] = Field(default=None, description="上传论文 ID 列表（与 folder_path 二选一）")
    research_direction: Optional[str] = Field(default=None, description="用户研究方向（可选）")


# ---------------------------------------------------------------------- #
# 后台分析函数
# ---------------------------------------------------------------------- #

async def run_analysis(
    task_id: str,
    folder_path: Optional[str] = None,
    paper_ids: Optional[list[str]] = None,
    research_direction: Optional[str] = None,
) -> None:
    """后台分析主流程：编排工作流 → 生成报告 → 生成评估 → 更新任务状态

    Args:
        task_id: 任务 ID
        folder_path: PDF 文件夹路径（与 paper_ids 二选一）
        paper_ids: 上传论文 ID 列表（与 folder_path 二选一）
        research_direction: 用户研究方向（可选）
    """
    logger.info(
        "启动后台分析: task_id=%s, folder=%s, paper_ids=%d, direction=%s",
        task_id, folder_path or "N/A", len(paper_ids or []),
        "有" if research_direction else "无",
    )
    try:
        # 标记为运行中
        task_manager.update_task(
            task_id, status="running", progress=0.0, current_stage=None
        )

        # 初始化组件：DeepSeek 客户端 + 工具注册表 + 记忆管理器
        client = DeepSeekClient()
        registry = build_default_registry()
        memory = MemoryManager()
        orchestrator = WorkflowOrchestrator(client, registry, memory)

        # 进度回调：更新任务状态 + 追加事件
        async def progress_callback(
            stage: str,
            status: str,
            message: str,
            progress: float,
            payload: Optional[dict] = None,
        ) -> None:
            task_manager.update_task(
                task_id, progress=progress, current_stage=stage
            )
            task_manager.add_event(
                task_id,
                {
                    "stage": stage,
                    "status": status,
                    "message": message,
                    "progress": progress,
                    "payload": payload,
                },
            )

        # 执行工作流流水线
        _t_pipe0 = time.perf_counter()
        pipeline_output = await orchestrator.run_pipeline(
            folder_path=folder_path,
            paper_ids=paper_ids,
            research_direction=research_direction,
            progress_callback=progress_callback,
        )
        logger.info("[task timing] run_pipeline: %.2fs", time.perf_counter() - _t_pipe0)
        final_results = pipeline_output.get("final_results", {}) or {}
        evaluation_data = pipeline_output.get("evaluation_data", {}) or {}

        # 用 ReportAgent 生成最终报告
        _t_rep0 = time.perf_counter()
        report_agent = ReportAgent(client=client)
        report = await report_agent.generate_report(final_results)
        logger.info("[task timing] ReportAgent.generate_report: %.2fs", time.perf_counter() - _t_rep0)

        # 用 Evaluator 生成评估
        _t_eval0 = time.perf_counter()
        evaluator = Evaluator(client=client)
        evaluation = await evaluator.evaluate(
            final_results,
            evaluation_data.get("tool_call_records", []),
            evaluation_data.get("confidence_stats", {}),
        )
        logger.info("[task timing] Evaluator.evaluate: %.2fs", time.perf_counter() - _t_eval0)

        # 存储最终结果，标记完成
        task_manager.update_task(
            task_id,
            status="completed",
            progress=1.0,
            result={
                "markdown": report.get("markdown", ""),
                "report": report,
                "evaluation": evaluation,
            },
        )
        logger.info("[task timing] 任务完成: task_id=%s", task_id)

    except Exception as exc:
        logger.error(
            "任务失败: task_id=%s, error=%s", task_id, exc, exc_info=True
        )
        task_manager.update_task(task_id, status="failed", error=str(exc))


# ---------------------------------------------------------------------- #
# 路由
# ---------------------------------------------------------------------- #

@router.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict:
    """提交分析任务：创建 task_id 并后台启动，立即返回 task_id

    Args:
        request: 含 folder_path 或 paper_ids + 可选 research_direction 的请求体

    Returns:
        {"task_id": str}
    """
    # 校验：folder_path 与 paper_ids 至少提供一个
    if not request.folder_path and not request.paper_ids:
        raise HTTPException(
            status_code=400,
            detail="必须提供 folder_path 或 paper_ids 之一",
        )

    # 创建任务
    task_id = task_manager.create_task(
        folder_path=request.folder_path,
        paper_ids=request.paper_ids,
        research_direction=request.research_direction,
    )

    # 后台启动分析（不阻塞响应）
    asyncio.create_task(
        run_analysis(
            task_id,
            folder_path=request.folder_path,
            paper_ids=request.paper_ids,
            research_direction=request.research_direction,
        )
    )

    return {"task_id": task_id}


# ---------------------------------------------------------------------- #
# 论文上传与管理
# ---------------------------------------------------------------------- #

@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)) -> dict:
    """上传 PDF 论文

    保存到 data/uploads/{paper_id}.pdf，注册到论文库。
    同一文件重复上传返回 duplicate=true。

    Args:
        file: PDF 文件

    Returns:
        {"paper_id": str, "filename": str, "duplicate": bool}
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    # 保存到临时文件以计算内容哈希
    tmp_path = settings.UPLOADS_DIR / f"tmp_{file.filename}"
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 计算内容哈希作为 paper_id
        paper_id = compute_paper_id(str(tmp_path))

        # 检查是否已存在
        library = get_paper_library()
        existing = library.get(paper_id)
        duplicate = existing is not None

        # 移动到正式存储路径
        final_path = settings.UPLOADS_DIR / f"{paper_id}.pdf"
        if not final_path.exists():
            shutil.move(str(tmp_path), str(final_path))
        else:
            # 已存在同名文件，删除临时文件
            tmp_path.unlink(missing_ok=True)

        # 注册到论文库
        library.register(
            paper_id=paper_id,
            filename=file.filename,
            source="upload",
            original_path=str(final_path),
        )

        logger.info("上传论文: paper_id=%s, filename=%s, duplicate=%s", paper_id[:12], file.filename, duplicate)
        return {
            "paper_id": paper_id,
            "filename": file.filename,
            "duplicate": duplicate,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("上传论文失败: %s", exc, exc_info=True)
        # 清理临时文件
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {exc}")


@router.get("/papers")
async def list_papers() -> dict:
    """列出论文库全部论文及预处理状态

    Returns:
        {"papers": [PaperMetadata]}
    """
    library = get_paper_library()
    papers = library.list_all()
    return {"papers": papers}


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str) -> dict:
    """删除论文：移除库记录 + 缓存文件 + Chroma chunks + 上传原文件

    Args:
        paper_id: 论文 ID

    Returns:
        {"deleted": bool, "paper_id": str}
    """
    library = get_paper_library()
    deleted = library.delete(paper_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"论文 {paper_id} 不存在")
    return {"deleted": True, "paper_id": paper_id}


@router.get("/progress/{task_id}")
async def progress(task_id: str) -> EventSourceResponse:
    """SSE 流：推送任务进度事件，任务结束时推送 done 事件并关闭

    Args:
        task_id: 任务 ID

    Returns:
        EventSourceResponse：逐条推送 {stage, status, message, progress, payload}
    """
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    async def event_generator():
        """SSE 事件生成器：从事件历史增量推送，任务结束发 done"""
        last_index = 0
        while True:
            # 1. 排空所有未发送事件
            events = task_manager.get_events(task_id)
            while last_index < len(events):
                event = events[last_index]
                last_index += 1
                yield {
                    "event": "progress",
                    "data": json.dumps(event, ensure_ascii=False, default=str),
                }

            # 2. 检查任务是否结束
            current = task_manager.get_task(task_id)
            if current is None:
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"message": "任务不存在"}, ensure_ascii=False
                    ),
                }
                return
            if current["status"] in ("completed", "failed"):
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "status": current["status"],
                            "task_id": task_id,
                            "progress": current.get("progress", 0.0),
                            "error": current.get("error"),
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                }
                return

            # 3. 清除通知标志后再次检查事件，避免竞态漏推
            notifier = task_manager.get_notifier(task_id)
            if notifier is not None:
                notifier.clear()
                # 清除后若有新事件，回到循环顶部发送
                events = task_manager.get_events(task_id)
                if last_index < len(events):
                    continue
                # 等待新事件到达（带超时作为 keepalive）
                try:
                    await asyncio.wait_for(notifier.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    # 超时发送 keepalive 注释，保持连接
                    yield {"comment": "keepalive"}
            else:
                # 无通知器则短睡后重试
                await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator(), ping=15)


@router.get("/report/{task_id}")
async def report(task_id: str) -> dict:
    """获取最终报告

    Args:
        task_id: 任务 ID

    Returns:
        {markdown, report, evaluation, status}
    """
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    status = task.get("status")
    result = task.get("result") or {}

    if status == "completed":
        return {
            "markdown": result.get("markdown", ""),
            "report": result.get("report", {}),
            "evaluation": result.get("evaluation", {}),
            "status": status,
        }
    elif status == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"任务失败: {task.get('error', '未知错误')}",
        )
    else:
        # pending / running：返回当前进度状态
        return {
            "markdown": "",
            "report": {},
            "evaluation": {},
            "status": status,
            "progress": task.get("progress", 0.0),
            "current_stage": task.get("current_stage"),
        }


@router.get("/tasks/{task_id}")
async def task_status(task_id: str) -> dict:
    """获取任务状态

    Args:
        task_id: 任务 ID

    Returns:
        {task_id, status, progress, current_stage}
    """
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return {
        "task_id": task_id,
        "status": task.get("status", "pending"),
        "progress": task.get("progress", 0.0),
        "current_stage": task.get("current_stage"),
    }


@router.get("/health")
async def health() -> dict:
    """健康检查"""
    return {"status": "ok", "model": settings.DEEPSEEK_MODEL}
