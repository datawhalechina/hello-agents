"""工具调用追踪器：记录与统计工具调用情况"""
from __future__ import annotations

import logging
from typing import Optional

from backend.models.schemas import ToolCallRecord

logger = logging.getLogger(__name__)


class ToolCallTracker:
    """工具调用追踪器：维护工具调用记录，提供成功率与分工具统计"""

    def __init__(self) -> None:
        # 维护全部工具调用记录（按调用先后顺序）
        self.records: list[ToolCallRecord] = []

    def record(
        self,
        tool_name: str,
        args_summary: str,
        success: bool,
        duration_sec: float,
        error: Optional[str] = None,
    ) -> ToolCallRecord:
        """记录一次工具调用

        参数：
            tool_name: 工具名称
            args_summary: 参数摘要（通常为截断后的 JSON 字符串）
            success: 是否调用成功
            duration_sec: 耗时（秒）
            error: 失败时的错误信息，成功时为 None
        """
        record = ToolCallRecord(
            tool_name=tool_name,
            args_summary=args_summary,
            success=success,
            duration_sec=duration_sec,
            error=error,
        )
        self.records.append(record)
        return record

    def record_from_dict(self, record_dict: dict) -> Optional[ToolCallRecord]:
        """从 dict 记录一次工具调用（接收 Controller 累计的 tool_calls）

        兼容 ToolCallRecord.model_dump() 产出的字典格式，
        timestamp 字段若存在则忽略（由 ToolCallRecord 自动生成）。
        """
        if not isinstance(record_dict, dict):
            logger.warning("record_from_dict 接收非 dict 入参: %r", type(record_dict))
            return None

        tool_name = record_dict.get("tool_name", "")
        args_summary = record_dict.get("args_summary", "")
        success = bool(record_dict.get("success", False))
        try:
            duration_sec = float(record_dict.get("duration_sec", 0.0))
        except (TypeError, ValueError):
            duration_sec = 0.0
        error = record_dict.get("error")

        return self.record(
            tool_name=tool_name,
            args_summary=args_summary,
            success=success,
            duration_sec=duration_sec,
            error=error,
        )

    def success_rate(self) -> float:
        """返回成功率 0-1，无记录时返回 0.0"""
        if not self.records:
            return 0.0
        success_count = sum(1 for r in self.records if r.success)
        return success_count / len(self.records)

    def summary(self) -> dict:
        """返回汇总统计

        结构：
            {
                total, success, failed, success_rate,
                by_tool: {tool_name: {total, success, rate}}
            }
        """
        total = len(self.records)
        success = sum(1 for r in self.records if r.success)
        failed = total - success
        rate = self.success_rate()

        # 按工具名聚合
        by_tool: dict[str, dict] = {}
        for r in self.records:
            entry = by_tool.setdefault(
                r.tool_name, {"total": 0, "success": 0, "rate": 0.0}
            )
            entry["total"] += 1
            if r.success:
                entry["success"] += 1
        for entry in by_tool.values():
            entry["rate"] = (
                entry["success"] / entry["total"] if entry["total"] else 0.0
            )

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": rate,
            "by_tool": by_tool,
        }

    def to_report(self) -> list[dict]:
        """返回所有记录的 dict 列表（可直接序列化）"""
        return [r.model_dump() for r in self.records]
