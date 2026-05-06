"""课程学习系统 - 主训练循环

整合所有子模块，提供完整的课程学习训练接口。
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Callable
from datetime import datetime

from .types import (
    CurriculumState,
    StageProgress,
    StageDefinition,
    TaskSample,
)
from .planner import CurriculumPlanner
from .task_generator import TaskGenerator
from .evaluator import TransitionEvaluator
from .difficulty import DifficultyAdapter
from .tracker import ProgressTracker


class CurriculumTrainer:
    """课程学习训练器 - 主循环

    使用示例:
        trainer = CurriculumTrainer()
        trainer.set_task_executor(my_executor_func)
        trainer.start()
        while not trainer.is_complete():
            task = trainer.next_task()
            result = agent.execute(task.question)
            trainer.record_result(task.task_id, result.success, result.steps)
        report = trainer.get_report()
    """

    def __init__(
        self,
        planner: Optional[CurriculumPlanner] = None,
        task_generator: Optional[TaskGenerator] = None,
        evaluator: Optional[TransitionEvaluator] = None,
        difficulty_adapter: Optional[DifficultyAdapter] = None,
        tracker: Optional[ProgressTracker] = None,
        output_dir: str = "./data/curriculum_progress",
        auto_resume: bool = True,
    ):
        self.planner = planner or CurriculumPlanner()
        self.task_generator = task_generator or TaskGenerator()
        self.evaluator = evaluator or TransitionEvaluator()
        self.difficulty = difficulty_adapter or DifficultyAdapter()
        self.tracker = tracker or ProgressTracker(output_dir)

        self._state: Optional[CurriculumState] = None
        self._stages: List[StageDefinition] = []
        self._task_executor: Optional[Callable] = None
        self._current_tasks: List[TaskSample] = []
        self._current_task_index: int = 0
        self._held_out_tasks: List[TaskSample] = []

        # 自动恢复
        if auto_resume:
            self._try_resume()

    # ── 初始化 ──

    def set_task_executor(self, executor: Callable[[str], Dict[str, Any]]):
        """设置任务执行回调"""
        self._task_executor = executor

    def start(self):
        """开始/重新开始课程学习"""
        if self._state is not None:
            print(f"Resuming curriculum from stage {self._state.current_stage_index}")
            return

        self._stages = self.planner.plan_stages()

        self._state = CurriculumState(
            current_stage_index=0,
            stages=[StageProgress(stage_id=s.stage_id) for s in self._stages],
            started_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )

        # 生成留出任务（用于评估泛化能力）
        if self._stages:
            last_stage = self._stages[-1]
            self._held_out_tasks = self.task_generator.generate_tasks(
                last_stage,
                count=30,
                difficulty_override=0.8,
            )

        print(f"Curriculum started: {len(self._stages)} stages")
        self._load_stage_tasks()

    def _try_resume(self):
        """尝试中断恢复"""
        saved = self.tracker.load_state()
        if saved is not None:
            self._state = saved
            self._stages = self.planner.plan_stages()
            # 确保 stages 数量匹配
            while len(self._state.stages) < len(self._stages):
                self._state.stages.append(
                    StageProgress(
                        stage_id=self._stages[len(self._state.stages)].stage_id
                    )
                )
            print(
                f"Resumed curriculum: stage {self._state.current_stage_index}, "
                f"{self._state.global_tasks_completed} tasks done"
            )
            # 检查已完成的阶段
            for i, sp in enumerate(self._state.stages):
                if i < len(self._stages):
                    sp.stage_id = self._stages[i].stage_id

    # ── 核心循环 ──

    def next_task(self) -> Optional[TaskSample]:
        """获取下一个训练任务

        Returns:
            任务样本，如果没有更多任务则返回 None
        """
        if self._state is None:
            self.start()

        if self._current_task_index >= len(self._current_tasks):
            # 当前批次用完，生成新的
            self._load_stage_tasks()

        if not self._current_tasks:
            # 尝试推进阶段
            if self._try_advance_stage():
                self._load_stage_tasks()
            else:
                return None

        if self._current_task_index >= len(self._current_tasks):
            return None

        task = self._current_tasks[self._current_task_index]
        self._current_task_index += 1
        return task

    def record_result(
        self,
        task_id: str,
        success: bool,
        steps: int,
        optimal_steps: int = 0,
        reward: float = 0.0,
        tool_usage: Optional[Dict[str, int]] = None,
    ):
        """记录任务执行结果

        Args:
            task_id: 任务ID
            success: 是否成功
            steps: 实际步数
            optimal_steps: 最优步数
            reward: 奖励值
            tool_usage: 工具使用统计
        """
        if self._state is None:
            return

        stage_idx = self._state.current_stage_index
        if stage_idx >= len(self._state.stages):
            return

        progress = self._state.stages[stage_idx]

        progress.tasks_completed += 1
        if success:
            progress.tasks_succeeded += 1
        progress.total_steps += steps
        progress.optimal_steps += optimal_steps or max(steps // 2, 1)
        progress.avg_reward = (
            progress.avg_reward * (progress.tasks_completed - 1) + reward
        ) / progress.tasks_completed

        # 更新工具使用统计
        if tool_usage:
            for tool, count in tool_usage.items():
                progress.tool_usage[tool] = progress.tool_usage.get(tool, 0) + count
            self._state.all_tool_usage[tool] = (
                self._state.all_tool_usage.get(tool, 0) + count
            )

        # 全局统计
        self._state.global_tasks_completed += 1
        self._state.global_avg_reward = (
            self._state.global_avg_reward * (self._state.global_tasks_completed - 1)
            + reward
        ) / max(self._state.global_tasks_completed, 1)

        # 难度适配
        self.difficulty.record_result(success, self._state.difficulty_level)
        self._state.difficulty_level = self.difficulty.get_adjusted_difficulty()

        # 定期保存
        if progress.tasks_completed % 10 == 0:
            self._save_progress()

        # 检查阶段过渡
        if progress.tasks_completed >= self._current_stage().num_tasks * 0.8:
            self._check_transition()

    def is_complete(self) -> bool:
        """检查课程是否全部完成"""
        if self._state is None:
            return False
        if self._state.current_stage_index >= len(self._stages) - 1:
            last_progress = self._state.stages[-1]
            if last_progress.is_completed:
                return True
            # 检查最后一个阶段的过渡评估
            verdict = self.evaluator.evaluate_stage(last_progress)
            return verdict.can_advance
        return False

    # ── 内部方法 ──

    def _load_stage_tasks(self):
        """加载当前阶段的任务"""
        if self._state is None:
            return

        stage = self._current_stage()
        if stage is None:
            self._current_tasks = []
            return

        difficulty = self._state.difficulty_level
        count = min(20, stage.num_tasks)

        self._current_tasks = self.task_generator.generate_tasks(
            stage,
            count=count,
            difficulty_override=difficulty,
        )
        self._current_task_index = 0

    def _current_stage(self) -> Optional[StageDefinition]:
        """获取当前阶段定义"""
        if self._state is None:
            return None
        idx = self._state.current_stage_index
        if idx >= len(self._stages):
            return None
        return self._stages[idx]

    def _try_advance_stage(self) -> bool:
        """尝试推进到下一阶段"""
        if self._state is None:
            return False

        stage_idx = self._state.current_stage_index
        if stage_idx >= len(self._stages) - 1:
            return False

        progress = self._state.stages[stage_idx]
        verdict = self.evaluator.evaluate_stage(progress)

        if verdict.can_advance:
            progress.is_completed = True
            progress.completed_at = datetime.now().isoformat()
            progress.readiness_score = verdict.current_score
            progress.bottleneck = verdict.bottleneck

            self._state.current_stage_index += 1
            self._state.last_updated = datetime.now().isoformat()

            print(
                f"Advanced to stage {self._state.current_stage_index}: "
                f"score={verdict.current_score:.3f}"
            )
            self._save_progress()
            return True

        return False

    def _check_transition(self):
        """检查并执行阶段过渡"""
        if self._state is None:
            return

        stage_idx = self._state.current_stage_index
        if stage_idx >= len(self._stages) - 1:
            return

        progress = self._state.stages[stage_idx]
        stage_def = self._stages[stage_idx]
        tasks_needed = max(30, stage_def.num_tasks // 2)

        if progress.tasks_completed < tasks_needed:
            return

        self._try_advance_stage()

    def _save_progress(self):
        """保存进度"""
        if self._state is not None:
            self._state.last_updated = datetime.now().isoformat()
            self.tracker.save_state(self._state)

            stage_idx = self._state.current_stage_index
            if stage_idx < len(self._state.stages):
                self.tracker.save_stage_progress(self._state.stages[stage_idx])

    def get_report(self) -> Dict[str, Any]:
        """获取课程报告"""
        if self._state is None:
            return {"status": "not_started"}

        return {
            "status": "completed" if self.is_complete() else "in_progress",
            "current_stage": self._state.current_stage_index,
            "total_stages": len(self._stages),
            "tasks_completed": self._state.global_tasks_completed,
            "avg_reward": self._state.global_avg_reward,
            "difficulty": self._state.difficulty_level,
            "stages": [
                {
                    "id": s.stage_id,
                    "completed": s.tasks_completed,
                    "succeeded": s.tasks_succeeded,
                    "success_rate": s.success_rate,
                    "avg_reward": round(s.avg_reward, 3),
                    "is_done": s.is_completed,
                }
                for s in self._state.stages
            ],
        }

    def summarize(self) -> str:
        """生成可读的课程摘要"""
        report = self.get_report()
        lines = [
            "=" * 60,
            "Curriculum Learning Summary",
            "=" * 60,
            f"Status: {report['status']}",
            f"Tasks Completed: {report['tasks_completed']}",
            f"Avg Reward: {report['avg_reward']:.3f}",
            f"Difficulty: {report['difficulty']:.2f}",
            "",
            "Stage Progress:",
        ]
        for s in report["stages"]:
            marker = (
                "✓"
                if s["is_done"]
                else "→"
                if s["id"] == report.get("current_stage_str", "")
                else " "
            )
            lines.append(
                f"  [{marker}] {s['id'][:40]:40s} "
                f"tasks={s['completed']:3d} "
                f"rate={s['success_rate']:.2f} "
                f"reward={s['avg_reward']:.3f}"
            )

        return "\n".join(lines)
