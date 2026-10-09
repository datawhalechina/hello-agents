# -*- coding: utf-8 -*-
"""Search endpoints: enqueue research jobs and return persisted results.

- POST /search/jobs enqueues the full pipeline and returns immediately.
- GET/POST /search/jobs/{job_id} exposes status and cancellation.
- GET  /search/history  lists recent searches (must be declared before
  /{search_id} so "history" is not captured as an int id).
- GET  /search/{id}  returns a stored search with its articles + analysis.
"""

from __future__ import annotations

import json
import logging
import uuid
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.article import Article
from backend.app.models.database import AsyncSessionLocal, get_db
from backend.app.models.search import Search
from backend.app.schemas.search import (
    AnalysisOut,
    ArticleOut,
    DashboardStatsOut,
    KeywordActionIn,
    KeywordActionOut,
    SearchCreate,
    SearchJobOut,
    SearchListOut,
    SearchOut,
)
from backend.services.search_stats import (
    build_dashboard_stats,
    load_excluded_keywords,
    save_excluded_keywords,
)
from backend.services.journal_metrics import JournalMetrics
from backend.services.search_jobs import (
    TERMINAL_STATUSES,
    create_progress_redis,
    job_event_payload,
    progress_channel,
    publish_job_event,
)
from backend.worker import celery_app, run_search_task

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.post(
    "/jobs",
    response_model=SearchJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_search_job(
    payload: SearchCreate,
    db: AsyncSession = Depends(get_db),
) -> SearchJobOut:
    """Persist and enqueue a research job without holding the HTTP request."""
    return await _enqueue_search(payload, db)


@router.post(
    "",
    response_model=SearchJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
)
async def create_search(
    payload: SearchCreate,
    db: AsyncSession = Depends(get_db),
) -> SearchJobOut:
    """Compatibility alias for the asynchronous /search/jobs endpoint."""
    return await _enqueue_search(payload, db)


async def _enqueue_search(payload: SearchCreate, db: AsyncSession) -> SearchJobOut:
    job_id = str(uuid.uuid4())
    search = Search(
        job_id=job_id,
        query_text=payload.query,
        max_results=payload.max_results,
        language=payload.language,
        search_mode=payload.search_mode,
        sort_by=payload.sort_by,
        min_year=payload.min_year,
        max_year=payload.max_year,
        min_impact_factor=payload.min_impact_factor,
        status="queued",
        progress_stage="queued",
        progress_percent=0,
        progress_message="任务已提交，正在等待 Worker 处理",
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)

    try:
        run_search_task.apply_async(args=[search.id], task_id=job_id)
        logger.info("Search job queued job_id=%s search_id=%s", job_id, search.id)
    except Exception as exc:
        logger.exception("Unable to enqueue search job %s", job_id)
        search.status = "failed"
        search.progress_stage = "failed"
        search.progress_percent = 100
        search.progress_message = "后台任务服务不可用"
        search.error_message = f"Unable to enqueue job: {exc}"[:2000]
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background job service is unavailable",
        ) from exc

    return _job_to_out(search)


@router.get("/jobs/{job_id}", response_model=SearchJobOut)
async def get_search_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> SearchJobOut:
    search = await _get_search_by_job_id(db, job_id)
    return _job_to_out(search)


@router.get("/jobs/{job_id}/events")
async def stream_search_job_events(job_id: str) -> StreamingResponse:
    """Stream durable job snapshots over Server-Sent Events."""
    async with AsyncSessionLocal() as db:
        await _get_search_by_job_id(db, job_id)
    return StreamingResponse(
        _job_event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _job_event_stream(job_id: str):
    async def load_snapshot() -> Search | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Search).where(Search.job_id == job_id))
            return result.scalar_one_or_none()

    def encode(search: Search) -> str:
        return f"data: {json.dumps(job_event_payload(search), ensure_ascii=False)}\n\n"

    search = await load_snapshot()
    if search is None:
        return
    yield encode(search)
    if search.status in TERMINAL_STATUSES:
        return

    client = create_progress_redis(stream=True)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(progress_channel(job_id))
        # Close the subscribe race by re-reading SQL after the subscription.
        search = await load_snapshot()
        if search is None:
            return
        yield encode(search)
        if search.status in TERMINAL_STATUSES:
            return

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=15.0,
            )
            if message and message.get("type") == "message":
                payload = str(message["data"])
                yield f"data: {payload}\n\n"
                try:
                    if json.loads(payload).get("status") in TERMINAL_STATUSES:
                        return
                except (TypeError, ValueError):
                    logger.warning("Invalid progress event for job %s", job_id)
            else:
                # Heartbeats keep proxies alive; SQL snapshots also recover a
                # Redis publication missed during a transient broker outage.
                search = await load_snapshot()
                if search is None:
                    return
                yield encode(search)
                if search.status in TERMINAL_STATUSES:
                    return
                yield ": keep-alive\n\n"
    except Exception:
        logger.warning("SSE stream unavailable for job %s", job_id, exc_info=True)
        return
    finally:
        try:
            await pubsub.unsubscribe(progress_channel(job_id))
        finally:
            await pubsub.aclose()
            await client.aclose()


@router.post("/jobs/{job_id}/cancel", response_model=SearchJobOut)
async def cancel_search_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> SearchJobOut:
    """Request cooperative cancellation and revoke queued delivery."""
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    cancelled = await db.execute(
        update(Search)
        .where(
            Search.job_id == job_id,
            Search.status.not_in({"completed", "partial", "failed", "cancelled"}),
        )
        .values(
            cancel_requested=True,
            status="cancelled",
            progress_stage="cancelled",
            progress_percent=100,
            progress_message="任务已取消",
            completed_at=now,
            updated_at=now,
        )
    )
    await db.commit()
    search = await _get_search_by_job_id(db, job_id)
    await publish_job_event(search)
    if cancelled.rowcount == 1:
        try:
            celery_app.control.revoke(job_id, terminate=False)
        except Exception:
            logger.warning("Could not broadcast revoke for job %s", job_id, exc_info=True)
    return _job_to_out(search)


async def _get_search_by_job_id(db: AsyncSession, job_id: str) -> Search:
    result = await db.execute(select(Search).where(Search.job_id == job_id))
    search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Search job not found")
    return search


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
        job_id=search.job_id,
        query_text=search.query_text,
        pubmed_query=search.pubmed_query or "",
        language=search.language or "en",
        search_mode=search.search_mode or "advanced",
        sort_by=search.sort_by or "relevance",
        min_year=search.min_year,
        max_year=search.max_year,
        min_impact_factor=search.min_impact_factor,
        max_results=search.max_results,
        total_found=search.total_found,
        status=search.status,
        error_message=search.error_message or "",
        created_at=search.created_at,
        articles=articles,
        analysis=analysis,
    )


def _job_to_out(search: Search) -> SearchJobOut:
    if search.job_id is None:
        raise ValueError("Legacy search rows do not have background job IDs")
    return SearchJobOut(
        job_id=search.job_id,
        search_id=search.id,
        status=search.status,
        progress_percent=search.progress_percent,
        progress_stage=search.progress_stage,
        progress_message=search.progress_message or "",
        error_message=search.error_message or "",
        cancel_requested=search.cancel_requested,
        created_at=search.created_at,
        updated_at=search.updated_at,
        started_at=search.started_at,
        completed_at=search.completed_at,
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
