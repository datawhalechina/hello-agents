"""FastAPI主应用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings
from .routes import chat, code, learning, assessment, auth, gamification, settings as settings_router

app = FastAPI(
    title="Way_to_Engineer API",
    description="AI辅助编程学习平台",
    version="0.1.0",
)

# CORS配置
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api")
app.include_router(code.router, prefix="/api")
app.include_router(learning.router)
app.include_router(assessment.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(gamification.router)
app.include_router(settings_router.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Way_to_Engineer API is running"}
