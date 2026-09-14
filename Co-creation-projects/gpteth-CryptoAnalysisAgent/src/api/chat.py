"""Chat API with SSE streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .deps import get_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    session_id: Optional[str] = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/send/sync", response_model=ChatResponse)
def send_sync(request: ChatRequest):
    agent = get_agent()
    session_id = request.session_id
    content = ""
    for event in agent.iter_events(request.message, session_id):
        if event["type"] == "session":
            session_id = event.get("session_id") or session_id
        elif event["type"] == "done":
            content = event.get("content") or content
            session_id = event.get("session_id") or session_id
        elif event["type"] == "error":
            content = f"错误: {event.get('error')}"
    return ChatResponse(content=content, session_id=session_id)


@router.post("/send/stream")
async def send_stream(request: ChatRequest):
    agent = get_agent()

    async def generate():
        iterator = agent.iter_events(request.message, request.session_id)
        while True:
            event = await asyncio.to_thread(next, iterator, None)
            if event is None:
                break
            kind = event.get("type")
            if kind == "session":
                yield _sse("session", {"session_id": event.get("session_id")})
            elif kind == "step_start":
                yield _sse("step_start", {"step": event.get("step"), "max_steps": event.get("max_steps")})
            elif kind == "thought":
                yield _sse("thought", {"content": event.get("content", "")})
            elif kind == "chunk":
                yield _sse("chunk", {"content": event.get("content", "")})
            elif kind == "tool_start":
                yield _sse("tool_start", {"tool": event.get("tool"), "args": event.get("args") or {}})
            elif kind == "tool_finish":
                yield _sse("tool_finish", {"tool": event.get("tool"), "result": event.get("result", "")})
            elif kind == "step_finish":
                yield _sse("step_finish", {"step": event.get("step")})
            elif kind == "done":
                yield _sse("done", {"content": event.get("content", ""), "session_id": event.get("session_id")})
            elif kind == "error":
                yield _sse("error", {"error": event.get("error", "未知错误")})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/send")
def send_compat(request: ChatRequest):
    return send_sync(request)
