"""聊天API"""

from fastapi import APIRouter, Query
from ...models.schemas import ChatRequest, ChatResponse
from ...agents.orchestrator import get_orchestrator
from ...services.data_store import data_store
from ...models.learning import UserProgress
from datetime import datetime
import uuid

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Query("default")):
    """与AI助手对话（自动路由到合适的Agent）"""
    orchestrator = get_orchestrator()
    
    # 生成会话ID
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # 路由到合适的Agent并获取回复（传递上下文）
    reply, agent_name = orchestrator.route(request.message, context=request.context)
    
    # 如果是教练回应，保存为学习计划到用户进度
    if agent_name == "coach":
        progress = data_store.get_user_progress(user_id)
        if not progress:
            progress = UserProgress(
                user_id=user_id,
                started_at=datetime.now(),
                last_activity_at=datetime.now()
            )
        progress.learning_plan = reply
        progress.last_activity_at = datetime.now()
        data_store.save_user_progress(progress)
    
    # 映射agent名称到中文
    agent_display_name = {
        "tutor": "编程导师",
        "debug": "调试助手",
        "review": "代码审查员",
        "arch": "架构师",
        "coach": "学习教练",
    }.get(agent_name, "编程导师")
    
    return ChatResponse(
        reply=reply,
        conversation_id=conversation_id,
        agent_name=agent_display_name,
    )
