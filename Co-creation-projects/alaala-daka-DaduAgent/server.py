"""
Agent_Dev FastAPI 服务器入口
提供 REST API + WebSocket 端点，连接 React 前端与 Agent 后端
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from api.chat import router as chat_router
from api.sessions import router as sessions_router
from api.config import router as config_router
from api.files import router as files_router
from api.tools import router as tools_router
from api.models import router as models_router
from api.reflections import router as reflections_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理"""
    from tool.logger_handler import logger
    from tool.uploads_cleanup import start_uploads_cleanup, stop_uploads_cleanup
    logger.info("[server] Agent_Dev API 服务器启动")
    start_uploads_cleanup()
    try:
        yield
    finally:
        stop_uploads_cleanup()
        logger.info("[server] Agent_Dev API 服务器关闭")


app = FastAPI(
    title="Agent_Dev API",
    description="AI Agent 开发框架的 REST + WebSocket API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API 路由
app.include_router(chat_router)
app.include_router(sessions_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(reflections_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Agent_Dev API"}


# 生产模式：托管前端静态文件
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)
