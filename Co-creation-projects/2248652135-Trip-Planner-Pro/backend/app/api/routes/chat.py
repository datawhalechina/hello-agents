"""旅游AI对话API路由"""
from fastapi import APIRouter, HTTPException, Request
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


@router.post("/sessions/{session_id}/messages", summary="发送消息")
async def send_message(session_id: int, req: ChatSendMessageRequest, request: Request):
    """发送消息并获取AI回复（包含历史上下文）"""
    user = _require_auth(request)
    session = get_chat_session(session_id, user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if not req.content.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. 保存用户消息
    add_chat_message(session_id, "user", req.content.strip())

    # 2. 获取历史消息（作为上下文）
    history = get_chat_messages(session_id)

    # 3. 调用旅游 AI 获取回复
    travel_chat = get_travel_chat_service()
    try:
        reply = travel_chat.chat(
            user_message=req.content.strip(),
            history=history[:-1],  # 除了刚保存的最后一条（已包含在history里）
        )
    except Exception as e:
        reply = f"抱歉，我暂时无法回答您的问题。错误信息：{str(e)}"

    # 4. 保存 AI 回复
    add_chat_message(session_id, "assistant", reply)

    # 5. 如果这是第一条消息，自动根据内容生成会话标题
    if len(history) <= 1:
        title = _generate_title(req.content.strip())
        update_chat_session_title(session_id, title)

    return {
        "success": True,
        "reply": reply,
    }


def _generate_title(user_message: str) -> str:
    """根据用户第一条消息生成会话标题"""
    # 截取前20个字符作为标题
    title = user_message.strip()[:20]
    if len(user_message) > 20:
        title += "..."
    return title
