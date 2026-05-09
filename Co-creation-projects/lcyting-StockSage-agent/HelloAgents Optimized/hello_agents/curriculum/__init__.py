"""课程学习系统 (Curriculum Learning System)

从简单任务（使用少量工具）开始训练，逐步增加任务难度和工具数量。
"""

from .types import (
    StageDefinition,
    StageType,
    ToolMetadata,
    TaskSample,
    StageProgress,
    CurriculumState,
)
from .planner import CurriculumPlanner
from .task_generator import TaskGenerator
from .evaluator import TransitionEvaluator, TransitionVerdict
from .difficulty import DifficultyAdapter, DifficultyConfig
from .tracker import ProgressTracker
from .trainer import CurriculumTrainer
from .visualizer import CurriculumVisualizer

__all__ = [
    "StageDefinition",
    "StageType",
    "ToolMetadata",
    "TaskSample",
    "StageProgress",
    "CurriculumState",
    "CurriculumPlanner",
    "TaskGenerator",
    "TransitionEvaluator",
    "TransitionVerdict",
    "DifficultyAdapter",
    "DifficultyConfig",
    "ProgressTracker",
    "CurriculumTrainer",
    "CurriculumVisualizer",
]
