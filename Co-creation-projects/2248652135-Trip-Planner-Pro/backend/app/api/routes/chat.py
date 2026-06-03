"""旅游AI对话API路由（SSE流式输出）"""
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from ...models.schemas import ChatSessionResponse, ChatSessionListResponse, ChatMessagesResponse, ChatSendMessageRequest, ChatDeleteResponse
from ...database import (
    create_chat_session, list_chat_sessions, get_chat_session,
    delete_chat_session, add_chat_message, get_chat_messages,
    update_chat_session_title
)
from ...services.travel_chat_service import get_travel_chat_service
from .auth import require_auth

router = APIRouter(prefix="/chat", tags=["旅游AI对话"])


def _require_auth(request: Request) -> dict:
    """统一鉴权"""
    try:
        return require_auth(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="请先登录后再使用AI对话")


@router.post("/sessions", summary="创建新会话")
async def create_session(request: Request):
    """创建一个新的聊天会话"""
    user = _require_auth(request)
    session = create_chat_session(user["id"])
    return ChatSessionResponse(success=True, session=session)


@router.get("/sessions", summary="获取会话列表")
async def list_sessions(request: Request):
    """获取当前用户的所有会话"""
    user = _require_auth(request)
    sessions = list_chat_sessions(user["id"])
    return ChatSessionListResponse(success=True, sessions=sessions)


@router.get("/sessions/{session_id}", summary="获取会话详情")
async def get_session(session_id: int, request: Request):
    """获取单个会话信息"""
    user = _require_auth(request)
    session = get_chat_session(session_id, user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatSessionResponse(success=True, session=session)


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: int, request: Request):
    """删除会话及其所有消息"""
    user = _require_auth(request)
    deleted = delete_chat_session(session_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatDeleteResponse(success=True, message="会话已删除")


@router.get("/sessions/{session_id}/messages", summary="获取会话消息")
async def get_messages(session_id: int, request: Request):
    """获取会话的所有聊天消息"""
    user = _require_auth(request)
    session = get_chat_session(session_id, user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = get_chat_messages(session_id)
    return ChatMessagesResponse(success=True, messages=messages)


@router.post("/sessions/{session_id}/messages", summary="发送消息（流式）")
async def send_message(session_id: int, req: ChatSendMessageRequest, request: Request):
    """
    发送消息并流式获取AI回复（SSE格式）

    流式返回 SSE 事件：
    - data: {"type": "token", "content": "文本片段"}
    - data: {"type": "error", "content": "错误信息"}
    - data: {"type": "done", "title": "更新后的会话标题"}
    """
    user = _require_auth(request)
    session = get_chat_session(session_id, user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. 保存用户消息
    add_chat_message(session_id, "user", content)

    # 2. 获取历史消息（作为上下文）
    history = get_chat_messages(session_id)

    # 3. 返回流式响应
    return StreamingResponse(
        _stream_ai_response(session_id, content, history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


async def _stream_ai_response(session_id: int, content: str, history: list):
    """流式生成AI回复的SSE事件"""
    travel_chat = get_travel_chat_service()
    full_response = ""

    try:
        # 获取流式生成器
        stream = travel_chat.chat_stream(
            user_message=content,
            history=history[:-1],  # 排除刚保存的最后一条
        )

        for chunk in stream:
            if chunk:
                full_response += chunk
                # 发送 token 事件
                yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

        # 流式完成 - 保存AI回复到数据库
        add_chat_message(session_id, "assistant", full_response)

        # 如果是第一条消息，自动生成会话标题
        title = None
        if len(history) <= 1:
            title = _generate_title(content)
            update_chat_session_title(session_id, title)

        # 发送完成事件
        done_event = {"type": "done"}
        if title:
            done_event["title"] = title
        yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

    except Exception as e:
        error_msg = f"抱歉，AI暂时无法回答您的问题，请稍后重试。"
        # 尝试发送错误事件
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"


def _generate_title(user_message: str) -> str:
    """根据用户第一条消息生成会话标题"""
    title = user_message.strip()[:20]
    if len(user_message) > 20:
        title += "..."
    return title
