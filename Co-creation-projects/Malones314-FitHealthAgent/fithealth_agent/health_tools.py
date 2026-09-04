"""HelloAgents tools for querying imported wellness and sleep data."""

from __future__ import annotations

import json
from typing import Any

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from .health_store import HealthStore


def _without_raw_sleep(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    sleep = result.get("sleep")
    if sleep:
        excluded = {"raw", "id", "import_id", "created_at"}
        result["sleep"] = {key: value for key, value in sleep.items() if key not in excluded}
    return result


def _tool_text(prefix: str, data: Any) -> str:
    return f"{prefix}\n{json.dumps(data, ensure_ascii=False, separators=(',', ':'))}"


class QueryDailyHealthTool(Tool):
    def __init__(self, store: HealthStore) -> None:
        super().__init__(
            name="query_daily_health",
            description="查询某一天导入的全天心率摘要和睡眠总结。日期表示本地日期/睡眠醒来日期。",
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="date", type="string", description="日期 YYYY-MM-DD", required=True),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        day = parameters.get("date")
        try:
            data = _without_raw_sleep(self.store.get_daily_health(str(day or "")))
        except ValueError:
            return ToolResponse.error(code="INVALID_DATE", message="日期格式必须为 YYYY-MM-DD")
        if not any(value for key, value in data.items() if key != "date"):
            return ToolResponse.success(text=f"{day} 没有已导入的健康数据。", data=data)
        return ToolResponse.success(
            text=_tool_text(f"{day} 的已导入健康数据如下：", data),
            data=data,
        )


class QueryHealthRangeTool(Tool):
    def __init__(self, store: HealthStore) -> None:
        super().__init__(
            name="query_health_range",
            description="查询最多31天的每日心率与睡眠摘要，用于趋势比较。",
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="start_date", type="string", description="开始日期 YYYY-MM-DD", required=True),
            ToolParameter(name="end_date", type="string", description="结束日期 YYYY-MM-DD", required=True),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        start = str(parameters.get("start_date") or "")
        end = str(parameters.get("end_date") or "")
        try:
            items = [
                _without_raw_sleep(item)
                for item in self.store.get_health_range(start, end)
            ]
        except ValueError as exc:
            return ToolResponse.error(code="INVALID_RANGE", message=str(exc))
        available = sum(bool(item["heart_rate"] or item["sleep"]) for item in items)
        return ToolResponse.success(
            text=_tool_text(
                f"查询范围共 {len(items)} 天，其中 {available} 天有数据。每日摘要如下：",
                items,
            ),
            data={"start_date": start, "end_date": end, "items": items},
        )


class QuerySleepTool(Tool):
    def __init__(self, store: HealthStore) -> None:
        super().__init__(
            name="query_sleep",
            description="按醒来日期查询睡眠时长、阶段、分数、夜间心率、血氧、呼吸和HRV。",
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="date", type="string", description="醒来日期 YYYY-MM-DD", required=True),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        day = str(parameters.get("date") or "")
        try:
            item = self.store.get_sleep(day)
        except ValueError:
            return ToolResponse.error(code="INVALID_DATE", message="日期格式必须为 YYYY-MM-DD")
        if item is None:
            return ToolResponse.success(text=f"{day} 没有已导入的睡眠总结。", data={"item": None})
        for key in ("raw", "id", "import_id", "created_at"):
            item.pop(key, None)
        return ToolResponse.success(
            text=_tool_text(f"{day}（醒来日期）的睡眠数据如下：", item),
            data={"item": item},
        )


class QueryHeartRateWindowTool(Tool):
    def __init__(self, store: HealthStore) -> None:
        super().__init__(
            name="query_heart_rate_window",
            description="统计指定北京时间窗口内的心率最小值、最大值、平均值和样本数，不返回原始序列。",
        )
        self.store = store

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间 ISO 8601；无时区时按 Asia/Shanghai",
                required=True,
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间 ISO 8601；窗口最多7天",
                required=True,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        try:
            data = self.store.query_heart_rate_window(
                str(parameters.get("start_time") or ""),
                str(parameters.get("end_time") or ""),
            )
        except ValueError as exc:
            return ToolResponse.error(code="INVALID_TIME_WINDOW", message=str(exc))
        if data["sample_count"] == 0:
            return ToolResponse.success(text="该时间窗口没有有效心率样本。", data=data)
        return ToolResponse.success(
            text=_tool_text(
                f"该窗口有 {data['sample_count']} 个有效心率时间点，统计如下：", data
            ),
            data=data,
        )
