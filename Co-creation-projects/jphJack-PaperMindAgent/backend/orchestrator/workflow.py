"""动态工作流编排与降级：组合 Controller + Reflexion

核心职责：
- 调用 Controller.run 执行主流程
- 在关键步骤（抽取/Gap/创新）后插入 Reflexion 自校验
- 低于阈值的触发针对性补抽
- 降级策略：索引失败→跳过 RAG 仅用结构化字段；联网搜索失败→跳过新颖性去重
- 返回 {final_results, evaluation_data}（含工具调用记录、置信度统计、降级记录）
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from backend.llm.client import DeepSeekClient
from backend.memory.manager import MemoryManager
from backend.orchestrator.controller import Controller, ProgressCallback
from backend.orchestrator.reflexion import Reflexion
from backend.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

# 需要插入 Reflexion 自校验的关键步骤
REFLEXION_STEPS = {"Extractor", "GapAnalyzer", "InnovationGenerator"}


class WorkflowOrchestrator:
    """动态工作流编排器：组合 Controller + Reflexion

    在 Controller 的 Plan-and-Execute 主流程上叠加 Reflexion 自校验：
    1. Controller 规划并逐步执行；
    2. 关键步骤完成后，Reflexion 对照上下文自检质量；
    3. 低于阈值的触发针对性补抽/重试；
    4. 降级策略保证流程在部分失败时仍能继续。
    """

    def __init__(
        self,
        client: DeepSeekClient,
        registry: ToolRegistry,
        memory: MemoryManager,
    ) -> None:
        self.controller = Controller(client, registry, memory)
        self.reflexion = Reflexion(client)
        # 降级记录
        self.degradations: list[dict] = []

    async def run_pipeline(
        self,
        folder_path: Optional[str] = None,
        paper_ids: Optional[list[str]] = None,
        research_direction: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """执行完整工作流：Controller 主流程 + Reflexion 自校验 + 降级处理

        Args:
            folder_path: PDF 文件夹路径（与 paper_ids 二选一）
            paper_ids: 上传论文 ID 列表（与 folder_path 二选一）
            research_direction: 用户研究方向（可选）
            progress_callback: 进度回调

        Returns:
            {
                "final_results": 各步骤结果 dict,
                "evaluation_data": {
                    "tool_call_records": 工具调用记录,
                    "confidence_stats": 置信度统计,
                    "degradation_records": 降级记录,
                    "degraded_steps": 降级步骤,
                    "needs_human_review": 需人工复核的步骤,
                }
            }
        """
        # 重置降级记录
        self.degradations = []

        # 定义步骤后钩子：在关键步骤后插入 Reflexion 自校验
        async def post_step_hook(step: dict, result: dict) -> dict:
            return await self._reflexion_hook(step, result, progress_callback)

        # 调用 Controller.run 执行主流程（带 Reflexion 钩子）
        results = await self.controller.run(
            folder_path=folder_path,
            paper_ids=paper_ids,
            research_direction=research_direction,
            progress_callback=progress_callback,
            post_step_hook=post_step_hook,
        )

        # 处理 Controller 自身的降级记录
        for degraded in results.get("degraded_steps", []):
            self._record_degradation(
                degraded.get("step", ""), degraded.get("reason", "")
            )

        # 收集需人工复核的步骤
        needs_human_review = self._collect_human_review(results)

        # 编译评估数据
        evaluation_data = {
            "tool_call_records": results.get("tool_call_records", []),
            "confidence_stats": self.reflexion.get_confidence_stats(),
            "degradation_records": self.degradations,
            "degraded_steps": results.get("degraded_steps", []),
            "needs_human_review": needs_human_review,
        }

        logger.info(
            "工作流完成: 置信度统计=%s, 降级记录=%d 条, 需人工复核=%d 步",
            self.reflexion.get_confidence_stats(),
            len(self.degradations),
            len(needs_human_review),
        )

        # 从各步骤的 tool_calls 里聚合结构化数据，组装成 ReportAgent 期望的 4 字段
        steps_results = results.get("steps_results", {})
        final_results = self._build_final_results(steps_results)

        return {
            "final_results": final_results,
            "evaluation_data": evaluation_data,
        }

    def _build_final_results(self, steps_results: dict) -> dict:
        """从 steps_results 中各步骤的 tool_calls 聚合结构化数据。

        ReportAgent 期望的输入字段：
          - papers_records：步骤2 Extractor 抽取的 PaperRecord 列表
          - gaps：步骤4 GapAnalyzer 工具返回的 Gap 列表
          - innovations：步骤5 InnovationGenerator 工具返回的 Innovation 列表
          - experiment_plans：步骤6 ExperimentDesigner 工具返回的 ExperimentPlan 列表
        """
        final: dict = {
            "papers_records": [],
            "gaps": [],
            "innovations": [],
            "experiment_plans": [],
        }

        for step_num, step_result in steps_results.items():
            if not isinstance(step_result, dict):
                continue
            tool_calls = step_result.get("tool_calls", []) or []
            for tc in tool_calls:
                if not isinstance(tc, dict) or not tc.get("success"):
                    continue
                tool_name = tc.get("tool_name", "")
                result_data = tc.get("result")
                if result_data is None:
                    continue

                # extract_paper_structure：单条 PaperRecord dict
                if tool_name == "extract_paper_structure":
                    if isinstance(result_data, dict):
                        final["papers_records"].append(result_data)
                    elif isinstance(result_data, list):
                        final["papers_records"].extend(
                            [x for x in result_data if isinstance(x, dict)]
                        )

                # analyze_gaps：{"gaps": [...]}
                elif tool_name == "analyze_gaps":
                    gaps = (
                        result_data.get("gaps", [])
                        if isinstance(result_data, dict)
                        else []
                    )
                    final["gaps"].extend(gaps)

                # generate_innovations：{"innovations": [...]}
                elif tool_name == "generate_innovations":
                    innovations = (
                        result_data.get("innovations", [])
                        if isinstance(result_data, dict)
                        else []
                    )
                    final["innovations"].extend(innovations)

                # design_experiments：{"experiment_plans": [...]}
                elif tool_name == "design_experiments":
                    plans = (
                        result_data.get("experiment_plans", [])
                        if isinstance(result_data, dict)
                        else []
                    )
                    final["experiment_plans"].extend(plans)

        logger.info(
            "结构化数据聚合: papers=%d, gaps=%d, innovations=%d, plans=%d",
            len(final["papers_records"]),
            len(final["gaps"]),
            len(final["innovations"]),
            len(final["experiment_plans"]),
        )
        return final

    async def _reflexion_hook(
        self,
        step: dict,
        result: dict,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """步骤后 Reflexion 钩子：对关键步骤自校验，低于阈值触发针对性补抽

        Args:
            step: 计划步骤 dict
            result: 步骤执行结果
            progress_callback: 进度回调

        Returns:
            校验/重试后的结果
        """
        agent_name = step.get("agent", "")

        # 仅对关键步骤启用 Reflexion
        if agent_name not in REFLEXION_STEPS:
            return result

        # 构建自校验上下文（依赖步骤的结果）
        context = self._build_reflexion_context(step)

        # 定义针对性重试函数：重新执行该步骤
        async def retry_func() -> dict:
            logger.info("步骤 %s 触发针对性补抽/重试", agent_name)
            # 推送重试进度
            if progress_callback:
                await self.controller._emit_progress(
                    progress_callback,
                    agent_name,
                    "running",
                    f"步骤 {agent_name} 触发针对性重试",
                    0.0,
                    {"retry": True, "step": step.get("step")},
                )
            # 重新执行该步骤
            step_context = self.controller._build_context(step)
            return await self.controller._execute_step(
                step, step_context, progress_callback
            )

        # Reflexion 自校验 + 重试
        checked_result = await self.reflexion.reflect_and_retry(
            step_name=agent_name,
            result=result,
            context=context,
            retry_func=retry_func,
        )

        # 若重试后产生了新的工具调用记录，追加到 Controller
        if isinstance(checked_result, dict):
            new_tool_calls = checked_result.get("tool_calls", [])
            if new_tool_calls and new_tool_calls != result.get("tool_calls", []):
                self.controller.tool_call_records.extend(new_tool_calls)

        return checked_result

    def _build_reflexion_context(self, step: dict) -> str:
        """构建 Reflexion 自校验上下文：从依赖步骤的结果中提取"""
        depends_on = step.get("depends_on", [])
        if not depends_on:
            return ""
        parts: list[str] = []
        for dep in depends_on:
            if dep in self.controller.step_results:
                result = self.controller.step_results[dep]
                result_str = json.dumps(result, ensure_ascii=False, default=str)[
                    :3000
                ]
                parts.append(f"步骤 {dep} 结果：\n{result_str}")
        return "\n\n".join(parts)

    def _record_degradation(self, step: str, reason: str) -> None:
        """记录降级事件"""
        record = {
            "step": step,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self.degradations.append(record)
        logger.warning("降级记录: step=%s, reason=%s", step, reason)

    def _collect_human_review(self, results: dict) -> list[dict]:
        """收集需人工复核的步骤"""
        review_list: list[dict] = []
        steps_results = results.get("steps_results", {})
        for step_num, result in steps_results.items():
            if isinstance(result, dict) and result.get("needs_human_review"):
                review_list.append(
                    {
                        "step": step_num,
                        "agent": result.get("agent", ""),
                        "reflexion": result.get("reflexion", {}),
                    }
                )
        return review_list
