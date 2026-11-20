"""Preview or requeue search jobs that have stopped making progress."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.models.database import engine
from backend.services.job_recovery import recover_stale_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stale-after-seconds",
        type=int,
        default=settings.search_job_stale_after_seconds,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually reset and requeue candidates; the default is a dry run.",
    )
    args = parser.parse_args()
    minimum = settings.celery_task_time_limit + 60
    if args.stale_after_seconds < minimum:
        parser.error(
            "--stale-after-seconds must be at least 60 seconds longer than "
            f"CELERY_TASK_TIME_LIMIT ({minimum})"
        )
    return args


async def run() -> int:
    args = parse_args()
    try:
        candidates = await recover_stale_jobs(
            stale_after_seconds=args.stale_after_seconds,
            apply=args.apply,
        )
    finally:
        await engine.dispose()

    mode = "REQUEUED" if args.apply else "DRY-RUN"
    print(f"{mode}: {len(candidates)} stale job(s)")
    for candidate in candidates:
        print(
            f"search_id={candidate.search_id} job_id={candidate.job_id} "
            f"status={candidate.previous_status} updated_at={candidate.updated_at.isoformat()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
