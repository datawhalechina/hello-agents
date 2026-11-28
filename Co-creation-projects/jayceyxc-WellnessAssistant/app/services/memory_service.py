"""长期记忆：事实写入、检索与健康上下文组装。"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models.entities import DEFAULT_USER_KEY, LongTermMemory, UserProfile
from app.services import health_service, plan_service


def add_fact(
    db: Session,
    fact: str,
    category: str = "general",
    source_record_id: int | None = None,
    confidence: float = 1.0,
) -> LongTermMemory:
    """写入一条长期事实，记录来源便于后续纠正。"""
    fact = fact.strip()
    if not fact:
        raise ValueError("fact 不能为空")
    memory = LongTermMemory(
        fact=fact,
        category=category,
        source_record_id=source_record_id,
        confidence=max(0.0, min(1.0, confidence)),
    )
    db.add(memory)
    db.flush()
    return memory


def list_active_facts(db: Session, limit: int = 20) -> list[LongTermMemory]:
    stmt = (
        select(LongTermMemory)
        .where(LongTermMemory.is_active.is_(True))
        .order_by(LongTermMemory.valid_from.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def deactivate_fact(db: Session, memory_id: int) -> bool:
    """用户纠正事实时停用旧记忆，不物理删除。"""
    memory = db.get(LongTermMemory, memory_id)
    if memory is None:
        return False
    db.execute(
        update(LongTermMemory)
        .where(LongTermMemory.id == memory_id)
        .values(is_active=False)
    )
    return True


def get_profile(db: Session) -> UserProfile:
    stmt = select(UserProfile).where(UserProfile.user_key == DEFAULT_USER_KEY)
    profile = db.scalars(stmt).first()
    if profile is None:
        profile = UserProfile(user_key=DEFAULT_USER_KEY)
        db.add(profile)
        db.flush()
    return profile


def save_profile(
    db: Session,
    basic_info: dict | None = None,
    health_goal: str | None = None,
    constraints: list[str] | None = None,
) -> UserProfile:
    profile = get_profile(db)
    if basic_info:
        merged = dict(profile.basic_info or {})
        merged.update({key: value for key, value in basic_info.items() if value is not None})
        profile.basic_info = merged
    if health_goal is not None:
        profile.health_goal = health_goal
    if constraints is not None:
        profile.constraints = constraints
    profile.updated_at = utcnow()
    db.flush()
    return profile


def build_context(db: Session, days: int = 30) -> dict:
    """组装 Agent 决策所需的全部结构化上下文。"""
    profile = get_profile(db)
    records = health_service.list_records(db, days=days, limit=50)
    plan = plan_service.get_current_plan(db)
    return {
        "profile": {
            "basic_info": profile.basic_info or {},
            "health_goal": profile.health_goal,
            "constraints": profile.constraints or [],
        },
        "recent_records": [health_service.serialize_record(item) for item in records[:20]],
        "record_count": len(records),
        "memories": [item.fact for item in list_active_facts(db)],
        "current_plan": plan_service.serialize_plan(plan) if plan else None,
    }
