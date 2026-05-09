"""
分析历史记录服务 — 管理各类分析报告的历史存储与查询
"""

from datetime import date
from typing import Optional

from sqlalchemy import select, func, delete
from app.models.database import async_session_factory
from app.models.history_models import AnalysisHistory


async def save_analysis(
    analysis_type: str,
    content: str,
    user_id: str = "default",
    stock_code: Optional[str] = None,
    stock_name: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """保存分析报告到历史记录"""
    try:
        today = date.today().isoformat()
        async with async_session_factory() as db:
            record = AnalysisHistory(
                user_id=user_id,
                date=today,
                type=analysis_type,
                stock_code=stock_code,
                stock_name=stock_name,
                title=title or f"{analysis_type}_{today}",
                content=content,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return {"success": True, "id": record.id}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_history_list(
    analysis_type: Optional[str] = None,
    user_id: str = "default",
    limit: int = 20,
) -> dict:
    """获取历史记录列表"""
    try:
        async with async_session_factory() as db:
            conditions = [AnalysisHistory.user_id == user_id]
            if analysis_type:
                conditions.append(AnalysisHistory.type == analysis_type)

            stmt = select(AnalysisHistory).where(*conditions).order_by(
                AnalysisHistory.created_at.desc()
            ).limit(limit)
            result = await db.execute(stmt)
            records = result.scalars().all()

            count_stmt = select(func.count()).select_from(AnalysisHistory).where(*conditions)
            total = (await db.execute(count_stmt)).scalar()

            return {
                "success": True,
                "items": [r.to_dict() for r in records],
                "total": total or 0,
            }
    except Exception as e:
        return {"success": False, "items": [], "total": 0, "error": str(e)}


async def get_history_detail(record_id: int) -> dict:
    """获取单条历史记录详情"""
    try:
        async with async_session_factory() as db:
            record = await db.get(AnalysisHistory, record_id)
            if not record:
                return {"success": False, "error": "记录不存在"}
            return {"success": True, "record": record.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_history(record_id: int) -> dict:
    """删除单条历史记录"""
    try:
        async with async_session_factory() as db:
            record = await db.get(AnalysisHistory, record_id)
            if not record:
                return {"success": False, "error": "记录不存在"}
            await db.delete(record)
            await db.commit()
            return {"success": True, "message": "已删除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def clear_today_history(analysis_type: Optional[str] = None) -> dict:
    """清空今日历史记录"""
    try:
        today = date.today().isoformat()
        async with async_session_factory() as db:
            conditions = [AnalysisHistory.date == today]
            if analysis_type:
                conditions.append(AnalysisHistory.type == analysis_type)
            stmt = delete(AnalysisHistory).where(*conditions)
            result = await db.execute(stmt)
            await db.commit()
            return {"success": True, "count": result.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}
