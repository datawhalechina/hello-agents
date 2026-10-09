"""Health check endpoint."""

from __future__ import annotations

import redis.asyncio as redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.models.database import AsyncSessionLocal
from backend.app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Compatibility liveness endpoint."""
    return _liveness()


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report whether the API process can serve requests."""
    return _liveness()


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(response: Response) -> ReadinessResponse:
    """Check dependencies required to accept search jobs."""
    database_ok = await _check_database()
    redis_ok = await _check_redis()
    ready = database_ok and redis_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        app_name=settings.app_name,
        app_version=settings.app_version,
        components={
            "database": "ok" if database_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    )


def _liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
    )


async def _check_database() -> bool:
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    client = redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()
