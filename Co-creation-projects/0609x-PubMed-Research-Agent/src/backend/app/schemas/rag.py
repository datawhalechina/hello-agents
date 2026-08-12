"""RAG query request/response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RagQueryIn(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    language: str = Field(default="en", pattern="^(en|zh)$")


class RagSource(BaseModel):
    pmid: str
    title: str
    relevance_score: float = 0.0


class RagQueryOut(BaseModel):
    answer: str
    sources: list[RagSource] = Field(default_factory=list)
