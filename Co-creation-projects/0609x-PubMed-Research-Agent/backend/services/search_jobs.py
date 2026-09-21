"""Durable execution service for background research jobs."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from typing import Any

import redis.asyncio as redis
from sqlalchemy import select, update

from backend.app.core.config import settings
from backend.app.models.analysis import Analysis
from backend.app.models.article import Article
from backend.app.models.database import AsyncSessionLocal
from backend.app.models.search import Search
from backend.services.agent_factory import build_agent

logger = logging.getLogger(__name__)
TERMINAL_STATUSES = {"completed", "partial", "failed", "cancelled"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def progress_channel(job_id: str) -> str:
    return f"search-job:{job_id}:progress"


def create_progress_redis(*, stream: bool = False):
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=None if stream else settings.redis_socket_timeout,
    )


def job_event_payload(search: Search) -> dict[str, Any]:
    def iso(value: dt.datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    return {
        "job_id": search.job_id,
        "search_id": search.id,
        "status": search.status,
        "progress_percent": search.progress_percent,
        "progress_stage": search.progress_stage,
        "progress_message": search.progress_message,
        "error_message": search.error_message or "",
        "cancel_requested": search.cancel_requested,
        "created_at": iso(search.created_at),
        "updated_at": iso(search.updated_at),
        "started_at": iso(search.started_at),
        "completed_at": iso(search.completed_at),
    }


async def publish_job_event(search: Search, redis_client=None) -> None:
    """Publish a best-effort progress event; SQL remains authoritative."""
    if not search.job_id:
        return
    owns_client = redis_client is None
    client = redis_client or create_progress_redis()
    try:
        await client.publish(
            progress_channel(search.job_id),
            json.dumps(job_event_payload(search), ensure_ascii=False),
        )
    except Exception:
        logger.warning("Unable to publish progress for job %s", search.job_id, exc_info=True)
    finally:
        if owns_client:
            await client.aclose()


async def record_job_progress(
    search_id: int,
    stage: str,
    percent: int,
    message: str,
    redis_client=None,
) -> None:
    """Persist a progress snapshot and publish the same snapshot to Redis."""
    async with AsyncSessionLocal() as db:
        changed = await db.execute(
            update(Search)
            .where(
                Search.id == search_id,
                Search.status == "running",
                Search.cancel_requested.is_(False),
            )
            .values(
                progress_stage=stage[:40],
                progress_percent=max(0, min(100, percent)),
                progress_message=message[:255],
                updated_at=_now(),
            )
        )
        await db.commit()
        if changed.rowcount != 1:
            return
        search = await db.get(Search, search_id)
        if search is not None:
            await publish_job_event(search, redis_client)


async def execute_search_job(search_id: int, *, allow_resume: bool = False) -> None:
    """Claim and execute one queued search, persisting all state in SQL."""
    async with AsyncSessionLocal() as db:
        claimable_statuses = ["queued", "running"] if allow_resume else ["queued"]
        claimed = await db.execute(
            update(Search)
            .where(
                Search.id == search_id,
                Search.status.in_(claimable_statuses),
                Search.cancel_requested.is_(False),
            )
            .values(
                status="running",
                progress_stage="starting",
                progress_percent=5,
                progress_message="Worker 已接收任务，正在初始化检索组件",
                started_at=_now(),
                updated_at=_now(),
            )
        )
        await db.commit()
        if claimed.rowcount != 1:
            logger.info("Search job %s was already claimed or cancelled", search_id)
            return

        search = await db.get(Search, search_id)
        if search is None:
            return
        logger.info("Search job started job_id=%s search_id=%s", search.job_id, search.id)
        request_args = (
            search.query_text,
            search.max_results,
            search.language,
            search.search_mode,
            search.sort_by,
            search.min_year,
            search.max_year,
            search.min_impact_factor,
        )

    redis_client = create_progress_redis()
    try:
        await record_job_progress(
            search_id,
            "starting",
            5,
            "Worker 已接收任务，正在初始化检索组件",
            redis_client,
        )
        agent = await asyncio.to_thread(build_agent, settings)
        loop = asyncio.get_running_loop()

        def on_progress(stage: str, percent: int, message: str) -> None:
            future = asyncio.run_coroutine_threadsafe(
                record_job_progress(
                    search_id, stage, percent, message, redis_client
                ),
                loop,
            )
            try:
                future.result(timeout=10)
            except Exception:
                logger.warning(
                    "Unable to persist progress for search %s at %s",
                    search_id,
                    stage,
                    exc_info=True,
                )

        report = await asyncio.to_thread(
            agent.research, *request_args, progress_callback=on_progress
        )

        async with AsyncSessionLocal() as db:
            search = (
                await db.execute(
                    select(Search).where(Search.id == search_id).with_for_update()
                )
            ).scalar_one_or_none()
            if search is None:
                return
            if search.cancel_requested or search.status == "cancelled":
                search.status = "cancelled"
                search.completed_at = search.completed_at or _now()
                search.updated_at = _now()
                await db.commit()
                await publish_job_event(search, redis_client)
                return
            await persist_report(db, search, report)
            await publish_job_event(search, redis_client)
            logger.info(
                "Search job finished job_id=%s search_id=%s status=%s",
                search.job_id,
                search.id,
                search.status,
            )
    except Exception as exc:
        logger.exception("Search job %s failed", search_id)
        async with AsyncSessionLocal() as db:
            search = await db.get(Search, search_id)
            if search is None:
                return
            if search.cancel_requested or search.status == "cancelled":
                search.status = "cancelled"
                search.progress_stage = "cancelled"
                search.progress_percent = 100
                search.progress_message = "任务已取消"
            else:
                search.status = "failed"
                search.progress_stage = "failed"
                search.progress_percent = 100
                search.progress_message = "任务执行失败"
                search.error_message = str(exc)[:2000]
            search.completed_at = _now()
            search.updated_at = _now()
            await db.commit()
            await publish_job_event(search, redis_client)
    finally:
        await redis_client.aclose()


async def persist_report(db, search: Search, report) -> None:
    """Persist a completed research report and its related records."""
    search.status = report.status
    search.progress_stage = report.status
    search.progress_percent = 100
    search.progress_message = (
        "分析完成，部分数据可能缺失" if report.status == "partial" else "分析完成"
    )
    search.pubmed_query = report.rewritten_query
    search.total_found = report.total_pubmed_hits
    search.error_message = "; ".join(report.errors)[:2000]
    search.completed_at = _now()
    search.updated_at = _now()

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
                current_hotspots=json.dumps(report.current_hotspots, ensure_ascii=False),
                main_findings=json.dumps(report.main_findings, ensure_ascii=False),
                experimental_methods=json.dumps(
                    report.experimental_methods, ensure_ascii=False
                ),
                future_directions=json.dumps(report.future_directions, ensure_ascii=False),
                model_used=report.model_used or "",
            )
        )

    await db.commit()
