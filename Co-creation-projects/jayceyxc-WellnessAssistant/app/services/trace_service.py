"""Trace：对话链路与工具调用步骤的持久化。"""

from __future__ import annotations

import json
import uuid
from contextvars import ContextVar

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models.entities import Trace, TraceStep

MAX_OUTPUT_CHARS = 4000

# 当前请求正在写入的链路 ID，供工具层与 LLM 层共享
current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)


def _clip_text(value: str | None) -> str | None:
    """截断长文本。"""
    if value is None:
        return None
    return value if len(value) <= MAX_OUTPUT_CHARS else value[:MAX_OUTPUT_CHARS] + "..."


def _clip_output(value: object | None) -> dict | None:
    """截断工具输出，同时保持 JSON 列的结构化格式。"""
    if value is None:
        return None
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, default=str)
        if len(text) <= MAX_OUTPUT_CHARS:
            return value
        return {"truncated": True, "preview": text[:MAX_OUTPUT_CHARS] + "..."}
    return {"value": _clip_text(str(value))}


def start_trace(db: Session, session_id: str, user_input: str) -> Trace:
    trace = Trace(
        id=uuid.uuid4().hex,
        session_id=session_id,
        user_input=user_input,
        status="running",
    )
    db.add(trace)
    db.flush()
    return trace


def add_step(
    db: Session,
    trace_id: str,
    step_type: str,
    thought: str | None = None,
    tool_name: str | None = None,
    tool_input: dict | None = None,
    tool_output: dict | None = None,
    error: str | None = None,
    latency_ms: int | None = None,
) -> TraceStep:
    """追加一个链路步骤，step_no 在链路内自增。"""
    current = db.scalar(
        select(func.coalesce(func.max(TraceStep.step_no), 0)).where(
            TraceStep.trace_id == trace_id
        )
    )
    step = TraceStep(
        trace_id=trace_id,
        step_no=(current or 0) + 1,
        step_type=step_type,
        thought=_clip_text(thought),
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=_clip_output(tool_output),
        error=_clip_text(error),
        latency_ms=latency_ms,
    )
    db.add(step)
    db.flush()
    return step


def finish_trace(
    db: Session,
    trace_id: str,
    final_answer: str = "",
    status: str = "success",
    error: str | None = None,
) -> None:
    db.execute(
        update(Trace)
        .where(Trace.id == trace_id)
        .values(
            final_answer=final_answer,
            status=status,
            error=error,
            ended_at=utcnow(),
        )
    )


def get_trace(db: Session, trace_id: str) -> Trace | None:
    return db.get(Trace, trace_id)


def list_steps(db: Session, trace_id: str) -> list[TraceStep]:
    stmt = (
        select(TraceStep)
        .where(TraceStep.trace_id == trace_id)
        .order_by(TraceStep.step_no)
    )
    return list(db.scalars(stmt))


def list_session_traces(
    db: Session, session_id: str | None = None, limit: int = 20
) -> list[Trace]:
    """查询某会话最近完成的对话轮次；session_id 为空时取最近一次会话。"""
    stmt = select(Trace).where(Trace.status == "success")
    if session_id:
        stmt = stmt.where(Trace.session_id == session_id)
    else:
        latest = db.scalar(
            select(Trace.session_id)
            .where(Trace.status == "success")
            .order_by(Trace.started_at.desc())
            .limit(1)
        )
        if not latest:
            return []
        stmt = stmt.where(Trace.session_id == latest)
    stmt = stmt.order_by(Trace.started_at.desc(), Trace.id.desc()).limit(limit)
    return list(reversed(list(db.scalars(stmt))))


def build_session_messages(
    db: Session, session_id: str | None = None, limit: int = 20
) -> dict:
    """将持久化 Trace 还原为前端可直接渲染的 user/assistant 消息列表。"""
    traces = list_session_traces(db, session_id, limit)
    if not traces:
        return {"session_id": session_id or "", "messages": []}

    messages: list[dict] = []
    for trace in traces:
        created_at = trace.started_at.isoformat()
        messages.append(
            {
                "role": "user",
                "content": trace.user_input,
                "trace_id": trace.id,
                "created_at": created_at,
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": trace.final_answer or "（该轮未生成回复）",
                "trace_id": trace.id,
                "created_at": created_at,
            }
        )
    return {"session_id": traces[0].session_id, "messages": messages}
