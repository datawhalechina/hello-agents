"""
Pydantic request/response models for the Guess Historical Figure Game API
"""

from typing import Optional
from pydantic import BaseModel


# Request models
class ChatRequest(BaseModel):
    message: str
    session_id: str


class GuessRequest(BaseModel):
    guess: str
    session_id: str


class StartRequest(BaseModel):
    pass


class HintRequest(BaseModel):
    session_id: str


class EndRequest(BaseModel):
    session_id: str


# Response model
class GameResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
