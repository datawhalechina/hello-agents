"""智能推荐 API：多智能体流水线（画像 → 检索 → 推荐）。

同步 Agent/LLM 通过 asyncio.to_thread 执行，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from ...agents.movie_recommender_agent import get_movie_recommender
from ...exceptions import AppError
from ...models.schemas import RecommendRequest, RecommendResponse
from ...utils.logger import get_logger

router = APIRouter(prefix="/recommend", tags=["Recommend"])
logger = get_logger("app.recommend")


@router.post(
    "",
    response_model=RecommendResponse,
    summary="智能电影推荐",
    description=(
        "串行多智能体：画像（无工具）→ 检索（TMDB Tool）→ 推荐（候选内决策）。"
        "耗时可能较长（视 LLM），建议客户端超时 ≥ 120s。"
    ),
)
async def recommend_movies(request: RecommendRequest) -> RecommendResponse:
    logger.info(
        "recommend 请求 mood=%s party=%s genres=%s",
        request.mood,
        request.party_type,
        request.genres,
    )
    agent = get_movie_recommender()
    # recommend() 内含多次同步 LLM/HTTP，放到线程池
    result, message = await asyncio.to_thread(agent.recommend, request)
    return RecommendResponse(success=True, message=message, data=result)


@router.get(
    "/health",
    summary="推荐服务健康检查",
    description="返回各 Agent 名称与工具数量；初始化失败时 503。",
)
async def recommend_health():
    try:
        agent = get_movie_recommender()
        snap = agent.health_snapshot()
        return {
            "status": "healthy",
            "service": "recommend",
            **snap,
        }
    except Exception as e:
        logger.exception("recommend health 失败")
        raise AppError(
            f"推荐服务不可用: {e}",
            code="RECOMMEND_UNAVAILABLE",
            status_code=503,
        ) from e
