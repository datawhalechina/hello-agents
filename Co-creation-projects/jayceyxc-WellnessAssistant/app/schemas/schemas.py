"""API 请求/响应模型，同时作为工具参数校验的参考定义。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    trace_id: str
    session_id: str


class HealthRecordOut(ORMModel):
    id: int
    metric_type: str
    value: float
    unit: str
    recorded_at: datetime
    source: str
    note: str | None


class TrendPoint(BaseModel):
    date: str
    value: float
    unit: str


class TrendOut(BaseModel):
    metric_type: str
    unit: str
    points: list[TrendPoint]


class PlanOut(ORMModel):
    plan_id: str
    version: int
    status: str
    goal: str
    content: dict
    reason: str
    created_at: datetime


class TraceStepOut(ORMModel):
    id: int
    step_no: int
    step_type: str
    thought: str | None
    tool_name: str | None
    tool_input: dict | None
    tool_output: dict | None
    error: str | None
    latency_ms: int | None
    created_at: datetime


class TraceOut(ORMModel):
    id: str
    session_id: str
    user_input: str
    final_answer: str
    status: str
    error: str | None
    started_at: datetime
    ended_at: datetime | None
    steps: list[TraceStepOut] = Field(default_factory=list)


class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    trace_id: str | None = None
    created_at: datetime | None = None


class ChatHistoryOut(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage]


class ServiceHealth(BaseModel):
    status: str
    app: str
    llm_model: str
    llm_provider: str
    database: str
