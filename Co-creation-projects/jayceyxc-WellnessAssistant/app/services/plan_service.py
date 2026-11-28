"""运动计划：规则化生成、版本化动态调整与查询。"""

from __future__ import annotations

import copy
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import ExercisePlan

INTENSITY_LEVELS = ("low", "medium", "high")
DISCOMFORT_KEYWORDS = ("疼", "痛", "不适", "头晕", "恶心", "受伤", "胸闷", "心慌")


def _goal_template(goal: str) -> tuple[str, list[dict]]:
    text = (goal or "").lower()
    if any(word in text for word in ("康复", "恢复", "拉伸", "rehab")):
        return "rehab", [
            {"type": "关节活动度练习", "minutes": 10, "intensity": "low"},
            {"type": "低强度步行", "minutes": 15, "intensity": "low"},
            {"type": "拉伸与放松", "minutes": 10, "intensity": "low"},
        ]
    if any(word in text for word in ("减脂", "减重", "瘦身", "fat", "weight")):
        return "fat_loss", [
            {"type": "快走或慢跑", "minutes": 25, "intensity": "medium"},
            {"type": "自重力量训练", "minutes": 15, "intensity": "medium"},
            {"type": "拉伸放松", "minutes": 5, "intensity": "low"},
        ]
    if any(word in text for word in ("增肌", "力量", "strength")):
        return "strength", [
            {"type": "力量训练", "minutes": 30, "intensity": "medium"},
            {"type": "核心训练", "minutes": 10, "intensity": "medium"},
            {"type": "拉伸放松", "minutes": 5, "intensity": "low"},
        ]
    return "general", [
        {"type": "有氧运动", "minutes": 20, "intensity": "medium"},
        {"type": "全身力量训练", "minutes": 15, "intensity": "medium"},
        {"type": "拉伸放松", "minutes": 5, "intensity": "low"},
    ]


def build_plan_content(
    goal: str,
    days_per_week: int = 3,
    session_minutes: int = 30,
    intensity: str = "medium",
    restrictions: list[str] | None = None,
) -> dict:
    """构造结构化计划内容，不依赖 LLM 输出格式。"""
    if intensity not in INTENSITY_LEVELS:
        raise ValueError(f"intensity 只能是 {', '.join(INTENSITY_LEVELS)}")
    if not 1 <= days_per_week <= 7:
        raise ValueError("days_per_week 需在 1~7 之间")
    if not 10 <= session_minutes <= 180:
        raise ValueError("session_minutes 需在 10~180 之间")

    goal_type, template = _goal_template(goal)
    sessions = copy.deepcopy(template)
    ratio = session_minutes / sum(item["minutes"] for item in sessions)
    for item in sessions:
        item["minutes"] = max(5, round(item["minutes"] * ratio))
        item["intensity"] = intensity if item["intensity"] != "low" else "low"

    restrictions = restrictions or []
    return {
        "goal_type": goal_type,
        "exercise_type": sessions[0]["type"],
        "frequency": f"每周 {days_per_week} 次",
        "session_minutes": session_minutes,
        "intensity": intensity,
        "sessions": sessions,
        "progression": "连续两周无不适后，可将单次时长增加 5~10 分钟；出现不适则降低强度。",
        "precautions": [
            "训练前热身 5 分钟，训练后逐步放松。",
            "出现疼痛、头晕或明显不适时立即停止并咨询专业人士。",
            *[f"注意限制：{item}" for item in restrictions],
        ],
        "restrictions": restrictions,
    }


def serialize_plan(plan: ExercisePlan) -> dict:
    return {
        "id": plan.id,
        "plan_id": plan.plan_id,
        "version": plan.version,
        "status": plan.status,
        "goal": plan.goal,
        "content": plan.content,
        "reason": plan.reason,
        "created_at": plan.created_at.isoformat(),
    }


def get_current_plan(db: Session) -> ExercisePlan | None:
    stmt = (
        select(ExercisePlan)
        .where(ExercisePlan.status == "active")
        .order_by(ExercisePlan.created_at.desc(), ExercisePlan.id.desc())
    )
    return db.scalars(stmt).first()


def list_versions(db: Session, plan_id: str) -> list[ExercisePlan]:
    stmt = (
        select(ExercisePlan)
        .where(ExercisePlan.plan_id == plan_id)
        .order_by(ExercisePlan.version)
    )
    return list(db.scalars(stmt))


def _supersede(db: Session, plan: ExercisePlan) -> None:
    db.execute(
        update(ExercisePlan)
        .where(ExercisePlan.id == plan.id)
        .values(status="superseded")
    )


def generate_plan(
    db: Session,
    goal: str,
    days_per_week: int = 3,
    session_minutes: int = 30,
    intensity: str = "medium",
    restrictions: list[str] | None = None,
) -> ExercisePlan:
    """生成初始计划；旧 active 计划转为 superseded。"""
    if not goal.strip():
        raise ValueError("goal 不能为空")
    content = build_plan_content(goal, days_per_week, session_minutes, intensity, restrictions)
    previous = get_current_plan(db)
    if previous:
        _supersede(db, previous)

    plan = ExercisePlan(
        plan_id=uuid.uuid4().hex,
        version=1,
        status="active",
        goal=goal,
        content=content,
        reason="根据用户基础信息与健康目标生成初始运动计划",
    )
    db.add(plan)
    db.flush()
    return plan


def adjust_plan(
    db: Session,
    feedback: str,
    direction: str = "decrease",
    reason: str = "",
) -> ExercisePlan:
    """依据身体反馈生成新版本；不适反馈强制降强度。"""
    current = get_current_plan(db)
    if current is None:
        raise ValueError("当前没有可调整的运动计划，请先生成计划")

    if direction not in {"decrease", "increase", "maintain"}:
        raise ValueError("direction 只能是 decrease、increase 或 maintain")
    if any(keyword in feedback for keyword in DISCOMFORT_KEYWORDS):
        direction = "decrease"

    content = copy.deepcopy(current.content or {})
    levels = list(INTENSITY_LEVELS)
    index = levels.index(content.get("intensity", "medium"))
    if direction == "decrease":
        index = max(0, index - 1)
    elif direction == "increase":
        index = min(len(levels) - 1, index + 1)
    content["intensity"] = levels[index]

    factor = {"decrease": 0.8, "increase": 1.1, "maintain": 1.0}[direction]
    content["session_minutes"] = max(
        10, min(180, round(content.get("session_minutes", 30) * factor))
    )
    for session in content.get("sessions", []):
        session["minutes"] = max(5, round(session["minutes"] * factor))
        if session["intensity"] != "low":
            session["intensity"] = levels[index]
    if direction == "decrease":
        content["progression"] = "暂停进阶，待身体状态稳定且无不适后再逐步恢复强度。"
        content["precautions"] = [
            "如不适持续或加重，请停止训练并咨询专业医师。",
            *content.get("precautions", []),
        ]

    _supersede(db, current)
    plan = ExercisePlan(
        plan_id=current.plan_id,
        version=current.version + 1,
        status="active",
        goal=current.goal,
        content=content,
        reason=reason.strip() or f"用户反馈：{feedback}；调整方向：{direction}",
    )
    db.add(plan)
    db.flush()
    return plan
