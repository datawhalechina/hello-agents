from io import BytesIO
from uuid import uuid4
import asyncio

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from memory.store import get_report_run, list_report_runs_for_user
from service.observability_views import build_report_observability
from service.health_analysis import HealthAnalysisService

router = APIRouter()


class HealthRequest(BaseModel):
    report_text: str
    user_id: str = Field(..., min_length=1, max_length=256)

    @field_validator("user_id")
    @classmethod
    def normalize_user_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("user_id 不能为空")
        return v


@router.post("/health/analysis")
async def analysis_health(request: HealthRequest):
    task_id = str(uuid4())

    service = HealthAnalysisService(task_id=task_id, user_id=request.user_id)
    asyncio.create_task(service.run(request.report_text, request.user_id))

    return {"task_id": task_id, "user_id": request.user_id}


@router.post("/health/analysis/pdf")
async def analysis_health_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    uid = user_id.strip()
    if not uid:
        return {"error": "user_id 不能为空"}

    contents = await file.read()

    text = ""

    with pdfplumber.open(BytesIO(contents)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if not text.strip():
        return {"error": "无法从PDF中提取文本"}

    task_id = str(uuid4())
    service = HealthAnalysisService(task_id=task_id, user_id=uid)

    asyncio.create_task(service.run(text, uid))

    return {"task_id": task_id, "user_id": uid}

@router.get("/health/task_status/{task_id}")
async def task_status(task_id: str):
    from agents.base import get_task_status

    status = get_task_status(task_id)
    if not status:
        return {"error": "task not found"}

    return status


@router.get("/health/users/{user_id}/report_history")
async def report_history(user_id: str, limit: int = 50):
    uid = user_id.strip()
    if not uid:
        return {"error": "user_id 无效", "items": []}
    items = list_report_runs_for_user(uid, limit=limit)
    return {"user_id": uid, "items": items}


@router.get("/health/report_runs/{task_id}")
async def report_run_detail(task_id: str):
    row = get_report_run(task_id)
    if not row:
        return {"error": "未找到该次分析记录（可能尚未落库或 task_id 无效）"}
    return row


@router.get("/health/report_runs/{task_id}/observability")
async def report_run_observability(
    task_id: str, include_raw_trace: bool = False
):
    """
    阶段 3：体检分析可观测性 — 各 Agent trace 已随 report_runs 持久化（新产生任务）。
    `include_raw_trace=true` 时返回完整 trace（体积可能较大）。
    """
    row = get_report_run(task_id.strip())
    if not row:
        raise HTTPException(status_code=404, detail="未找到该次分析记录")
    return build_report_observability(row, include_raw_trace=include_raw_trace)