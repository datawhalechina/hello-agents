"""评估汇总：组合工具调用追踪与输出质量评估，产出统一评估结果"""
from __future__ import annotations

import logging
from typing import Optional

from backend.evaluator.quality import QualityEvaluator
from backend.evaluator.tracker import ToolCallTracker
from backend.llm.client import DeepSeekClient
from backend.models.schemas import EvaluationReport, ThreeDScore, ToolCallRecord

logger = logging.getLogger(__name__)


class Evaluator:
    """评估汇总器：组合 ToolCallTracker + QualityEvaluator"""

    def __init__(
        self,
        tracker: Optional[ToolCallTracker] = None,
        quality: Optional[QualityEvaluator] = None,
        client: Optional[DeepSeekClient] = None,
    ) -> None:
        self.tracker = tracker or ToolCallTracker()
        # 优先复用传入的 quality；否则用 client 构造（client 为 None 时 quality 内部走单例）
        self.quality = quality or QualityEvaluator(client=client)

    async def evaluate(
        self,
        pipeline_results: dict,
        tool_call_records: list[dict],
        confidence_stats: dict,
    ) -> dict:
        """汇总评估：创新点三维评分、工具调用成功率、平均置信度

        参数：
            pipeline_results: 流水线产出，至少包含 innovations 列表与可选的 final_report
            tool_call_records: Controller 累计的工具调用记录 dict 列表
            confidence_stats: 自校验置信度统计，形如 {avg_confidence, ...}

        返回：
            {innovations_scores, tool_call_success_rate, total_tool_calls,
             failed_tool_calls, avg_confidence, tool_calls, quality_assessment}
        """
        # 1. 录入工具调用记录
        for rec in tool_call_records or []:
            self.tracker.record_from_dict(rec)

        summary = self.tracker.summary()
        tool_call_success_rate = summary["success_rate"]
        total_tool_calls = summary["total"]
        failed_tool_calls = summary["failed"]

        # 2. 创新点三维评分
        innovations = (
            pipeline_results.get("innovations", [])
            if isinstance(pipeline_results, dict)
            else []
        )
        if not isinstance(innovations, list):
            innovations = []
        innovations_scores = await self.quality.evaluate_innovations(innovations)

        # 3. 平均置信度
        avg_confidence = 0.0
        if isinstance(confidence_stats, dict):
            try:
                avg_confidence = float(confidence_stats.get("avg_confidence", 0.0))
            except (TypeError, ValueError):
                avg_confidence = 0.0

        # 4. 报告整体质量评估
        final_report = (
            pipeline_results.get("final_report")
            if isinstance(pipeline_results, dict)
            else None
        )
        if not isinstance(final_report, dict):
            # 退化：用 pipeline_results 自身作为报告概览
            final_report = (
                pipeline_results if isinstance(pipeline_results, dict) else {}
            )
        quality_assessment = await self.quality.evaluate_report(final_report)

        return {
            "innovations_scores": innovations_scores,
            "tool_call_success_rate": tool_call_success_rate,
            "total_tool_calls": total_tool_calls,
            "failed_tool_calls": failed_tool_calls,
            "avg_confidence": avg_confidence,
            "tool_calls": self.tracker.to_report(),
            "quality_assessment": quality_assessment,
        }

    def build_evaluation_report(self, eval_data: dict) -> dict:
        """转为 EvaluationReport 兼容格式（返回 dict，便于序列化）

        将 evaluate() 产出的 eval_data 映射到 EvaluationReport schema，
        额外保留 quality_assessment 字段以供下游使用。
        """
        # 构造 ThreeDScore 列表
        innovations_scores: list[ThreeDScore] = []
        for item in eval_data.get("innovations_scores", []):
            if not isinstance(item, dict):
                continue
            score = item.get("score", {})
            if not isinstance(score, dict):
                score = {}
            try:
                innovations_scores.append(
                    ThreeDScore(
                        novelty=float(score.get("novelty", 0.0)),
                        feasibility=float(score.get("feasibility", 0.0)),
                        significance=float(score.get("significance", 0.0)),
                    )
                )
            except Exception as exc:
                logger.warning("ThreeDScore 构造失败: %s", exc)

        # 构造 ToolCallRecord 列表
        tool_calls: list[ToolCallRecord] = []
        for rec in eval_data.get("tool_calls", []):
            if not isinstance(rec, dict):
                continue
            try:
                tool_calls.append(
                    ToolCallRecord(
                        tool_name=rec.get("tool_name", ""),
                        args_summary=rec.get("args_summary", ""),
                        success=bool(rec.get("success", False)),
                        duration_sec=float(rec.get("duration_sec", 0.0)),
                        error=rec.get("error"),
                    )
                )
            except Exception as exc:
                logger.warning("ToolCallRecord 构造失败: %s", exc)

        report = EvaluationReport(
            innovations_scores=innovations_scores,
            tool_call_success_rate=float(eval_data.get("tool_call_success_rate", 0.0)),
            total_tool_calls=int(eval_data.get("total_tool_calls", 0)),
            failed_tool_calls=int(eval_data.get("failed_tool_calls", 0)),
            avg_confidence=float(eval_data.get("avg_confidence", 0.0)),
            tool_calls=tool_calls,
        )
        # 兼容 EvaluationReport 字段，同时保留质量评估附加信息
        result = report.model_dump()
        result["quality_assessment"] = eval_data.get("quality_assessment")
        return result
