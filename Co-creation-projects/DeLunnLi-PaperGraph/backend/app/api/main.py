import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..settings import configure_logging, get_settings, print_config, validate_config
from ..services.graph.kg_relations import get_kg_metrics
from .routes import paper_routes, paper_reader_routes, search_routes

settings = get_settings()
logger = logging.getLogger(__name__)

class _MeaningfulActivityMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            from ..services.daily.daily_auto_refresh import touch_meaningful_activity_if_needed

            touch_meaningful_activity_if_needed(request.app, request.method, request.url.path)
        except Exception:
            pass
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("%s", "=" * 60)
    logger.info("📚 %s v%s", settings.app_name, settings.app_version)
    logger.info("%s", "=" * 60)

    app.state.last_meaningful_activity_monotonic = None
    daily_refresh_task: asyncio.Task | None = None

    print_config()

    try:
        validate_config()
        logger.info("✅ 配置验证通过")
    except ValueError as e:
        logger.error("❌ 配置验证失败: %s", e)
        raise

    try:
        from ..services.daily.daily_auto_refresh import spawn_daily_auto_refresh

        daily_refresh_task = spawn_daily_auto_refresh(app)
    except Exception as exc:
        logger.warning("每日论文后台自动刷新任务未启动: %s", exc)

    logger.info("%s", "=" * 60)

    yield

    logger.info("%s", "=" * 60)
    logger.info("👋 应用正在关闭...")
    if daily_refresh_task is not None:
        daily_refresh_task.cancel()
        try:
            await daily_refresh_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("每日论文后台任务结束异常", exc_info=True)
    logger.info("%s", "=" * 60)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.description,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(_MeaningfulActivityMiddleware)

app.include_router(paper_routes.router, prefix="/api")
app.include_router(paper_reader_routes.router, prefix="/api")
app.include_router(search_routes.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_enabled": False,
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "kg_metrics": get_kg_metrics(),
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception(
        "未处理异常: %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": str(exc)},
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
