# -*- coding: utf-8 -*-
"""Translation endpoints: translate PubMed text via the configured LLM."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.schemas.translate import TranslateIn, TranslateOut
from backend.services.agent_factory import build_summarizer
from backend.services.translation import LiteratureTranslator, TranslationError

router = APIRouter(prefix="/translate", tags=["translate"])
logger = logging.getLogger(__name__)

_translator: Optional[LiteratureTranslator] = None


def get_translator() -> LiteratureTranslator:
    """Lazily build (and reuse) the translator for the app lifetime."""
    global _translator
    if _translator is None:
        summarizer = build_summarizer(settings)
        _translator = LiteratureTranslator(
            api_base=summarizer.api_base,
            api_key=summarizer.api_key,
            model=summarizer.model,
            timeout=summarizer.timeout,
        )
        logger.info("Translator built (model=%s)", summarizer.model)
    return _translator


@router.post("", response_model=TranslateOut)
async def translate(payload: TranslateIn) -> TranslateOut:
    """Translate a block of text (title/abstract) into the target language."""
    try:
        translator = get_translator()
        translated = await asyncio.to_thread(
            translator.translate,
            payload.text,
            payload.target_language,
        )
        return TranslateOut(
            translated_text=translated,
            model_used=translator.model,
        )
    except TranslationError as exc:
        logger.error("Translation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected translation error")
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}")
