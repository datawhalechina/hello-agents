# -*- coding: utf-8 -*-
"""FastAPI application entrypoint.

Run (from repo root):
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

Or (from backend/):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import json
import re
import sys
import time
import uuid
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.routing import Match

# Make the repo root importable (tools/, services/, agents/) even when the
# app is started from the backend/ directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.v1.router import router
from backend.app.core.config import settings
from backend.app.models.database import engine
from backend.services.metrics import request_metrics

class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


log_handler = logging.StreamHandler()
if settings.log_format.strip().lower() == "json":
    log_handler.setFormatter(JsonLogFormatter())
else:
    log_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    handlers=[log_handler],
    force=True,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage process-wide resources; schema changes are handled by Alembic."""
    logger.info("Application started; database migrations are managed by Alembic")
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _matched_route_path(request: Request) -> str:
    """Resolve the declared route template without recording user-controlled IDs."""
    for route in request.app.router.routes:
        effective_contexts = getattr(route, "effective_route_contexts", None)
        if callable(effective_contexts):
            for context in effective_contexts():
                methods = getattr(context, "methods", set())
                path_regex = getattr(context, "path_regex", None)
                if (
                    path_regex is not None
                    and path_regex.match(request.url.path)
                    and request.method in methods
                ):
                    return getattr(context, "path_format", "__unmatched__")
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", "__unmatched__")
    return "__unmatched__"


@app.middleware("http")
async def request_observability(request: Request, call_next):
    """Attach request IDs, timing, security headers, and one access log."""
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
    route_path = _matched_route_path(request)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
    finally:
        elapsed_seconds = time.perf_counter() - started
        elapsed_ms = elapsed_seconds * 1000
        request_metrics.observe(
            method=request.method,
            route=route_path,
            status_code=status_code,
            duration_seconds=elapsed_seconds,
        )
        logger.info(
            "http_request request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            status_code,
            elapsed_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "docs": "/docs" if settings.enable_api_docs else "disabled",
    }
