"""
FastAPI 应用入口 - 英语句子扩写智能体
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os

# 添加当前目录（backend）到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers.expand import router as expand_router

# 创建 FastAPI 应用
app = FastAPI(
    title="英语句子扩写智能体 API",
    description="基于多智能体协作的英语写作教练应用",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 包含路由
app.include_router(expand_router)


# 统一异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "英语句子扩写智能体 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
