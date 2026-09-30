"""Celery application and tasks for long-running research work."""

from __future__ import annotations

import asyncio

from celery import Celery

from backend.app.core.config import settings

celery_app = Celery("pubmed_research_agent", broker=settings.redis_url)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_backend=None,
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
)


@celery_app.task(name="backend.worker.run_search_task", bind=True)
def run_search_task(self, search_id: int) -> None:
    """Run one database-backed research job in a worker process."""

    async def _run() -> None:
        from backend.app.models.database import engine
        from backend.services.search_jobs import execute_search_job

        try:
            redelivered = bool(self.request.delivery_info.get("redelivered"))
            await execute_search_job(search_id, allow_resume=redelivered)
        finally:
            await engine.dispose()

    asyncio.run(_run())
