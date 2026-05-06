"""策略协调器 (Policy Coordinator)

负责高层策略和低层策略之间的通信、状态同步和训练协调。
"""

import time
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(Enum):
    """执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SubgoalResult:
    """子目标执行结果"""

    index: int
    description: str
    status: ExecutionStatus
    trajectory: List[Dict] = field(default_factory=list)
    summary: str = ""
    steps_taken: int = 0
    error_message: str = ""
    timestamp: float = 0.0


@dataclass
class ExecutionReport:
    """完整执行报告"""

    task: str
    subgoals: List[SubgoalResult]
    total_steps: int = 0
    task_success: bool = False
    elapsed_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "task_success": self.task_success,
            "total_steps": self.total_steps,
            "elapsed_time": self.elapsed_time,
            "subgoals": [
                {
                    "index": sg.index,
                    "description": sg.description,
                    "status": sg.status.value,
                    "summary": sg.summary,
                    "steps_taken": sg.steps_taken,
                    "error": sg.error_message,
                }
                for sg in self.subgoals
            ],
        }


class PolicyCoordinator:
    """策略协调器

    职责：
    1. 将高层生成的子目标传递给低层
    2. 收集低层执行结果反馈给高层
    3. 管理状态信息更新
    4. 处理执行过程中的异常和回退

    协调协议：
    高层 → 低层: (subgoal, context) → 工具调用序列
    低层 → 高层: (result, summary, exit_status) → 下一步规划
    """

    def __init__(
        self,
        high_policy: Any,
        low_policy: Any,
        tool_executor: Optional[Callable] = None,
        max_global_steps: int = 50,
    ):
        self.high = high_policy
        self.low = low_policy
        self.tool_executor = tool_executor
        self.max_global_steps = max_global_steps

    def execute_task(
        self,
        task: str,
        tool_descriptions: str,
        **kwargs,
    ) -> ExecutionReport:
        """执行完整任务：规划 → 执行 → 汇报

        流程:
        1. 高层生成子目标序列
        2. 遍历每个子目标，调用低层执行
        3. 每个子目标完成后，收集结果
        4. 返回完整执行报告
        """
        start_time = time.time()
        global_steps = 0

        # 1. 高层规划
        subgoals = self.high.generate(task, tool_descriptions, **kwargs)
        if not subgoals:
            return ExecutionReport(
                task=task,
                subgoals=[],
                task_success=False,
            )

        subgoal_results = []

        # 2. 逐个子目标执行
        for i, sg in enumerate(subgoals):
            if global_steps >= self.max_global_steps:
                subgoal_results.append(
                    SubgoalResult(
                        index=i,
                        description=getattr(sg, "description", str(sg)),
                        status=ExecutionStatus.FAILED,
                        error_message="Max global steps reached",
                    )
                )
                break

            # 执行前检查依赖
            deps = getattr(sg, "depends_on", []) or []
            dep_failed = any(
                j < len(subgoal_results)
                and subgoal_results[j].status == ExecutionStatus.FAILED
                for j in deps
            )
            if dep_failed:
                subgoal_results.append(
                    SubgoalResult(
                        index=i,
                        description=getattr(sg, "description", str(sg)),
                        status=ExecutionStatus.FAILED,
                        error_message="Dependency failed",
                    )
                )
                continue

            # 低层执行
            expected = getattr(sg, "expected_output", "")
            description = getattr(sg, "description", str(sg))
            trajectory = self.low.execute(
                subgoal_description=description,
                expected_output=expected,
                tool_descriptions=tool_descriptions,
                **kwargs,
            )

            global_steps += len(trajectory)

            # 判断执行状态
            success = any(
                isinstance(step, dict) and step.get("type") == "finish"
                for step in trajectory
            )
            error_count = sum(
                1
                for step in trajectory
                if isinstance(step, dict)
                and str(step.get("observation", "")).startswith("Error")
            )
            status = (
                ExecutionStatus.SUCCESS
                if success
                else (
                    ExecutionStatus.PARTIAL
                    if error_count < len(trajectory)
                    else ExecutionStatus.FAILED
                )
            )

            result = SubgoalResult(
                index=i,
                description=description,
                status=status,
                trajectory=trajectory,
                summary=self._summarize_trajectory(trajectory),
                steps_taken=len(trajectory),
                error_message="" if success else f"{error_count} errors",
                timestamp=time.time(),
            )
            subgoal_results.append(result)

        # 3. 构建报告
        task_success = all(r.status == ExecutionStatus.SUCCESS for r in subgoal_results)

        return ExecutionReport(
            task=task,
            subgoals=subgoal_results,
            total_steps=global_steps,
            task_success=task_success,
            elapsed_time=time.time() - start_time,
        )

    def _summarize_trajectory(self, trajectory: List[Dict]) -> str:
        """总结执行轨迹"""
        tool_names = set()
        for step in trajectory:
            if isinstance(step, dict):
                tc = step.get("tool_call")
                if tc:
                    tool_names.add(getattr(tc, "tool_name", str(tc)))
        tools_used = ", ".join(sorted(tool_names)) if tool_names else "none"
        return f"Used tools: [{tools_used}], {len(trajectory)} steps"

    def compute_high_reward_from_report(
        self,
        report: ExecutionReport,
        optimal_subgoals: Optional[List] = None,
    ) -> Dict[str, float]:
        """从执行报告计算高层奖励"""
        completion = sum(
            1 for sg in report.subgoals if sg.status == ExecutionStatus.SUCCESS
        ) / max(len(report.subgoals), 1)

        dependency = 1.0
        for sg in report.subgoals:
            if sg.error_message == "Dependency failed":
                dependency -= 0.2

        n = len(report.subgoals)
        if 2 <= n <= 8:
            granularity = 1.0 - 0.1 * abs(n - 4)
        else:
            granularity = max(0.0, 0.3 if n == 1 else 1.0 - 0.1 * (n - 8))

        return {
            "completeness": completion,
            "dependency": max(0, dependency),
            "granularity": max(0, granularity),
            "task_success": 1.0 if report.task_success else 0.0,
        }

    def compute_low_reward_from_report(
        self,
        report: ExecutionReport,
    ) -> Dict[str, float]:
        """从执行报告计算低层奖励"""
        all_trajectories = [step for sg in report.subgoals for step in sg.trajectory]

        total_tool_calls = sum(
            1
            for step in all_trajectories
            if isinstance(step, dict) and step.get("type") == "tool_call"
        )
        successful_calls = sum(
            1
            for step in all_trajectories
            if isinstance(step, dict)
            and step.get("type") == "tool_call"
            and not str(step.get("observation", "")).startswith("Error")
        )

        subgoal_success_rate = sum(
            1
            for sg in report.subgoals
            if sg.status in (ExecutionStatus.SUCCESS, ExecutionStatus.PARTIAL)
        ) / max(len(report.subgoals), 1)

        return {
            "tool_correctness": successful_calls / max(total_tool_calls, 1)
            if total_tool_calls > 0
            else 0.5,
            "parameter_quality": 0.0,  # 需要更细粒度的分析
            "efficiency": subgoal_success_rate
            * min(1.0, 3.0 / max(report.total_steps / max(len(report.subgoals), 1), 1)),
            "error_recovery": 0.0,  # 需要跟踪错误恢复
        }
