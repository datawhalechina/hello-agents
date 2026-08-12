# -*- coding: utf-8 -*-
"""Search endpoints: run the ResearchAgent pipeline and persist results.

- POST /search  runs the full pipeline (rewrite -> hybrid search -> rerank
  -> compress -> LLM summary) and persists articles + analysis.
- GET  /search/history  lists recent searches (must be declared before
  /{search_id} so "history" is not captured as an int id).
- GET  /search/{id}  returns a stored search with its articles + analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models.analysis import Analysis
from backend.app.models.article import Article
from backend.app.models.database import get_db
from backend.app.models.search import Search
from backend.app.schemas.search import (
    AnalysisOut,
    ArticleOut,
    DashboardStatsOut,
    KeywordActionIn,
    KeywordActionOut,
    SearchCreate,
    SearchListOut,
    SearchOut,
)
from backend.services.agent_factory import build_agent
from backend.services.search_stats import (
    build_dashboard_stats,
    load_excluded_keywords,
    save_excluded_keywords,
)
from backend.services.journal_metrics import JournalMetrics

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SearchOut, status_code=201)
async def create_search(
    payload: SearchCreate,
    db: AsyncSession = Depends(get_db),
) -> SearchOut:
    """Run the full ResearchAgent pipeline and persist the results."""
    search = Search(
        query_text=payload.query,
        max_results=payload.max_results,
        status="running",
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)

    try:
        agent = await asyncio.to_thread(build_agent, settings)
        report = await asyncio.to_thread(
            agent.research,
            payload.query,
            payload.max_results,
            payload.language,
            payload.search_mode,
            payload.sort_by,
            payload.min_year,
            payload.max_year,
            payload.min_impact_factor,
        )
        await _persist_report(db, search, report)
    except Exception as exc:
        logger.exception("Search pipeline failed for query=%r", payload.query)
        search.status = "failed"
        search.error_message = str(exc)[:2000]
        await db.commit()
        await db.refresh(search)

    out = await _load_search_out(db, search.id)
    # Echo request options (not persisted) so the client can render them.
    out.search_mode = payload.search_mode
    out.sort_by = payload.sort_by
    return out


@router.get("/history", response_model=list[SearchListOut])
async def list_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[SearchListOut]:
    """Return the most recent searches, newest first."""
    result = await db.execute(
        select(Search)
        .order_by(Search.created_at.desc(), Search.id.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        SearchListOut(
            id=row.id,
            query_text=row.query_text,
            status=row.status,
            total_found=row.total_found,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/stats", response_model=DashboardStatsOut)
async def search_stats(
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsOut:
    """Return aggregated statistics for the research dashboard."""
    search_rows = (await db.execute(select(Search))).scalars().all()
    article_rows = (await db.execute(select(Article))).scalars().all()
    excluded = load_excluded_keywords()
    data = build_dashboard_stats(
        articles=[(a.journal, a.publish_date) for a in article_rows],
        queries=[s.query_text for s in search_rows],
        rewritten_queries=[s.pubmed_query for s in search_rows],
        metrics=_get_journal_metrics(),
        excluded_keywords=excluded,
    )
    return DashboardStatsOut(**data)


@router.post("/keywords/exclude", response_model=KeywordActionOut)
async def exclude_keyword(payload: KeywordActionIn) -> KeywordActionOut:
    """Hide a trending keyword from the dashboard."""
    excluded = load_excluded_keywords()
    keyword = payload.keyword.strip()
    if keyword:
        excluded.add(keyword)
        save_excluded_keywords(excluded)
    return KeywordActionOut(excluded_keywords=sorted(excluded))


@router.post("/keywords/restore", response_model=KeywordActionOut)
async def restore_keyword(payload: KeywordActionIn) -> KeywordActionOut:
    """Bring a previously hidden keyword back."""
    excluded = load_excluded_keywords()
    keyword = payload.keyword.strip()
    if keyword:
        excluded.discard(keyword)
        save_excluded_keywords(excluded)
    return KeywordActionOut(excluded_keywords=sorted(excluded))


@router.post("/keywords/restore-all", response_model=KeywordActionOut)
async def restore_all_keywords() -> KeywordActionOut:
    """Restore every hidden keyword."""
    save_excluded_keywords(set())
    return KeywordActionOut(excluded_keywords=[])


@router.get("/{search_id}", response_model=SearchOut)
async def get_search(
    search_id: int,
    db: AsyncSession = Depends(get_db),
) -> SearchOut:
    """Return a stored search with its articles and analysis."""
    return await _load_search_out(db, search_id)


async def _load_search_out(db: AsyncSession, search_id: int) -> SearchOut:
    """Fetch a search with relations eagerly loaded and map it to SearchOut."""
    result = await db.execute(
        select(Search)
        .where(Search.id == search_id)
        .options(selectinload(Search.articles), selectinload(Search.analysis))
    )
    search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return _search_to_out(search)


async def _persist_report(db: AsyncSession, search: Search, report) -> None:
    """Store the report: search metadata, articles, and the LLM analysis."""
    search.status = report.status
    search.pubmed_query = report.rewritten_query
    search.total_found = report.total_pubmed_hits
    search.error_message = "; ".join(report.errors)[:2000]

    for art in report.articles:
        db.add(
            Article(
                search_id=search.id,
                pmid=str(art.get("pmid", "")),
                title=art.get("title", "") or "",
                abstract=art.get("abstract", "") or "",
                doi=art.get("doi", "") or "",
                authors=json.dumps(art.get("authors", []), ensure_ascii=False),
                journal=art.get("journal", "") or "",
                publish_date=art.get("publish_date", "") or "",
                publication_type=art.get("publication_type", "") or "",
            )
        )

    if report.research_background or report.main_findings:
        db.add(
            Analysis(
                search_id=search.id,
                research_background=report.research_background or "",
                current_hotspots=json.dumps(
                    report.current_hotspots, ensure_ascii=False
                ),
                main_findings=json.dumps(report.main_findings, ensure_ascii=False),
                experimental_methods=json.dumps(
                    report.experimental_methods, ensure_ascii=False
                ),
                future_directions=json.dumps(
                    report.future_directions, ensure_ascii=False
                ),
                model_used=report.model_used or "",
            )
        )

    await db.commit()
    await db.refresh(search)


def _search_to_out(search: Search) -> SearchOut:
    """Map a Search ORM row (with relations loaded) to SearchOut."""
    articles = []
    metrics = _get_journal_metrics()
    for art in search.articles:
        try:
            authors = json.loads(art.authors or "[]")
        except json.JSONDecodeError:
            authors = []
        articles.append(
            ArticleOut(
                pmid=art.pmid,
                title=art.title or "",
                abstract=art.abstract or "",
                doi=art.doi or "",
                authors=authors,
                journal=art.journal or "",
                publish_date=art.publish_date or "",
                publication_type=art.publication_type or "",
                impact_factor=metrics.impact_factor(art.journal or ""),
            )
        )

    analysis = None
    if search.analysis is not None:
        analysis = AnalysisOut(
            research_background=search.analysis.research_background or "",
            current_hotspots=_json_list(search.analysis.current_hotspots),
            main_findings=_json_list(search.analysis.main_findings),
            experimental_methods=_json_list(search.analysis.experimental_methods),
            future_directions=_json_list(search.analysis.future_directions),
            model_used=search.analysis.model_used or "",
        )

    return SearchOut(
        id=search.id,
        query_text=search.query_text,
        pubmed_query=search.pubmed_query or "",
        max_results=search.max_results,
        total_found=search.total_found,
        status=search.status,
        error_message=search.error_message or "",
        created_at=search.created_at,
        articles=articles,
        analysis=analysis,
    )


_metrics: Optional[JournalMetrics] = None


def _get_journal_metrics() -> JournalMetrics:
    """Lazily build the shared journal impact-factor lookup table."""
    global _metrics
    if _metrics is None:
        _metrics = JournalMetrics()
    return _metrics


def _json_list(value: str) -> list:
    """Parse a JSON-array column, tolerating empty or invalid values."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []
