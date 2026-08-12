"""
智能股票分析助手 — 用户偏好API路由

提供偏好的读取、更新和投资画像查询接口。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from app.models.database import get_db_session
from app.services import preference_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/preferences", tags=["用户偏好"])


# =========================================================================
# 请求体模型
# =========================================================================

class PreferenceUpdateRequest(BaseModel):
    """偏好更新请求体——所有字段可选，支持部分更新"""

    risk_tolerance: Optional[str] = Field(None, description="风险承受度: conservative/moderate/aggressive", pattern="^(conservative|moderate|aggressive)$")
    investment_style: Optional[str] = Field(None, description="投资风格: value/growth/momentum/dividend/blend", pattern="^(value|growth|momentum|dividend|blend)$")
    investment_horizon: Optional[str] = Field(None, description="投资期限: short/medium/long", pattern="^(short|medium|long)$")
    target_return_rate: Optional[float] = Field(None, description="目标年化收益率(%)", ge=0, le=100)
    max_position_ratio: Optional[float] = Field(None, description="单票最大仓位(%)", ge=1, le=100)
    max_drawdown_limit: Optional[float] = Field(None, description="最大回撤预警线(%)", le=0)
    notification_enabled: Optional[bool] = Field(None, description="是否启用通知")
    notification_channels: Optional[List[str]] = Field(None, description="通知渠道")
    market_alert_threshold: Optional[float] = Field(None, description="异动提醒阈值(%)", ge=0, le=100)
    language: Optional[str] = Field(None, description="界面语言: zh/en", pattern="^(zh|en)$")
    theme: Optional[str] = Field(None, description="主题: light/dark/auto", pattern="^(light|dark|auto)$")
    default_view: Optional[str] = Field(None, description="默认首页: dashboard/watchlist", pattern="^(dashboard|watchlist)$")
    preferred_sectors: Optional[List[str]] = Field(None, description="偏好行业列表")
    excluded_sectors: Optional[List[str]] = Field(None, description="排除行业列表")


# =========================================================================
# API接口
# =========================================================================

@router.get("/")
async def get_preferences(
    user_id: str = "default",
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户偏好配置"""
    try:
        result = await preference_service.get_preference(db, user_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(code=500, message=f"获取偏好失败: {str(e)}")


@router.put("/")
async def update_preferences(
    request: PreferenceUpdateRequest,
    user_id: str = "default",
    db: AsyncSession = Depends(get_db_session),
):
    """更新用户偏好（支持部分更新，仅传入需要修改的字段）"""
    try:
        # 仅提交非None的字段
        update_data = request.model_dump(exclude_none=True)
        if not update_data:
            return error_response(code=400, message="未提供需要更新的字段")

        result = await preference_service.update_preference(db, user_id, update_data)
        return success_response(data=result, message="偏好更新成功")
    except Exception as e:
        return error_response(code=500, message=f"更新偏好失败: {str(e)}")


@router.get("/profile")
async def get_profile(
    user_id: str = "default",
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户投资画像摘要"""
    try:
        result = await preference_service.get_profile_summary(db, user_id)
        return success_response(data=result)
    except Exception as e:
        return error_response(code=500, message=f"获取画像失败: {str(e)}")
