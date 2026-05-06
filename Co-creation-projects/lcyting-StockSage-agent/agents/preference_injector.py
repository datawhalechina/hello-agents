"""
智能股票分析助手 — 智能体偏好注入模块

在Agent执行前读取用户偏好，将偏好参数注入分析上下文，
实现个性化投资分析体验。

使用方式:
    from agents.preference_injector import inject_preferences
    
    context = await inject_preferences(user_id)
    # 将 context 注入到 Agent 的 system_prompt 中
"""

import sys
from pathlib import Path

# 确保能导入后端模块
_BACKEND_PATH = Path(__file__).parent.parent / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))

from app.models.database import async_session_factory
from app.services.preference_service import get_preference_context, get_preference


async def inject_preferences(user_id: str = "default") -> str:
    """读取用户偏好并生成可注入Agent的上下文文本

    Args:
        user_id: 用户标识，默认"default"

    Returns:
        格式化的中文偏好描述文本，可直接追加到Agent的system_prompt中
    """
    async with async_session_factory() as db:
        context = await get_preference_context(db, user_id)
        return context


async def get_risk_profile(user_id: str = "default") -> dict:
    """获取用户风险画像，供选股Agent和投资顾问Agent使用

    Returns:
        {
            "risk_tolerance": "conservative",
            "investment_style": "value",
            "preferred_sectors": [...],
            "max_position_ratio": 30.0,
            ...
        }
    """
    async with async_session_factory() as db:
        pref = await get_preference(db, user_id)
        return pref
