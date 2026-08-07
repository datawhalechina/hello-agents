"""
FastAPI 路由层 - 英语句子扩写智能体
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.entities import (
    StartRequest,
    SubmitRequest,
    AgentResponse,
    SessionState
)
from services.session_store import get_session_store
from agents.orchestrator import get_orchestrator
from agents.auto_mode_agent import get_auto_mode

router = APIRouter(prefix="/api", tags=["expand"])


@router.post("/session/start", response_model=AgentResponse)
async def start_session(request: StartRequest) -> AgentResponse:
    """
    创建新会话，返回第一阶段提问
    
    Args:
        request: 开始会话请求，包含种子句和模式
        
    Returns:
        AgentResponse: 智能体响应
    """
    # 获取会话存储
    session_store = get_session_store()
    
    # 创建会话
    session = session_store.create_session(
        seed_sentence=request.seed_sentence,
        mode=request.mode
    )
    
    # 获取 Orchestrator
    orchestrator = get_orchestrator()
    
    # 开始会话
    response = orchestrator.start_session(session)
    
    return response


@router.post("/session/submit", response_model=AgentResponse)
async def submit_sentence(request: SubmitRequest) -> AgentResponse:
    """
    提交用户扩写句子，返回点评和下一阶段提问（手动模式）
    
    Args:
        request: 提交请求，包含会话 ID 和用户句子
        
    Returns:
        AgentResponse: 智能体响应
    """
    # 获取会话存储
    session_store = get_session_store()
    
    # 获取会话
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 获取 Orchestrator
    orchestrator = get_orchestrator()
    
    # 处理用户输入
    response = orchestrator.process_user_input(
        session_state=session,
        user_sentence=request.user_sentence
    )
    
    # 更新会话
    session_store.update_session(session)
    
    return response


@router.get("/session/{session_id}/auto")
async def auto_mode_stream(session_id: str) -> StreamingResponse:
    """
    SSE 流式推送三轮自动演示
    
    Args:
        session_id: 会话 ID
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    # 获取会话存储
    session_store = get_session_store()
    
    # 获取会话
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 获取 AutoModeAgent
    auto_mode_agent = get_auto_mode()
    
    # 生成流式响应
    async def event_generator() -> AsyncGenerator[str, None]:
        import json
        try:
            # 使用流式运行
            async for event in auto_mode_agent.run_auto_mode_stream(session.seed_sentence):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            # 发送结束事件
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e), 'type': type(e).__name__}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    """
    获取当前会话完整状态
    
    Args:
        session_id: 会话 ID
        
    Returns:
        SessionState: 会话状态
    """
    # 获取会话存储
    session_store = get_session_store()
    
    # 获取会话
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session
