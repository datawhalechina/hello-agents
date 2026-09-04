"""
会话管理 REST API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session.session_store import (
    list_sessions, delete_session, get_session_info, session_exists,
    load_session_messages, save_session_messages, load_session_todos,
)
from tool.logger_handler import logger

router = APIRouter()


class CreateSessionRequest(BaseModel):
    name: str = ""


class SessionInfo(BaseModel):
    session_id: str
    title: str = ""              # 会话标题（存储标题，或首条用户消息截断，空会话为 ""）
    message_count: int
    user_message_count: int = 0  # 仅统计内容非空的用户消息
    created_at: str | None = None
    updated_at: str | None = None
    size_bytes: int | None = None
    size_human: str | None = None


@router.get("/sessions")
async def api_list_sessions():
    """列出所有会话（按创建时间倒序）"""
    sessions = list_sessions()
    return {"sessions": sessions}


@router.post("/sessions")
async def api_create_session(req: CreateSessionRequest):
    """创建新会话"""
    from Agent import Agent

    agent = Agent()  # ephemeral Agent，无 session_id
    sid = agent.new_session(req.name or "默认会话")
    return {"session_id": sid}


@router.get("/sessions/{session_id}")
async def api_get_session(session_id: str):
    """获取会话详情"""
    info = get_session_info(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"会话 [{session_id}] 不存在")
    return info


@router.delete("/sessions/{session_id}")
async def api_delete_session(session_id: str):
    """删除会话（同时驱逐 Agent 缓存，防止删除后被断连保存逻辑复活）"""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"会话 [{session_id}] 不存在")
    from api.chat import evict_agent
    evict_agent(session_id)
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除会话失败")
    return {"deleted": session_id}


@router.get("/sessions/{session_id}/messages")
async def api_get_messages(session_id: str, offset: int = 0, limit: int = 50):
    """获取会话消息历史（分页）"""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"会话 [{session_id}] 不存在")
    messages = load_session_messages(session_id)
    if messages is None:
        return {"messages": [], "total": 0}
    total = len(messages)
    page = messages[offset: offset + limit]
    # 序列化为 JSON 兼容格式
    from session.session_store import serialize_message
    serialized = []
    for msg in page:
        record = serialize_message(msg)
        serialized.append(record)
    # 附上会话当前的 todo 状态，供前端历史回显待办面板
    todos_state = load_session_todos(session_id)
    todos = todos_state[0] if todos_state else []
    return {"messages": serialized, "total": total, "todos": todos}
