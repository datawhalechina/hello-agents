"""
游戏化API路由 - XP、等级、徽章
"""
from fastapi import APIRouter, Query
from ...services.gamification_service import get_gamification_service

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


@router.get("/profile")
async def get_gamification_profile(user_id: str = Query("default")):
    """获取用户游戏化档案"""
    service = get_gamification_service()
    profile = service.get_profile(user_id)
    return profile


@router.get("/badges")
async def get_badge_definitions():
    """获取所有徽章定义"""
    from ...services.gamification_service import BADGE_DEFINITIONS
    return {"badges": list(BADGE_DEFINITIONS.values())}
