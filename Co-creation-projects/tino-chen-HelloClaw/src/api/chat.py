"""聊天 API 路由"""
import json
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    session_id: Optional[str] = None


def get_agent():
    """获取全局 Agent 实例"""
    from ..main import get_agent as _get_agent
    return _get_agent()


@router.post("/send/sync", response_model=ChatResponse)
async def send_message_sync(request: ChatRequest):
    """发送消息并获取同步响应"""
    agent = get_agent()
    if not agent:
        return ChatResponse(content="Agent not initialized", session_id=request.session_id)

    response = agent.chat(request.message, request.session_id)
    return ChatResponse(content=response, session_id=request.session_id)


@router.post("/send/stream")
async def send_message_stream(request: ChatRequest):
    """发送消息并获取流式响应 (SSE)

    事件类型：
    - session: 会话信息（包含 session_id）
    - step_start: 步骤开始
    - chunk: LLM 文本块
    - tool_start: 工具调用开始
    - tool_finish: 工具调用结束
    - step_finish: 步骤结束
    - done: 完成
    - error: 错误
    """

    async def event_generator():
        agent = get_agent()
        if not agent:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Agent not initialized"}, ensure_ascii=False)
            }
            return

        try:
            async for event in agent.achat(request.message, request.session_id):
                event_type = event.type.value
                event_data = event.data

                # 处理不同类型的事件
                if event_type == "agent_start":
                    # 发送会话信息
                    session_id = getattr(agent, '_current_session_id', None)
                    yield {
                        "event": "session",
                        "data": json.dumps({"session_id": session_id}, ensure_ascii=False)
                    }

                elif event_type == "step_start":
                    # 步骤开始
                    yield {
                        "event": "step_start",
                        "data": json.dumps({
                            "step": event_data.get("step", 1),
                            "max_steps": event_data.get("max_steps", 10)
                        }, ensure_ascii=False)
                    }

                elif event_type == "llm_chunk":
                    # LLM 文本块
                    chunk = event_data.get("chunk", "")
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": chunk}, ensure_ascii=False)
                    }

                elif event_type == "tool_call_start":
                    # 工具调用开始
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({
                            "tool": event_data.get("tool_name", ""),
                            "args": event_data.get("args", {})
                        }, ensure_ascii=False)
                    }

                elif event_type == "tool_call_finish":
                    # 工具调用结束
                    yield {
                        "event": "tool_finish",
                        "data": json.dumps({
                            "tool": event_data.get("tool_name", ""),
                            "result": event_data.get("result", "")
                        }, ensure_ascii=False)
                    }

                elif event_type == "step_finish":
                    # 步骤结束
                    yield {
                        "event": "step_finish",
                        "data": json.dumps({
                            "step": event_data.get("step", 1)
                        }, ensure_ascii=False)
                    }

                elif event_type == "agent_finish":
                    # Agent 完成，保存会话
                    session_id = agent.save_current_session()
                    final_content = event_data.get("result", "")

                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "content": final_content,
                            "session_id": session_id
                        }, ensure_ascii=False)
                    }

                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": event_data.get("error", "Unknown error")}, ensure_ascii=False)
                    }

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


@router.post("/send")
async def send_message(request: ChatRequest):
    """发送消息（暂返回同步响应）"""
    return await send_message_sync(request)
