import logging
from typing import Any

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from .daily_checkin import (
    AGENT_ALLOWED_CATEGORIES, CHECKIN_CATEGORY, nutrition_estimate_from_totals,
    validate_agent_daily_record,
)
from .storage import DailyRecordStore


logger = logging.getLogger(__name__)

#: query_daily_records 的返回条数上限。每条 record 可能包含完整 segments，
#: 不设上限时 limit=200 会直接把 ReAct 的观察撑爆。
_QUERY_LIMIT_MAX = 30


class SaveDailyRecordTool(Tool):
    def __init__(self, store: DailyRecordStore) -> None:
        super().__init__(
            name="save_daily_record",
            description=(
                "保存每日健康记录（恢复/营养/小结）。"
                f"category 只能是 {' / '.join(AGENT_ALLOWED_CATEGORIES)} 之一。"
                "营养记录优先使用 calories_kcal/protein_g/carbs_g/fat_g，"
                "中文同义字段也会被规范化；食物名、重量、餐次和备注不会保存。"
                "不能用本工具保存训练记录——训练由用户在侧栏确认或经 FIT 导入写入。"
            ),
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="date", type="string", description="日期，必须是 YYYY-MM-DD 的具体日期，不能用「今天」「昨天」", required=True),
            ToolParameter(
                name="category",
                type="string",
                description=f"记录分类，只能是 {' / '.join(AGENT_ALLOWED_CATEGORIES)} 之一",
                required=False,
                default="daily",
            ),
            ToolParameter(name="record", type="object", description="结构化记录内容，嵌套不超过 3 层", required=True),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        raw_date = parameters.get("date")
        raw_category = parameters.get("category", "daily")
        raw_record = parameters.get("record")

        try:
            record_date, category, record = validate_agent_daily_record(
                raw_date, raw_category, raw_record
            )
        except ValueError as exc:
            # 审计日志只记结构摘要，不记录原文，避免把健康细节写进日志
            logger.info(
                "tool=save_daily_record result=rejected date=%r category=%r fields=%s reason=%s",
                raw_date,
                raw_category,
                sorted(raw_record)[:10] if isinstance(raw_record, dict) else type(raw_record).__name__,
                exc,
            )
            return ToolResponse.error(code="INVALID_PARAM", message=str(exc))

        if category == "nutrition":
            # Nutrition belongs to the editable daily check-in. A same-day
            # update preserves weight, recovery, notes, and photo meal details.
            record.pop("source", None)
            record["nutrition_source"] = "agent_tool"
            record["meal_estimates"] = [nutrition_estimate_from_totals(record)]
            saved, _created, _folded = self.store.upsert_dated_record(
                date=record_date,
                category=CHECKIN_CATEGORY,
                record=record,
                additive_fields=("calories_kcal", "protein_g", "carbs_g", "fat_g"),
                append_fields=("meal_estimates",),
            )
        else:
            saved = self.store.add_record(date=record_date, category=category, record=record)
        logger.info(
            "tool=save_daily_record result=saved id=%s date=%s category=%s fields=%s",
            saved.get("id"),
            record_date,
            category,
            sorted(record),
        )
        return ToolResponse.success(
            text=f"已保存 {saved['date']} 的 {category} 记录。",
            data=saved,
        )


class QueryDailyRecordsTool(Tool):
    def __init__(self, store: DailyRecordStore) -> None:
        super().__init__(
            name="query_daily_records",
            description="查询每日健康与训练记录，可按日期过滤。",
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="date", type="string", description="可选，格式 YYYY-MM-DD", required=False),
            ToolParameter(
                name="limit",
                type="integer",
                description=f"最多返回条数（1-{_QUERY_LIMIT_MAX}）",
                required=False,
                default=7,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        date = parameters.get("date")
        limit = parameters.get("limit", 7)

        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            return ToolResponse.error(code="INVALID_PARAM", message="limit 必须是大于 0 的整数")
        # 每条 record 可能带着完整 segments，不封顶会把 ReAct 的观察撑爆。
        # 静默收窄而不是报错：模型的本意是"多查一些"，没必要为此浪费一步重试。
        limit = min(limit, _QUERY_LIMIT_MAX)

        rows = self.store.query_records(date=date, limit=limit)
        if not rows:
            return ToolResponse.success(
                text="未查询到符合条件的记录。",
                data={"items": []},
            )

        return ToolResponse.success(
            text=f"已查询到 {len(rows)} 条记录。",
            data={"items": rows},
        )
