# -*- coding: utf-8 -*-
"""RAG chat endpoints grounded in the user's browser-saved literature."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.schemas.rag import RagQueryIn, RagQueryOut
from backend.services.agent_factory import build_summarizer
from backend.services.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])
logger = logging.getLogger(__name__)

_service: Optional[RagService] = None


def get_rag_service() -> RagService:
    """Lazily build (and reuse) the RAG service for the app lifetime."""
    global _service
    if _service is None:
        summarizer = build_summarizer(settings)
        _service = RagService(llm=summarizer)
        logger.info("Favorite-library RAG service built")
    return _service


@router.post("/query", response_model=RagQueryOut)
async def rag_query(payload: RagQueryIn) -> RagQueryOut:
    """Answer a question using only the articles supplied from favorites."""
    try:
        service = get_rag_service()
        return await asyncio.to_thread(
            service.answer,
            payload.query,
            payload.documents,
            payload.top_k,
            payload.language,
        )
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {exc}")
