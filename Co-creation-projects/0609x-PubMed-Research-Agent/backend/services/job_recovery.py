"""Recovery helpers for search jobs that stopped making progress."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import or_, select, update

from backend.app.models.database import AsyncSessionLocal
from backend.app.models.search import Search


@dataclass(frozen=True)
class RecoveryCandidate:
    search_id: int
    job_id: str
    previous_status: str
    updated_at: dt.datetime


async def recover_stale_jobs(
    *,
    stale_after_seconds: int,
    apply: bool,
    dispatch: Callable[[int, str], None] | None = None,
    session_factory=AsyncSessionLocal,
) -> list[RecoveryCandidate]:
    """Find stale queued/running jobs and optionally put them back on Celery."""
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    stale_before = now - dt.timedelta(seconds=stale_after_seconds)
    async with session_factory() as db:
        rows = (
            await db.execute(
                select(Search)
                .where(
                    Search.job_id.is_not(None),
                    Search.cancel_requested.is_(False),
                    Search.updated_at < stale_before,
                    or_(Search.status == "queued", Search.status == "running"),
                )
                .order_by(Search.updated_at.asc())
            )
        ).scalars()
        candidates = [
            RecoveryCandidate(
                search_id=row.id,
                job_id=str(row.job_id),
                previous_status=row.status,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        if not apply or not candidates:
            return candidates

    if dispatch is None:
        from backend.worker import run_search_task

        dispatch = lambda search_id, job_id: run_search_task.apply_async(
            args=[search_id], task_id=job_id
        )

    claimed: list[RecoveryCandidate] = []
    for candidate in candidates:
        async with session_factory() as db:
            changed = await db.execute(
                update(Search)
                .where(
                    Search.id == candidate.search_id,
                    Search.status == candidate.previous_status,
                    Search.updated_at == candidate.updated_at,
                    Search.cancel_requested.is_(False),
                )
                .values(
                    status="queued",
                    progress_stage="queued",
                    progress_percent=0,
                    progress_message="陈旧任务已由恢复工具重新排队",
                    error_message="",
                    started_at=None,
                    completed_at=None,
                    # Keep the old timestamp until broker delivery succeeds. If
                    # dispatch fails or this process stops, the next run can
                    # retry immediately instead of waiting for another window.
                    updated_at=candidate.updated_at,
                )
            )
            await db.commit()
            if changed.rowcount == 1:
                claimed.append(candidate)
            else:
                continue

        try:
            dispatch(candidate.search_id, candidate.job_id)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to requeue search job {candidate.job_id}; it remains recoverable"
            ) from exc

        async with session_factory() as db:
            await db.execute(
                update(Search)
                .where(
                    Search.id == candidate.search_id,
                    Search.status == "queued",
                    Search.updated_at == candidate.updated_at,
                )
                .values(updated_at=now)
            )
            await db.commit()
    return claimed
