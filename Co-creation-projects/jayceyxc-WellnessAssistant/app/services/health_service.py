"""健康台账：指标校验、写入、查询与趋势聚合。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models.entities import HealthRecord

SUPPORTED_METRICS: dict[str, tuple[str, float, float]] = {
    "weight": ("kg", 20.0, 400.0),
    "sleep_hours": ("h", 0.0, 24.0),
    "heart_rate": ("bpm", 30.0, 250.0),
    "steps": ("步", 0.0, 200000.0),
    "body_fat": ("%", 1.0, 80.0),
    "water_ml": ("ml", 0.0, 20000.0),
}

DATE_FORMAT = "%Y-%m-%d"


def default_unit(metric_type: str) -> str:
    """返回指标默认单位，未知指标拒绝写入。"""
    if metric_type not in SUPPORTED_METRICS:
        supported = ", ".join(SUPPORTED_METRICS)
        raise ValueError(f"不支持的指标类型 '{metric_type}'，可用指标：{supported}")
    return SUPPORTED_METRICS[metric_type][0]


def parse_recorded_at(value: str | None) -> datetime:
    """解析 ISO 日期时间或 YYYY-MM-DD，留空时取当前时间。"""
    if not value:
        return utcnow()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, DATE_FORMAT)
        except ValueError as exc:
            raise ValueError("recorded_at 需为 ISO 日期时间或 YYYY-MM-DD 格式") from exc


def create_record(
    db: Session,
    metric_type: str,
    value: float,
    unit: str | None = None,
    recorded_at: str | None = None,
    note: str | None = None,
    source: str = "chat",
) -> HealthRecord:
    """写入一条健康记录，包含范围与单位校验。"""
    if metric_type not in SUPPORTED_METRICS:
        default_unit(metric_type)  # 抛出带可用指标列表的错误
    default, lower, upper = SUPPORTED_METRICS[metric_type]
    if value is None or not lower <= float(value) <= upper:
        raise ValueError(f"{metric_type} 数值 {value} 超出合理范围 {lower}~{upper}")

    record = HealthRecord(
        metric_type=metric_type,
        value=float(value),
        unit=(unit or default).strip(),
        recorded_at=parse_recorded_at(recorded_at),
        note=note,
        source=source,
    )
    db.add(record)
    db.flush()
    return record


def serialize_record(record: HealthRecord) -> dict:
    return {
        "id": record.id,
        "metric_type": record.metric_type,
        "value": record.value,
        "unit": record.unit,
        "recorded_at": record.recorded_at.isoformat(),
        "source": record.source,
        "note": record.note,
    }


def list_records(
    db: Session, metric_type: str | None = None, days: int = 30, limit: int = 200
) -> list[HealthRecord]:
    """按时间倒序查询健康记录。"""
    cutoff = utcnow() - timedelta(days=max(1, min(days, 3650)))
    stmt = select(HealthRecord).where(HealthRecord.recorded_at >= cutoff)
    if metric_type:
        stmt = stmt.where(HealthRecord.metric_type == metric_type)
    stmt = stmt.order_by(HealthRecord.recorded_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def build_trends(db: Session, metric_type: str, days: int = 30) -> dict:
    """按日期聚合成趋势点（同日多条取平均值）。"""
    cutoff = utcnow() - timedelta(days=max(1, min(days, 3650)))
    day = func.strftime(DATE_FORMAT, HealthRecord.recorded_at)
    stmt = (
        select(day, func.avg(HealthRecord.value), func.max(HealthRecord.unit))
        .where(HealthRecord.metric_type == metric_type)
        .where(HealthRecord.recorded_at >= cutoff)
        .group_by(day)
        .order_by(day)
    )
    rows = db.execute(stmt).all()
    return {
        "metric_type": metric_type,
        "unit": rows[0][2] if rows else default_unit(metric_type),
        "points": [
            {"date": str(date), "value": round(float(avg), 2), "unit": unit or ""}
            for date, avg, unit in rows
        ],
    }


def mark_source(db: Session, record_id: int, source: str) -> None:
    """更新记录来源（预留给设备同步等扩展）。"""
    db.execute(
        update(HealthRecord)
        .where(HealthRecord.id == record_id)
        .values(source=source)
    )
