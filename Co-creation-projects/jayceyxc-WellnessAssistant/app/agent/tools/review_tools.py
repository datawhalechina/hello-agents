"""健康复盘工具。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.base import WellnessTool
from app.services import review_service


class ReviewParams(BaseModel):
    days: int = Field(default=7, description="复盘区间天数，默认 7 天")


def _review(params: ReviewParams, db: Session) -> dict:
    return review_service.build_review(db, params.days)


def build_review_tools() -> list[WellnessTool]:
    return [
        WellnessTool(
            "generate_health_review",
            "结合历史健康记录生成周期性复盘与非诊断性健康提示",
            ReviewParams,
            _review,
        )
    ]
