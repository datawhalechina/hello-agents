#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动FastAPI服务器
"""

import uvicorn
from src.api.routes import router
from fastapi import FastAPI
from config.settings import settings

# 创建FastAPI应用
app = FastAPI(
    title="故事生成器智能体",
    description="一个基于AI的故事生成器智能体，支持小说、诗歌、剧本等多种文本生成",
    version="1.0.0",
    debug=settings.debug
)

# 添加路由
app.include_router(router)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用故事生成器智能体",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "model": settings.model_name,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens
    }

if __name__ == "__main__":
    print(f"启动服务器...")
    print(f"地址: http://{settings.host}:{settings.port}")
    print(f"文档: http://{settings.host}:{settings.port}/docs")
    print(f"调试模式: {settings.debug}")

    uvicorn.run(
        "start_server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )