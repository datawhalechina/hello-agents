"""
智能股票分析助手 — 用户偏好服务层

提供偏好的CRUD操作，以及向智能体层输出偏好上下文的方法。
"""

import json
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference import UserPreference


# =========================================================================
# 默认偏好（当用户未配置或无登录时使用）
# =========================================================================
DEFAULT_PREFERENCE = {
    "risk_tolerance": "moderate",
    "investment_style": "blend",
    "preferred_sectors": [],
    "excluded_sectors": [],
    "investment_horizon": "medium",
    "target_return_rate": 10.0,
    "max_position_ratio": 30.0,
    "max_drawdown_limit": -15.0,
    "notification_enabled": True,
    "notification_channels": ["push"],
    "market_alert_threshold": 5.0,
    "language": "zh",
    "theme": "auto",
    "default_view": "dashboard",
}


# =========================================================================
# CRUD 操作
# =========================================================================

async def get_preference(db: AsyncSession, user_id: str = "default") -> dict:
    """获取用户偏好，不存在时返回默认值"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        return {**DEFAULT_PREFERENCE, "user_id": user_id}
    return pref.to_dict()


async def get_or_create_preference(db: AsyncSession, user_id: str = "default") -> UserPreference:
    """获取或创建用户偏好记录，返回ORM对象"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = UserPreference.create_default(user_id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref


async def update_preference(db: AsyncSession, user_id: str, data: dict) -> dict:
    """更新用户偏好，支持部分更新"""
    pref = await get_or_create_preference(db, user_id)

    # 允许更新的字段白名单（防止注入未定义的字段）
    ALLOWED_FIELDS = {
        "risk_tolerance", "investment_style", "investment_horizon",
        "target_return_rate", "max_position_ratio", "max_drawdown_limit",
        "notification_enabled", "market_alert_threshold",
        "language", "theme", "default_view",
        # 以下是JSON字段
        "preferred_sectors", "excluded_sectors", "notification_channels",
    }

    for key, value in data.items():
        if key not in ALLOWED_FIELDS:
            continue

        # JSON数组字段序列化
        if key in ("preferred_sectors", "excluded_sectors", "notification_channels"):
            if value is not None:
                setattr(pref, key, json.dumps(value, ensure_ascii=False))
        # 布尔值字段
        elif key == "notification_enabled":
            setattr(pref, key, bool(value))
        # 数值字段
        elif key in ("target_return_rate", "max_position_ratio", "max_drawdown_limit", "market_alert_threshold"):
            setattr(pref, key, float(value))
        else:
            setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)
    return pref.to_dict()


# =========================================================================
# 智能体注入方法
# =========================================================================

async def get_preference_context(db: AsyncSession, user_id: str = "default") -> str:
    """生成偏好上下文文本，供智能体层注入分析流程

    返回格式化的中文描述，可直接作为Agent系统提示词的一部分。
    """
    pref = await get_preference(db, user_id)
    if pref is None:
        pref = DEFAULT_PREFERENCE

    risk_map = {
        "conservative": "保守型——侧重低估值、高股息、蓝筹股，回避高风险标的",
        "moderate": "稳健型——均衡配置，兼顾成长与价值",
        "aggressive": "激进型——侧重高成长、高波动标的，接受较大回撤",
    }
    style_map = {
        "value": "价值投资——偏好低PE、低PB、高股息率标的",
        "growth": "成长投资——偏好高营收增速、高利润增速标的",
        "momentum": "动量投资——偏好强势股、趋势跟踪",
        "dividend": "股息投资——偏好高分红率标的",
        "blend": "混合风格——综合运用多种投资策略",
    }
    horizon_map = {
        "short": "短期（<1年）",
        "medium": "中期（1-3年）",
        "long": "长期（>3年）",
    }

    preferred = json.loads(pref.get("preferred_sectors", "[]")) if isinstance(pref.get("preferred_sectors"), str) else pref.get("preferred_sectors", [])
    excluded = json.loads(pref.get("excluded_sectors", "[]")) if isinstance(pref.get("excluded_sectors"), str) else pref.get("excluded_sectors", [])

    context_parts = [
        "## 用户投资偏好（请据此调整分析和建议）",
        f"- 风险承受度: {risk_map.get(pref['risk_tolerance'], pref['risk_tolerance'])}",
        f"- 投资风格: {style_map.get(pref['investment_style'], pref['investment_style'])}",
        f"- 投资期限: {horizon_map.get(pref['investment_horizon'], pref['investment_horizon'])}",
        f"- 目标年化收益率: {pref['target_return_rate']}%",
        f"- 单票最大仓位: {pref['max_position_ratio']}%",
        f"- 最大回撤预警线: {pref['max_drawdown_limit']}%",
    ]

    if preferred:
        context_parts.append(f"- 偏好行业: {', '.join(preferred)}")
    if excluded:
        context_parts.append(f"- 排除行业: {', '.join(excluded)}")

    return "\n".join(context_parts)


async def get_profile_summary(db: AsyncSession, user_id: str = "default") -> dict:
    """获取用户投资画像摘要（用于前端偏好摘要展示）"""
    pref = await get_preference(db, user_id)
    if pref is None:
        pref = DEFAULT_PREFERENCE

    risk_labels = {"conservative": "保守型", "moderate": "稳健型", "aggressive": "激进型"}
    style_labels = {"value": "价值投资", "growth": "成长投资", "momentum": "动量投资", "dividend": "股息投资", "blend": "混合风格"}

    return {
        "user_id": pref["user_id"],
        "risk_label": risk_labels.get(pref["risk_tolerance"], pref["risk_tolerance"]),
        "style_label": style_labels.get(pref["investment_style"], pref["investment_style"]),
        "target_return": f"{pref['target_return_rate']}%",
        "max_drawdown": f"{pref['max_drawdown_limit']}%",
        "preferred_sectors_count": len(pref.get("preferred_sectors", []) if isinstance(pref.get("preferred_sectors"), list) else json.loads(pref.get("preferred_sectors", "[]"))),
        "is_configured": pref.get("id") is not None,
    }
