"""FastAPI 主应用（CORS / health / Swagger / startup）"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings, print_config, validate_config
from ..utils.logger import get_logger, setup_logging
from .exception_handlers import register_exception_handlers
from .routes import movies, recommend

settings = get_settings()
logger = get_logger("app.api")

OPENAPI_TAGS = [
    {"name": "System", "description": "健康检查与服务信息"},
    {"name": "Movies", "description": "确定性 TMDB 搜片 / 发现（不经 LLM）"},
    {"name": "Recommend", "description": "多智能体智能推荐（HelloAgents + TMDB Tool）"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("%s v%s 启动中", settings.app_name, settings.app_version)
    print_config()
    validate_config()
    # 0.0.0.0 仅表示监听所有网卡，浏览器请用 localhost / 127.0.0.1
    docs_host = "127.0.0.1" if settings.host in ("0.0.0.0", "::") else settings.host
    logger.info("Swagger: http://%s:%s/docs", docs_host, settings.port)
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "HelloAgents + TMDB 的 LLM 电影推荐 Demo API。\n\n"
        "- **Movies**：确定性片库通道（search / discover）\n"
        "- **Recommend**：多智能体推荐（画像 → 检索 → 推荐）\n\n"
        "密钥仅通过环境变量配置，详见 `.env.example`。"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
        "persistAuthorization": True,
    },
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")


@app.get("/", tags=["System"], summary="服务根信息")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@app.get("/health", tags=["System"], summary="健康检查")
async def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "tmdb_configured": settings.has_tmdb_credentials(),
    }
