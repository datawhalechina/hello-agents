"""Agent 调用链路查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import TraceOut, TraceStepOut
from app.services import trace_service

router = APIRouter(prefix="/api", tags=["trace"])


@router.get("/traces/{trace_id}", response_model=TraceOut)
def get_trace(trace_id: str, db: Session = Depends(get_db)) -> TraceOut:
    trace = trace_service.get_trace(db, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="未找到该 Trace")
    steps = trace_service.list_steps(db, trace_id)
    return TraceOut(
        id=trace.id,
        session_id=trace.session_id,
        user_input=trace.user_input,
        final_answer=trace.final_answer,
        status=trace.status,
        error=trace.error,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        steps=[TraceStepOut.model_validate(step) for step in steps],
    )
