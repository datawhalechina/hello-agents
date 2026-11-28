"""运动计划查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import PlanOut
from app.services import plan_service

router = APIRouter(prefix="/api", tags=["plan"])


@router.get("/plans/current", response_model=PlanOut | None)
def get_current_plan(db: Session = Depends(get_db)) -> PlanOut | None:
    plan = plan_service.get_current_plan(db)
    return PlanOut.model_validate(plan) if plan else None


@router.get("/plans/{plan_id}/versions", response_model=list[PlanOut])
def get_plan_versions(
    plan_id: str, db: Session = Depends(get_db)
) -> list[PlanOut]:
    plans = plan_service.list_versions(db, plan_id)
    return [PlanOut.model_validate(plan) for plan in plans]
