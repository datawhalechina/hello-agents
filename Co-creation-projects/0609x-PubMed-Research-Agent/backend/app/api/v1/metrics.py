"""Prometheus-compatible operational metrics."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.database import get_db
from backend.app.models.search import Search
from backend.services.metrics import request_metrics

router = APIRouter(tags=["operations"])


@router.get("/metrics", include_in_schema=False)
async def metrics(db: AsyncSession = Depends(get_db)) -> Response:
    """Expose bounded-cardinality API and durable job metrics."""
    rows = await db.execute(select(Search.status, func.count()).group_by(Search.status))
    job_counts = {str(status): int(count) for status, count in rows.all()}

    oldest_queued = await db.scalar(
        select(func.min(Search.created_at)).where(Search.status == "queued")
    )
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    oldest_queued_age = (
        (now - oldest_queued).total_seconds() if oldest_queued is not None else 0.0
    )
    stale_before = now - dt.timedelta(seconds=settings.search_job_stale_after_seconds)
    stale_running = await db.scalar(
        select(func.count())
        .select_from(Search)
        .where(Search.status == "running", Search.updated_at < stale_before)
    )

    body = request_metrics.render(
        job_counts=job_counts,
        oldest_queued_age_seconds=oldest_queued_age,
        stale_running_jobs=int(stale_running or 0),
    )
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
