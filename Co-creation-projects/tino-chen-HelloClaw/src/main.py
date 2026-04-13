"""
HelloClaw Backend - FastAPI 入口
"""
import os

# 禁用 PYTHONSTARTUP 以避免 I/O 问题
os.environ.pop("PYTHONSTARTUP", None)

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, session, config, memory
from .workspace.manager import WorkspaceManager
from .agent.helloclaw_agent import HelloClawAgent

# 加载环境变量
load_dotenv()

# 全局 Agent 实例
_agent: HelloClawAgent = None


def get_agent() -> HelloClawAgent:
    """获取全局 Agent 实例"""
    global _agent
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _agent

    # 启动时初始化
    print("HelloClaw Backend starting...")

    # 初始化工作空间
    workspace_path = os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")
    workspace = WorkspaceManager(workspace_path)
    workspace.ensure_workspace_exists()
    print(f"Workspace initialized at: {workspace.workspace_path}")

    # 设置全局 workspace 实例
    config.set_workspace(workspace)
    memory.set_workspace(workspace)

    # 初始化全局 Agent 实例
    _agent = HelloClawAgent(workspace_path=workspace_path)
    print("HelloClawAgent initialized")

    yield
    # 关闭时清理
    print("HelloClaw Backend shutting down...")


app = FastAPI(
    title="HelloClaw API",
    description="AI Agent powered by HelloAgents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "helloclaw-backend"}


# 注册 API 路由
app.include_router(chat.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(memory.router, prefix="/api")


@app.get("/api")
async def api_root():
    return {"message": "HelloClaw API v0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
