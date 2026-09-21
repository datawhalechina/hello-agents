"""Analysis response schema."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisOut(BaseModel):
    id: int
    search_id: int
    summary: str = ""
    research_background: str = ""
    current_hotspots: list[dict] = Field(default_factory=list)
    main_findings: list[str] = Field(default_factory=list)
    experimental_methods: list[dict] = Field(default_factory=list)
    future_directions: list[dict] = Field(default_factory=list)
    model_used: str = ""
    token_usage: dict = Field(default_factory=dict)
    created_at: dt.datetime
