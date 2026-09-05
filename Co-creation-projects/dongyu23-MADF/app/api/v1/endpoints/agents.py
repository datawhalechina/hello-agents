from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
import logging
from pydantic import BaseModel

from app.db.session import get_db
from app.schemas import MessageResponse
from app.crud import create_message, get_forum_messages
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory

router = APIRouter()
logger = logging.getLogger(__name__)

class AgentChatRequest(BaseModel):
    agent_name: str
    persona_json: dict
    context_messages: List[dict]
    theme: str = "AI对未来的影响"

class AgentChatResponse(BaseModel):
    content: str
    thought: Optional[dict] = None

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest):
    """
    Directly invoke an agent to think and speak based on provided context.
    This is a stateless endpoint wrapper around the ParticipantAgent logic.
    """
    # 1. Reconstruct Agent
    try:
        agent = ParticipantAgent(
            name=request.agent_name, 
            persona=request.persona_json, 
            n_participants=3, # Default, doesn't affect single-turn much
            theme=request.theme
        )
    except Exception:
        logger.exception("Failed to initialize agent")
        raise HTTPException(status_code=400, detail="Failed to initialize agent")

    # 2. Reconstruct Context
    # We need to convert the list of dicts into the string format expected by agent.think/speak
    # Or better, use SharedMemory to generate it if we want to reuse logic exactly.
    memory = SharedMemory(n_participants=3)
    for msg in request.context_messages:
        memory.add_message(msg.get("speaker", "Unknown"), msg.get("content", ""))
    
    context_str = memory.get_context_str()

    # 3. Think
    thought = agent.think(context_str)
    
    if not thought:
        raise HTTPException(status_code=500, detail="Agent failed to think")

    # 4. Speak
    # If agent decides to listen, we return empty content but include thought
    if thought.get("action") == "listen":
        return AgentChatResponse(content="", thought=thought)

    # If speaking
    response_stream = agent.speak(thought, context_str)
    
    full_content = ""
    if response_stream:
        for token in response_stream:
            if token:
                full_content += token
    
    return AgentChatResponse(content=full_content, thought=thought)
