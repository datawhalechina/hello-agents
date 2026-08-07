"""
智能股票分析助手 — FastAPI 应用入口

启动方法（从项目根目录执行）：
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

exe 打包后直接运行：
    stock_analyzer.exe
    浏览器访问 http://127.0.0.1:5174/dashboard（端口以 exe 旁 .env 中 BACKEND_PORT 为准）
"""

import sys
import io
from pathlib import Path

# Windows 控制台编码修复：强制使用 UTF-8 输出，避免 emoji/中文打印报错
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

# 将项目关键目录加入sys.path，确保各类导入正常工作
# main.py 位于 backend/app/main.py，需要向上3级到项目根目录
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"             # 使 from app.xxx 导入生效
_AGENTS_DIR = _PROJECT_ROOT / "agents"               # 使 from agents.xxx 导入生效
_HELLO_DIR = _PROJECT_ROOT / "HelloAgents Optimized"  # 使 from hello_agents 导入生效

for p in [_BACKEND_DIR, _PROJECT_ROOT, _AGENTS_DIR, _HELLO_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.response import success_response, error_response
from app.models.database import init_db, close_db
from app.models.report import AnalysisReport  # noqa: F401 — 确保数据库初始化时创建表
from app.models.history_models import AnalysisHistory  # noqa: F401 — 确保历史记录表创建


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"[后端] 智能股票分析助手启动中...")
    warnings = settings.validate()
    if warnings:
        print("[后端] ⚠️ 配置警告:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[后端] ✅ 配置验证通过")
    print(f"[后端] 服务地址: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")

    # 初始化数据库（创建表）
    await init_db()
    print("[后端] ✅ 数据库初始化完成")

    # 后台预热仪表盘所需妙想缓存（不阻塞本 worker 接受请求）
    async def _warm_dashboard_cache_bg() -> None:
        try:
            from app.services.dashboard_warmup import warm_dashboard_cache

            await asyncio.to_thread(warm_dashboard_cache)
            print("[后端] ✅ 仪表盘数据预热已完成（进程内妙想缓存已填充）")
        except Exception as exc:
            print(f"[后端] ⚠️ 仪表盘预热未完成（可忽略）: {exc}")

    asyncio.create_task(_warm_dashboard_cache_bg())

    yield
    # 关闭时执行
    await close_db()
    print("[后端] 服务关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title="智能股票分析助手",
    description="基于多智能体架构的A股投资分析工具API",
    version="0.1.0",
    lifespan=lifespan,
)

# 是否托管 Vue 构建产物（exe 一体化或设置 FRONTEND_DIR 且存在 dist）
_FRONTEND_DIR = settings.FRONTEND_DIR
_SERVE_FRONTEND = _FRONTEND_DIR.exists() and (_FRONTEND_DIR / "index.html").exists()
# SPA 入口禁用强缓存：避免升级 exe 后浏览器仍用旧 index 引用已过期的 hash chunk
_SPA_INDEX_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}

# =========================================================================
# CORS 跨域中间件（允许前端Vue3开发服务器访问）
# =========================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        "http://127.0.0.1:5173",
        f"http://127.0.0.1:{settings.BACKEND_PORT}",
        "*",  # 开发阶段允许所有来源
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# 系统路由
# =========================================================================
@app.get("/api/v1/system/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return success_response(
        data={
            "status": "ok",
            "version": "0.1.0",
            "agent_ready": settings.is_agent_ready(),
            "skills_ready": settings.is_skills_ready(),
        }
    )


@app.get("/api/v1/system/config", tags=["系统"])
async def system_config():
    """获取系统配置（公开信息，不包含密钥）"""
    return success_response(
        data={
            "llm_model": settings.LLM_MODEL_ID,
            "agent_ready": settings.is_agent_ready(),
            "skills_ready": settings.is_skills_ready(),
            "frontend_port": settings.FRONTEND_PORT,
        }
    )


@app.get("/", tags=["系统"])
async def root():
    """根路径：托管前端时返回 index.html（与 vite dev 一致）；否则返回 API 说明"""
    if _SERVE_FRONTEND:
        return FileResponse(str(_FRONTEND_DIR / "index.html"), headers=dict(_SPA_INDEX_HEADERS))
    return {"message": "智能股票分析助手 API", "docs": "/docs"}


# =========================================================================
# 注册子路由
# =========================================================================
from app.api.preferences import router as preferences_router
from app.api.market import router as market_router
from app.api.financial import router as financial_router
from app.api.news import router as news_router
from app.api.screener import router as screener_router
from app.api.analysis import router as analysis_router
from app.api.watchlist import router as watchlist_router
from app.api.buffett import router as buffett_router
from app.api.simulation import router as simulation_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router
from app.api.agent_api import router as agent_router
from app.api.sentiment import router as sentiment_router
from app.api.data_analysis import router as data_analysis_router
from app.api.cache_api import router as cache_router
from app.api.system_browser import router as system_browser_router

app.include_router(preferences_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(financial_router, prefix="/api/v1")
app.include_router(news_router, prefix="/api/v1")
app.include_router(screener_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(watchlist_router, prefix="/api/v1")
app.include_router(buffett_router, prefix="/api/v1")
app.include_router(simulation_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(sentiment_router, prefix="/api/v1")
app.include_router(data_analysis_router, prefix="/api/v1")
app.include_router(cache_router, prefix="/api/v1")
app.include_router(system_browser_router, prefix="/api/v1")

# =========================================================================
# 前端静态文件服务（exe 模式或 FRONTEND_DIR 指定时启用）
# =========================================================================
if _SERVE_FRONTEND:
    # 挂载 assets 等静态资源（文件名带 content hash，可由浏览器长期缓存）
    _assets_dir = _FRONTEND_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend_assets")

    # SPA 回退：非 /api 路径返回 index.html（含禁止缓存响应头，见 _SPA_INDEX_HEADERS）
    @app.get("/{full_path:path}", tags=["前端"])
    async def serve_spa(full_path: str = ""):
        fp = _FRONTEND_DIR / full_path
        if full_path and fp.exists() and fp.is_file():
            return FileResponse(str(fp))
        return FileResponse(str(_FRONTEND_DIR / "index.html"), headers=dict(_SPA_INDEX_HEADERS))


# =========================================================================
# exe 独立入口
# =========================================================================
def start_server(host: str = None, port: int = None):
    """启动 uvicorn 服务器（供 exe 入口调用）"""
    import uvicorn
    uvicorn.run(
        app,
        host=host or settings.BACKEND_HOST,
        port=port or settings.BACKEND_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.BACKEND_DEBUG,
    )
