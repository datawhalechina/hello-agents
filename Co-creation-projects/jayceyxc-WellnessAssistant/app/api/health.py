"""服务健康检查、健康台账与趋势接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.schemas import HealthRecordOut, ServiceHealth, TrendOut
from app.services import health_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=ServiceHealth)
def service_health() -> ServiceHealth:
    return ServiceHealth(
        status="ok",
        app=settings.app_name,
        llm_model=settings.llm_model_id,
        llm_provider=settings.llm_provider,
        database=settings.database_url.split(":///")[0],
    )


@router.get("/health/records", response_model=list[HealthRecordOut])
def list_records(
    metric_type: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> list[HealthRecordOut]:
    records = health_service.list_records(db, metric_type, days)
    return [HealthRecordOut.model_validate(record) for record in records]


@router.get("/health/trends", response_model=TrendOut)
def get_trends(
    metric_type: str = Query(...),
    days: int = Query(default=30, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> TrendOut:
    return TrendOut(**health_service.build_trends(db, metric_type, days))
