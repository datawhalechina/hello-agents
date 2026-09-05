from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from ..config import get_settings, valid_config, print_config
from .routers import train
import asyncio

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于HelloAgents框架的健身助手Agent",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 注册路由
app.include_router(train.router)

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    # 打印config配置信息
    print_config()

    # 验证配置
    try:
        valid_config()
        print("\n ✔验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise

    print("\n" + "=" * 60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("\n" + "="*60)
    print("👋 应用正在关闭...")
    print("="*60 + "\n")

# @app.get("/")
# async def root():
#     """根路径"""
#     return {
#         "name": settings.app_name,
#         "version": settings.app_version,
#         "status": "running",
#         "docs": "/docs",
#         "redoc": "/redoc"
#     }

@app.get("/")
async def root():
    return RedirectResponse(url="/train/")


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

