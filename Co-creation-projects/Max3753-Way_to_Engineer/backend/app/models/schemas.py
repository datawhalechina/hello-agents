"""数据模型"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: datetime = datetime.now()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # 学习上下文


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str
    conversation_id: str
    agent_name: str = "编程导师"
