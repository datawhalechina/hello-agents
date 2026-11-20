from __future__ import annotations

import asyncio
import datetime as dt

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import backend.app.models.analysis  # noqa: F401
import backend.app.models.article  # noqa: F401
import backend.app.models.search  # noqa: F401
from backend.app.models.database import Base
from backend.app.models.search import Search
from backend.services.job_recovery import recover_stale_jobs


def test_recover_stale_jobs_is_dry_run_by_default_and_apply_is_conditional():
    async def scenario() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        old = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(hours=2)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            db.add(
                Search(
                    job_id="stale-job",
                    query_text="recover me",
                    status="running",
                    progress_percent=50,
                    progress_stage="summarizing",
                    updated_at=old,
                    started_at=old,
                )
            )
            await db.commit()

        dry_run = await recover_stale_jobs(
            stale_after_seconds=1800,
            apply=False,
            session_factory=session_factory,
        )
        assert [item.job_id for item in dry_run] == ["stale-job"]
        async with session_factory() as db:
            unchanged = await db.get(Search, dry_run[0].search_id)
            assert unchanged is not None
            assert unchanged.status == "running"

        dispatched = []
        recovered = await recover_stale_jobs(
            stale_after_seconds=1800,
            apply=True,
            session_factory=session_factory,
            dispatch=lambda search_id, job_id: dispatched.append((search_id, job_id)),
        )
        assert len(recovered) == 1
        assert dispatched == [(recovered[0].search_id, "stale-job")]
        async with session_factory() as db:
            updated = await db.get(Search, recovered[0].search_id)
            assert updated is not None
            assert updated.status == "queued"
            assert updated.progress_percent == 0
            assert updated.started_at is None

            retryable = Search(
                job_id="broker-failure-job",
                query_text="retry dispatch",
                status="running",
                updated_at=old,
                started_at=old,
            )
            db.add(retryable)
            await db.commit()
            await db.refresh(retryable)
            retryable_id = retryable.id

        def fail_dispatch(search_id: int, job_id: str) -> None:
            raise ConnectionError("broker unavailable")

        try:
            await recover_stale_jobs(
                stale_after_seconds=1800,
                apply=True,
                session_factory=session_factory,
                dispatch=fail_dispatch,
            )
        except RuntimeError as exc:
            assert "remains recoverable" in str(exc)
        else:
            raise AssertionError("broker failure must be reported")

        immediately_retryable = await recover_stale_jobs(
            stale_after_seconds=1800,
            apply=False,
            session_factory=session_factory,
        )
        assert [item.search_id for item in immediately_retryable] == [retryable_id]
        await engine.dispose()

    asyncio.run(scenario())
