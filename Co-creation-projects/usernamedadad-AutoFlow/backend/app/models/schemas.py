from typing import Literal, Optional
from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    text: str = Field(..., description="按行输入的计划文本")
    direction: Literal["TD", "LR"] = "TD"


class PlanResponse(BaseModel):
    mermaid_code: str


class AgentChatRequest(BaseModel):
    mode: Literal["standard", "inspire"]
    prompt: str = Field(..., min_length=1)
    direction: Literal["TD", "LR"] = "TD"


class AgentChatResult(BaseModel):
    mode: Literal["standard", "inspire"]
    mermaid_code: str
    optimized_text: Optional[str] = None
    attempts: int
    valid: bool
    message: Optional[str] = None
