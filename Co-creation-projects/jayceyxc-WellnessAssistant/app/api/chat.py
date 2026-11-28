"""对话接口：编排 ReAct Agent 与 Trace 落库。"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agent.wellness_agent import get_agent
from app.core.config import settings
from app.core.database import get_db
from app.schemas.schemas import ChatHistoryOut, ChatRequest, ChatResponse
from app.services import trace_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/history", response_model=ChatHistoryOut)
def chat_history(
    session_id: str | None = Query(default=None, description="留空则恢复最近一次会话"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ChatHistoryOut:
    """从持久化的 Trace 中还原聊天记录，供刷新页面或切换标签后恢复。"""
    return ChatHistoryOut(**trace_service.build_session_messages(db, session_id, limit))


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session_id = request.session_id or uuid.uuid4().hex
    trace = None
    if settings.trace_enabled:
        trace = trace_service.start_trace(db, session_id, request.message)
        trace_service.add_step(
            db, trace.id, "user_input", thought=f"用户输入：{request.message}"
        )
        db.commit()

    token = trace_service.current_trace_id.set(trace.id if trace else None)
    try:
        reply = get_agent().run(request.message)
        if settings.disclaimer not in reply:
            reply = f"{reply}\n\n{settings.disclaimer}"
        if trace:
            trace_service.add_step(
                db, trace.id, "final_answer", thought=reply
            )
            trace_service.finish_trace(db, trace.id, reply, "success")
            db.commit()
        return ChatResponse(
            reply=reply,
            trace_id=trace.id if trace else "",
            session_id=session_id,
        )
    except Exception as exc:
        logger.exception("Agent 调用失败")
        if trace:
            trace_service.add_step(db, trace.id, "error", error=str(exc))
            trace_service.finish_trace(db, trace.id, "", "error", str(exc))
            db.commit()
        raise HTTPException(status_code=502, detail=f"智能体调用失败：{exc}") from exc
    finally:
        trace_service.current_trace_id.reset(token)
