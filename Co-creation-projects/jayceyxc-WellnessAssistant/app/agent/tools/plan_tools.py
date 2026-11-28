"""运动计划生成与动态调整工具。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.base import WellnessTool
from app.services import plan_service


class GeneratePlanParams(BaseModel):
    goal: str = Field(description="健康目标，例如减脂、康复、增肌或日常维持")
    days_per_week: int = Field(default=3, description="每周训练次数，1~7")
    session_minutes: int = Field(default=30, description="单次训练时长（分钟），10~180")
    intensity: str = Field(default="medium", description="强度：low、medium 或 high")
    restrictions: list[str] | None = Field(default=None, description="运动限制，例如膝盖不适")


class AdjustPlanParams(BaseModel):
    feedback: str = Field(description="用户身体反馈原文，例如训练后膝盖不适")
    direction: str = Field(
        default="decrease", description="调整方向：decrease、increase 或 maintain"
    )
    reason: str | None = Field(default=None, description="调整原因补充说明")


class PlanVersionsParams(BaseModel):
    plan_id: str = Field(description="计划组 ID")


def _generate(params: GeneratePlanParams, db: Session) -> dict:
    plan = plan_service.generate_plan(
        db,
        goal=params.goal,
        days_per_week=params.days_per_week,
        session_minutes=params.session_minutes,
        intensity=params.intensity,
        restrictions=params.restrictions,
    )
    return {"message": "运动计划已生成", "plan": plan_service.serialize_plan(plan)}


def _adjust(params: AdjustPlanParams, db: Session) -> dict:
    plan = plan_service.adjust_plan(
        db,
        feedback=params.feedback,
        direction=params.direction,
        reason=params.reason or "",
    )
    return {"message": "运动计划已调整并生成新版本", "plan": plan_service.serialize_plan(plan)}


def _versions(params: PlanVersionsParams, db: Session) -> dict:
    plans = plan_service.list_versions(db, params.plan_id)
    return {
        "plan_id": params.plan_id,
        "count": len(plans),
        "versions": [plan_service.serialize_plan(plan) for plan in plans],
    }


def build_plan_tools() -> list[WellnessTool]:
    return [
        WellnessTool(
            "generate_exercise_plan",
            "根据用户目标生成结构化运动计划并保存为新版本",
            GeneratePlanParams,
            _generate,
        ),
        WellnessTool(
            "adjust_exercise_plan",
            "根据身体反馈动态调整当前运动计划的强度与内容，生成新版本",
            AdjustPlanParams,
            _adjust,
        ),
        WellnessTool(
            "list_plan_versions",
            "查询同一份运动计划的所有历史版本与调整原因",
            PlanVersionsParams,
            _versions,
        ),
    ]
