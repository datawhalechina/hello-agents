# -*- coding: utf-8 -*-
"""Translation request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateIn(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(
        default="zh", pattern="^(zh|en)$", description="Target language code"
    )


class TranslateOut(BaseModel):
    translated_text: str = ""
    model_used: str = ""
