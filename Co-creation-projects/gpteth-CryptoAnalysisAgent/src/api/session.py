"""Session CRUD."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .deps import get_sessions

router = APIRouter(prefix="/session", tags=["session"])


class SessionInfo(BaseModel):
    id: str
    title: str = "会话"
    created_at: float
    updated_at: float


class ChatMessage(BaseModel):
    role: str
    content: str = ""
    metadata: Optional[dict] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    message: str = "Session created successfully"


@router.get("/list")
def list_sessions():
    return {"sessions": get_sessions().list()}


@router.post("/create", response_model=SessionCreateResponse)
def create_session():
    session_id = get_sessions().create()
    return SessionCreateResponse(session_id=session_id)


@router.get("/{session_id}")
def get_session(session_id: str):
    data = get_sessions().get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(
        id=data["id"],
        title=data.get("title") or "会话",
        created_at=data.get("created_at") or 0,
        updated_at=data.get("updated_at") or 0,
    )


@router.get("/{session_id}/history")
def get_history(session_id: str):
    messages = get_sessions().history(session_id)
    return {
        "session_id": session_id,
        "messages": [
            ChatMessage(
                role=m.get("role", "assistant"),
                content=m.get("content") or "",
                metadata=m.get("metadata"),
            )
            for m in messages
        ],
    }


@router.delete("/{session_id}")
def delete_session(session_id: str):
    if not get_sessions().delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully", "session_id": session_id}
