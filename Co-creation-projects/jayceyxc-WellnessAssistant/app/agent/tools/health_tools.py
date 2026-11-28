"""健康台账与用户上下文工具。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.base import WellnessTool
from app.services import health_service, memory_service


class RecordMetricParams(BaseModel):
    metric_type: str = Field(
        description="指标类型：weight(体重)、sleep_hours(睡眠小时)、heart_rate(心率)、steps(步数)、body_fat(体脂率)、water_ml(饮水量)"
    )
    value: float = Field(description="指标数值")
    unit: str | None = Field(default=None, description="单位，留空时使用指标默认单位")
    recorded_at: str | None = Field(
        default=None, description="记录日期，YYYY-MM-DD 或 ISO 日期时间；留空表示今天"
    )
    note: str | None = Field(default=None, description="补充说明")


class QueryRecordsParams(BaseModel):
    metric_type: str | None = Field(default=None, description="指标类型，留空查询全部指标")
    days: int = Field(default=30, description="查询最近多少天，默认 30 天")


class TrendParams(BaseModel):
    metric_type: str = Field(description="要查看趋势的指标类型，例如 weight")
    days: int = Field(default=30, description="趋势区间天数，默认 30 天")


class ProfileParams(BaseModel):
    health_goal: str | None = Field(default=None, description="健康目标，例如减脂、康复")
    age: int | None = Field(default=None, description="年龄")
    height_cm: float | None = Field(default=None, description="身高，单位 cm")
    weight_kg: float | None = Field(default=None, description="体重，单位 kg")
    constraints: list[str] | None = Field(default=None, description="运动限制或既往不适")


class NoParams(BaseModel):
    pass


def _record_metric(params: RecordMetricParams, db: Session) -> dict:
    record = health_service.create_record(
        db,
        metric_type=params.metric_type.strip(),
        value=params.value,
        unit=params.unit,
        recorded_at=params.recorded_at,
        note=params.note,
    )
    return {
        "message": "健康记录已保存",
        "record": health_service.serialize_record(record),
    }


def _query_records(params: QueryRecordsParams, db: Session) -> dict:
    records = health_service.list_records(db, params.metric_type, params.days)
    return {
        "count": len(records),
        "records": [health_service.serialize_record(item) for item in records],
    }


def _trends(params: TrendParams, db: Session) -> dict:
    return health_service.build_trends(db, params.metric_type, params.days)


def _save_profile(params: ProfileParams, db: Session) -> dict:
    basic_info = {
        "age": params.age,
        "height_cm": params.height_cm,
        "weight_kg": params.weight_kg,
    }
    profile = memory_service.save_profile(
        db,
        basic_info=basic_info,
        health_goal=params.health_goal,
        constraints=params.constraints,
    )
    return {
        "message": "用户基础信息已更新",
        "profile": {
            "basic_info": profile.basic_info,
            "health_goal": profile.health_goal,
            "constraints": profile.constraints,
        },
    }


def _context(_params: NoParams, db: Session) -> dict:
    return memory_service.build_context(db)


def build_health_tools() -> list[WellnessTool]:
    return [
        WellnessTool(
            "record_health_metric",
            "记录一条健康指标（体重、睡眠、心率、步数、体脂率、饮水量），必须提供指标类型和数值",
            RecordMetricParams,
            _record_metric,
        ),
        WellnessTool(
            "query_health_records",
            "查询历史健康记录，用于了解用户近期的健康数据",
            QueryRecordsParams,
            _query_records,
        ),
        WellnessTool(
            "get_health_trends",
            "按日期聚合健康指标趋势，返回可用于绘图的趋势点",
            TrendParams,
            _trends,
        ),
        WellnessTool(
            "save_user_profile",
            "保存用户基础信息、健康目标与运动限制，供后续个性化方案使用",
            ProfileParams,
            _save_profile,
        ),
        WellnessTool(
            "get_health_context",
            "一次性获取用户画像、近期健康记录、长期记忆与当前运动计划",
            NoParams,
            _context,
        ),
    ]
