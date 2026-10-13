"""RAG query request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RagDocumentIn(BaseModel):
    """One browser-saved article available to the local RAG retriever."""

    pmid: str = Field(..., min_length=1, max_length=32)
    title: str = Field(default="", max_length=1000)
    abstract: str = Field(default="", max_length=5000)
    journal: str = Field(default="", max_length=500)
    publish_date: str = Field(default="", max_length=100)


class RagQueryIn(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    language: str = Field(default="en", pattern="^(en|zh)$")
    documents: list[RagDocumentIn] = Field(default_factory=list, max_length=100)


class RagSource(BaseModel):
    pmid: str
    title: str
    relevance_score: float = 0.0


class RagQueryOut(BaseModel):
    answer: str
    sources: list[RagSource] = Field(default_factory=list)
