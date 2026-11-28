"""健康复盘：基于历史数据生成非诊断性总结与提示。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import health_service, plan_service


def build_review(db: Session, days: int = 7) -> dict:
    """按指标汇总区间变化，并给出保守的健康提示。"""
    records = health_service.list_records(db, days=days, limit=1000)
    by_metric: dict[str, list] = {}
    for record in records:
        by_metric.setdefault(record.metric_type, []).append(record)

    summary: list[dict] = []
    hints: list[str] = []
    for metric_type, items in by_metric.items():
        ordered = sorted(items, key=lambda item: item.recorded_at)
        first, last = ordered[0].value, ordered[-1].value
        summary.append(
            {
                "metric_type": metric_type,
                "unit": ordered[-1].unit,
                "count": len(items),
                "first": round(first, 2),
                "latest": round(last, 2),
                "average": round(sum(item.value for item in items) / len(items), 2),
                "change": round(last - first, 2),
            }
        )

        if metric_type == "sleep_hours" and sum(item.value for item in items) / len(items) < 7:
            hints.append("近期平均睡眠时长偏短，建议优先保证规律作息，再评估训练强度。")
        if metric_type == "weight" and abs(last - first) > 3:
            hints.append("近期体重变化较明显，建议结合饮食与身体状态复核，不建议单纯加大训练量。")
        if metric_type == "heart_rate" and any(item.value > 100 for item in items):
            hints.append("记录中存在偏高的静息心率，建议减少高强度训练并咨询专业人士。")

    if not records:
        hints.append("该时间范围内暂无健康记录，建议先持续记录体重、睡眠等指标。")

    plan = plan_service.get_current_plan(db)
    return {
        "period_days": days,
        "record_count": len(records),
        "metrics": summary,
        "hints": hints,
        "current_plan": plan_service.serialize_plan(plan) if plan else None,
        "disclaimer": settings.disclaimer,
    }
