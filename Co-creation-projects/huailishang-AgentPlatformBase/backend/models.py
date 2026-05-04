from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentKind(str, Enum):
    chat = "chat"
    planner = "planner"
    research = "research"
    tool = "tool"


class AgentProfile(BaseModel):
    agent_id: str
    name: str
    kind: AgentKind
    description: str
    system_prompt: str = ""
    tools: List[str] = Field(default_factory=list)
    memory_policy: str = "session"
    enabled: bool = True


class AgentRequest(BaseModel):
    input: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None


class AgentResponse(BaseModel):
    agent_id: str
    output: str
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    agent_id: str = "general_chat"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    input: str
    agent_id: str
    status: TaskStatus = TaskStatus.pending
    output: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BatchRunRequest(BaseModel):
    requests: Dict[str, AgentRequest] = Field(
        ...,
        description="Mapping from agent_id to request payload.",
    )
