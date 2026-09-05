# -*- coding: utf-8 -*-
"""Search request/response schemas."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class SearchCreate(BaseModel):
    query: str = Field(..., min_length=1, description="Research question")
    max_results: int = Field(default=20, ge=1, le=100)
    language: str = Field(default="en", pattern="^(en|zh)$")
    search_mode: str = Field(
        default="advanced",
        pattern="^(keyword|advanced)$",
        description="keyword: raw keyword search; advanced: LLM-rewritten PubMed query",
    )
    sort_by: str = Field(
        default="relevance",
        pattern="^(relevance|date_desc|date_asc)$",
        description="Result ordering",
    )
    min_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    max_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    min_impact_factor: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class ArticleOut(BaseModel):
    pmid: str
    title: str = ""
    abstract: str = ""
    doi: str = ""
    authors: list[dict] = Field(default_factory=list)
    journal: str = ""
    publish_date: str = ""
    publication_type: str = ""
    impact_factor: Optional[float] = Field(default=None, description="Journal impact factor from the local metrics table")


class AnalysisOut(BaseModel):
    """LLM 5-dimension summary stored for a search."""

    research_background: str = ""
    current_hotspots: list[dict] = Field(default_factory=list)
    main_findings: list[str] = Field(default_factory=list)
    experimental_methods: list[dict] = Field(default_factory=list)
    future_directions: list[dict] = Field(default_factory=list)
    model_used: str = ""


class SearchOut(BaseModel):
    id: int
    query_text: str
    pubmed_query: str = ""
    search_mode: str = "advanced"
    sort_by: str = "relevance"
    max_results: int = 20
    total_found: int = 0
    status: str
    error_message: str = ""
    created_at: dt.datetime
    articles: list[ArticleOut] = Field(default_factory=list)
    analysis: Optional[AnalysisOut] = None


class SearchListOut(BaseModel):
    id: int
    query_text: str
    status: str
    total_found: int
    created_at: dt.datetime


class JournalStat(BaseModel):
    name: str
    count: int


class YearStat(BaseModel):
    year: int
    count: int


class ImpactFactorBucket(BaseModel):
    bucket: str
    count: int


class KeywordStat(BaseModel):
    keyword: str
    count: int


class DashboardStatsOut(BaseModel):
    """Aggregated research-dashboard statistics."""

    total_searches: int = 0
    total_articles: int = 0
    journals: list[JournalStat] = Field(default_factory=list)
    years: list[YearStat] = Field(default_factory=list)
    impact_factor_buckets: list[ImpactFactorBucket] = Field(default_factory=list)
    top_keywords: list[KeywordStat] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)


class KeywordActionIn(BaseModel):
    keyword: str = Field(..., min_length=1)


class KeywordActionOut(BaseModel):
    excluded_keywords: list[str] = Field(default_factory=list)
