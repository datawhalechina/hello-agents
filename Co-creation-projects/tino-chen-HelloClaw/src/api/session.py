"""会话 API 路由"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union, Literal

router = APIRouter(prefix="/session", tags=["session"])


class SessionInfo(BaseModel):
    """会话信息"""
    id: str
    created_at: float
    updated_at: float


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionInfo]


class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    summarize_old: bool = False  # 是否总结旧会话
    old_session_id: Optional[str] = None  # 要总结的旧会话 ID


class SessionCreateResponse(BaseModel):
    """创建会话响应"""
    session_id: str
    message: str = "Session created successfully"
    summary_file: Optional[str] = None  # 如果总结了旧会话，返回总结文件名


class SessionSummaryInfo(BaseModel):
    """会话总结信息"""
    filename: str
    date: str
    slug: str
    size: int
    updated_at: float


class SessionSummaryListResponse(BaseModel):
    """会话总结列表响应"""
    summaries: List[SessionSummaryInfo]


# ==================== OpenAI 标准消息格式 ====================

class ToolCallFunction(BaseModel):
    """工具调用函数"""
    name: str
    arguments: str  # JSON 字符串


class ToolCall(BaseModel):
    """工具调用"""
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    """聊天消息（OpenAI 标准格式）"""
    role: Literal["user", "assistant", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None  # assistant 消息中的工具调用
    tool_call_id: Optional[str] = None  # tool 消息中的调用 ID


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""
    session_id: str
    messages: List[ChatMessage]


def get_agent():
    """获取全局 Agent 实例"""
    from ..main import get_agent as _get_agent
    return _get_agent()


@router.get("/list", response_model=SessionListResponse)
async def list_sessions():
    """获取会话列表

    返回所有会话，按更新时间倒序排列
    """
    agent = get_agent()
    if not agent:
        return SessionListResponse(sessions=[])

    sessions = agent.list_sessions()
    return SessionListResponse(sessions=[
        SessionInfo(
            id=s["id"],
            created_at=s["created_at"],
            updated_at=s["updated_at"]
        )
        for s in sessions
    ])


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest = None):
    """创建新会话

    可选参数：
    - summarize_old: 是否在创建新会话前总结旧会话
    - old_session_id: 要总结的旧会话 ID（如果不指定，则总结最近一个会话）

    返回新会话的 ID
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    request = request or SessionCreateRequest()
    summary_file = None

    # 如果需要总结旧会话
    if request.summarize_old:
        old_session_id = request.old_session_id

        # 如果没有指定旧会话，找最近的一个
        if not old_session_id:
            sessions = agent.list_sessions()
            if sessions:
                old_session_id = sessions[0]["id"]

        # 总结旧会话
        if old_session_id:
            summary_file = await _summarize_session(agent, old_session_id)

    # 创建新会话
    session_id = agent.create_session()

    return SessionCreateResponse(
        session_id=session_id,
        summary_file=summary_file,
        message="Session created successfully" + (f", old session summarized to {summary_file}" if summary_file else "")
    )


async def _summarize_session(agent, session_id: str) -> Optional[str]:
    """总结指定会话

    Args:
        agent: Agent 实例
        session_id: 会话 ID

    Returns:
        总结文件名，如果失败返回 None
    """
    try:
        from ..memory import SessionSummarizer

        # 获取会话历史
        messages = agent.get_session_history(session_id)
        if not messages:
            return None

        # 创建总结器
        summarizer = SessionSummarizer(
            workspace_manager=agent.workspace,
            model_id=agent._model_id,
            api_key=agent._api_key,
            base_url=agent._base_url,
        )

        # 执行总结
        summary_file = await summarizer.summarize_session(
            messages=messages,
            last_n=10,
            session_id=session_id,
        )

        return summary_file

    except Exception as e:
        print(f"⚠️ 会话总结失败: {e}")
        return None


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话详情

    返回会话的基本信息
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    sessions = agent.list_sessions()
    for s in sessions:
        if s["id"] == session_id:
            return SessionInfo(
                id=s["id"],
                created_at=s["created_at"],
                updated_at=s["updated_at"]
            )

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str):
    """获取会话历史消息

    返回会话的所有聊天记录，按照 OpenAI 标准格式
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    raw_messages = agent.get_session_history(session_id)
    if raw_messages is None:
        raw_messages = []

    # 转换为 OpenAI 标准格式
    chat_messages: List[ChatMessage] = []

    for m in raw_messages:
        role = m.get("role", "")
        content = m.get("content", "")
        metadata = m.get("metadata", {})

        if role == "user":
            chat_messages.append(ChatMessage(role="user", content=content))

        elif role == "assistant":
            tool_calls_data = metadata.get("tool_calls")
            if tool_calls_data:
                # 包含工具调用的 assistant 消息
                tool_calls = [
                    ToolCall(
                        id=tc.get("id", ""),
                        type="function",
                        function=ToolCallFunction(
                            name=tc.get("function", {}).get("name", ""),
                            arguments=tc.get("function", {}).get("arguments", "{}")
                        )
                    )
                    for tc in tool_calls_data
                ]
                chat_messages.append(ChatMessage(
                    role="assistant",
                    content=content if content else None,
                    tool_calls=tool_calls
                ))
            elif content:
                # 普通的 assistant 文本消息
                chat_messages.append(ChatMessage(role="assistant", content=content))

        elif role == "tool":
            # tool 消息
            tool_call_id = metadata.get("tool_call_id")
            chat_messages.append(ChatMessage(
                role="tool",
                content=content,
                tool_call_id=tool_call_id
            ))

    return SessionHistoryResponse(
        session_id=session_id,
        messages=chat_messages
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话

    删除指定会话及其历史记录
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    success = agent.delete_session(session_id)
    if success:
        return {"message": "Session deleted successfully", "session_id": session_id}

    raise HTTPException(status_code=404, detail="Session not found")


# ==================== 会话总结 API ====================

@router.get("/summaries/list", response_model=SessionSummaryListResponse)
async def list_session_summaries():
    """获取所有会话总结列表

    返回按日期倒序排列的会话总结
    """
    agent = get_agent()
    if not agent:
        return SessionSummaryListResponse(summaries=[])

    summaries = agent.workspace.list_session_summaries()
    return SessionSummaryListResponse(summaries=[
        SessionSummaryInfo(
            filename=s["filename"],
            date=s["date"],
            slug=s["slug"],
            size=s["size"],
            updated_at=s["updated_at"]
        )
        for s in summaries
    ])


@router.get("/summaries/{filename}")
async def get_session_summary(filename: str):
    """获取会话总结内容

    Args:
        filename: 总结文件名
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    content = agent.workspace.load_session_summary(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Summary not found")

    return {"filename": filename, "content": content}
