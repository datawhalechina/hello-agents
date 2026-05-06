"""课程学习系统 - 进度跟踪器

管理课程学习状态的持久化：
1. 保存/加载进度快照
2. 序列化/反序列化
3. 恢复中断的训练
"""

from __future__ import annotations

import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from .types import CurriculumState, StageProgress


class ProgressTracker:
    """进度跟踪器 - 负责课程状态的持久化

    持久化位置: curriculum_progress.json（输出目录下）
    支持中途中断恢复。
    """

    def __init__(self, output_dir: str = "./data/curriculum_progress"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_state(
        self, state: CurriculumState, filename: str = "curriculum_state.json"
    ):
        """保存课程状态"""
        state.last_updated = datetime.now().isoformat()
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
        return str(filepath)

    def load_state(
        self, filename: str = "curriculum_state.json"
    ) -> Optional[CurriculumState]:
        """加载课程状态"""
        filepath = self.output_dir / filename
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CurriculumState.from_dict(data)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def save_stage_progress(
        self,
        progress: StageProgress,
        filename: str = "stage_progress.json",
    ):
        """保存单个阶段进度"""
        filepath = self.output_dir / filename
        existing = {}
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing = {}

        existing[progress.stage_id] = progress.__dict__

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    def load_stage_progress(
        self, stage_id: str, filename: str = "stage_progress.json"
    ) -> Optional[StageProgress]:
        """加载单个阶段进度"""
        filepath = self.output_dir / filename
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            stage_data = data.get(stage_id)
            if stage_data:
                return StageProgress(**stage_data)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            pass
        return None

    def export_report(
        self,
        state: CurriculumState,
        filename: str = "curriculum_report.json",
    ) -> str:
        """导出课程报告（详细版本）"""
        report = {
            "summary": {
                "current_stage": state.current_stage_index,
                "total_stages": len(state.stages),
                "tasks_completed": state.global_tasks_completed,
                "avg_reward": state.global_avg_reward,
                "difficulty": state.difficulty_level,
                "duration": self._compute_duration(state),
            },
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "tasks_completed": s.tasks_completed,
                    "success_rate": s.success_rate,
                    "efficiency": s.efficiency,
                    "avg_reward": s.avg_reward,
                    "is_completed": s.is_completed,
                    "bottleneck": s.bottleneck,
                }
                for s in state.stages
            ],
        }

        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return str(filepath)

    def _compute_duration(self, state: CurriculumState) -> str:
        """计算训练持续时间"""
        if not state.started_at:
            return "unknown"
        try:
            start = datetime.fromisoformat(state.started_at)
            end = datetime.fromisoformat(state.last_updated or state.started_at)
            delta = end - start
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s"
        except (ValueError, TypeError):
            return "unknown"

    def list_snapshots(self) -> List[str]:
        """列出所有已保存的快照"""
        return [str(p) for p in self.output_dir.glob("*.json")]
