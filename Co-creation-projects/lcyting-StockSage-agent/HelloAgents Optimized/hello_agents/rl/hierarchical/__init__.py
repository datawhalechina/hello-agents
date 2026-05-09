"""分层强化学习模块（Hierarchical RL for Tool-Use Agents）

本模块实现分层强化学习方案，用于训练智能体高效使用工具：
- 高层策略 (High-Level Policy): 负责任务规划，将任务分解为子目标序列
- 低层策略 (Low-Level Policy): 负责工具调用，执行具体子目标

架构:
    HighLevelPolicy (π_high)
        │  输出：子目标序列 [subgoal_1, subgoal_2, ..., subgoal_n]
        ▼
    LowLevelPolicy (π_low)
        │  输出：具体工具调用序列 [tool_call_1, tool_call_2, ...]
        ▼
    ToolEnvironment
        │  反馈：工具执行结果
        ▼
    HierarchicalRewardFunction
        │  高层奖励：子目标完成度
        │  低层奖励：工具调用正确性 + 效率
"""

from .high_level_policy import HighLevelPolicy, SubgoalConfig, SubgoalType
from .low_level_policy import LowLevelPolicy, ToolCallConfig
from .reward import HierarchicalReward, RewardComponent
from .trainer import HierarchicalGRPOTrainer, HierarchicalTrainingConfig
from .curriculum import (
    CurriculumTaskGenerator,
    StageConfig,
    StageReadinessEvaluator,
    ToolDependencyGraph,
)
from .coordinator import PolicyCoordinator, ExecutionReport, SubgoalResult

__all__ = [
    "HighLevelPolicy",
    "SubgoalConfig",
    "SubgoalType",
    "LowLevelPolicy",
    "ToolCallConfig",
    "HierarchicalReward",
    "RewardComponent",
    "HierarchicalGRPOTrainer",
    "HierarchicalTrainingConfig",
    "CurriculumTaskGenerator",
    "StageConfig",
    "StageReadinessEvaluator",
    "ToolDependencyGraph",
    "PolicyCoordinator",
    "ExecutionReport",
    "SubgoalResult",
]
