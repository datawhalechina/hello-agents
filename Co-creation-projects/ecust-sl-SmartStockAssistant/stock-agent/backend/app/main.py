# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.analysis import router as analysis_router
from api.schemas import HealthResponse
from app.config import settings
from data.sources.stock_list import ensure_stock_list
from data.sources.hot_stocks import prewarm as prewarm_hot_stocks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时异步加载股票列表 + 预热热门股票缓存（都不阻塞启动）
    import asyncio
    asyncio.create_task(ensure_stock_list())
    asyncio.create_task(prewarm_hot_stocks())
    yield


app = FastAPI(
    title="Stock Analysis Agent",
    description="基于 LangGraph + Qwen 的股票多维度分析 Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        mock_mode=settings.use_mock_data,
    )