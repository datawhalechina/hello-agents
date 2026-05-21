
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from ...settings import get_settings
import contextlib

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_daily_compute_lock: asyncio.Lock | None = None

def get_daily_compute_lock() -> asyncio.Lock:
    global _daily_compute_lock
    if _daily_compute_lock is None:
        _daily_compute_lock = asyncio.Lock()
    return _daily_compute_lock

_EXCLUDE_MEANINGFUL_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/papers/meta/summary",
    "/api/papers/reading/calendar",
)

def request_updates_meaningful_activity(method: str, path: str) -> bool:
    p = path or ""
    if p in ("/", "/health"):
        return False
    for pref in _EXCLUDE_MEANINGFUL_PREFIXES:
        if p.startswith(pref):
            return False
    return not (method.upper() == "GET" and p.startswith("/api/papers/daily"))

def touch_meaningful_activity_if_needed(app: FastAPI, method: str, path: str) -> None:
    if not request_updates_meaningful_activity(method, path):
        return
    with contextlib.suppress(Exception):
        app.state.last_meaningful_activity_monotonic = time.monotonic()

async def daily_auto_refresh_loop(app: FastAPI) -> None:
    s = get_settings()
    if not s.papergraph_daily_auto_refresh:
        logger.info("每日论文后台自动刷新已关闭（PAPERGRAPH_DAILY_AUTO_REFRESH=0）")
        return

    idle = max(15, s.papergraph_daily_auto_refresh_idle_sec)
    poll = max(30, s.papergraph_daily_auto_refresh_poll_sec)
    grace = max(10, s.papergraph_daily_auto_refresh_startup_grace_sec)
    logger.info("每日论文后台自动刷新已启用：idle=%ss poll=%ss startup_grace=%ss", idle, poll, grace)
    await asyncio.sleep(grace)

    from starlette.concurrency import run_in_threadpool
    from ...api.dependencies import get_db_path, get_searcher
    from ...models.schemas import DailyPapersRequest
    from ...services.daily.daily_cache_store import get_cache
    from ...services.daily.daily_service import compute_daily_papers as compute_daily
    import datetime as _dt
    from ...services.papers.papers_helpers import daily_paper_identity_sig

    def _cache_nonempty(cached) -> bool:
        if not cached:
            return False
        try:
            return bool(cached.get("arxiv_selected") or []) or bool(cached.get("personalized") or [])
        except Exception:
            return False

    lock = get_daily_compute_lock()
    date_key = _dt.datetime.now().strftime("%Y-%m-%d")

    while True:
        try:
            await asyncio.sleep(poll)
            ts = getattr(app.state, "last_meaningful_activity_monotonic", None)
            if ts is not None and time.monotonic() - ts < idle:
                continue
            db_path = get_db_path()
            if _cache_nonempty(await run_in_threadpool(get_cache, db_path, date_key=date_key, cache_key='default')):
                continue
            if lock.locked():
                continue

            async with lock:
                if _cache_nonempty(await run_in_threadpool(get_cache, db_path, date_key=date_key, cache_key='default')):
                    continue
                ts2 = getattr(app.state, "last_meaningful_activity_monotonic", None)
                if ts2 is not None and time.monotonic() - ts2 < idle:
                    continue
                settings = get_settings()
                from ...services.papers import papers_converters
                body = DailyPapersRequest(force_refresh=False)
                logger.info("每日论文：后台自动拉取开始（当日无有效缓存且系统空闲）")
                await compute_daily(
                    body=body, db_path=db_path, searcher=get_searcher(),
                    daily_paper_identity_sig_fn=daily_paper_identity_sig,
                    daily_arxiv_cs_categories=settings.get_daily_arxiv_cs_categories(),
                    papergraph_to_api_fn=papers_converters.litpaper_to_api_paper,
                    logger=logger,
                )
                logger.info("每日论文：后台自动拉取完成")
        except asyncio.CancelledError:
            logger.info("每日论文后台自动刷新任务已取消")
            raise
        except Exception:
            logger.exception("每日论文后台自动拉取失败（将按 poll 间隔重试）")

def spawn_daily_auto_refresh(app: FastAPI) -> asyncio.Task:
    return asyncio.create_task(daily_auto_refresh_loop(app), name="papergraph_daily_auto_refresh")
