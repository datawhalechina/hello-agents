import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.mermaid_agent_service import MermaidAgentService
from app.models.schemas import AgentChatRequest


router = APIRouter(prefix="/api", tags=["agent"])
agent_service = MermaidAgentService()


@router.post("/agent/chat/stream")
async def stream_agent_chat(payload: AgentChatRequest):
    async def event_generator():
        try:
            async for event in agent_service.stream_chat(payload.mode, payload.prompt, payload.direction):
                yield f"event: {event.get('type', 'message')}\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            error_event = {"type": "error", "message": f"流式服务异常: {str(exc)}"}
            yield "event: error\n"
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            yield "event: done\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
