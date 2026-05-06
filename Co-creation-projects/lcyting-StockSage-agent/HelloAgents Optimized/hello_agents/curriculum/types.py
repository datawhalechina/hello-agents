"""课程学习系统 - 类型与核心定义

定义课程学习系统的所有数据类型：
- 课程阶段 (StageDefinition)
- 阶段类型 (StageType)
- 工具元数据 (ToolMetadata)
- 任务样本 (TaskSample)
- 评估指标 (EvaluationMetrics)
- 进度快照 (ProgressSnapshot)
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class StageType(Enum):
    """课程阶段类型"""

    TOOL_INTRODUCTION = "tool_introduction"
    """工具引入：单工具使用，学习基本调用方法"""

    TOOL_MASTERY = "tool_mastery"
    """工具掌握：同工具多场景使用，提高熟练度"""

    TOOL_COMPOSITION = "tool_composition"
    """工具组合：两个工具串联/并联使用"""

    TOOL_CHAINING = "tool_chaining"
    """工具链：三个以上工具按依赖顺序执行"""

    CONDITIONAL_BRANCHING = "conditional_branching"
    """条件分支：根据中间结果选择不同工具"""

    ERROR_RECOVERY = "error_recovery"
    """错误恢复：工具调用失败后的回退策略"""

    OPEN_ENDED = "open_ended"
    """开放任务：综合使用所有工具解决复杂问题"""


@dataclass
class ToolMetadata:
    """工具元数据 - 描述一个工具的教学属性"""

    name: str
    """工具名称"""
    description: str
    """工具描述"""
    dependencies: List[str] = field(default_factory=list)
    """依赖的工具列表"""
    estimated_difficulty: float = 0.5
    """估计难度 0.0~1.0"""
    parameter_complexity: int = 1
    """参数复杂度 1~5"""
    prerequisite_tools: List[str] = field(default_factory=list)
    """先修工具"""
    teaching_examples: List[str] = field(default_factory=list)
    """教学示例"""
    category: str = "general"
    """工具类别: search/calculation/code/file/data"""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def default_registry(cls) -> Dict[str, ToolMetadata]:
        """默认工具注册表"""
        return {
            "search": cls(
                name="search",
                description="搜索互联网获取信息",
                estimated_difficulty=0.3,
                parameter_complexity=2,
                category="search",
                teaching_examples=[
                    "Search for the capital of France.",
                    "Find the population of Japan.",
                    "Search for the author of the book '1984'.",
                ],
            ),
            "calculator": cls(
                name="calculator",
                description="执行数学计算",
                estimated_difficulty=0.2,
                parameter_complexity=1,
                category="calculation",
                teaching_examples=[
                    "Calculate 3.14 * 2.5.",
                    "What is 128 + 256?",
                    "Compute the square root of 144.",
                ],
            ),
            "code_executor": cls(
                name="code_executor",
                description="执行Python代码",
                estimated_difficulty=0.4,
                parameter_complexity=3,
                category="code",
                teaching_examples=[
                    "Write Python code to compute factorial of 10.",
                    "Sort the list [3, 1, 4, 1, 5, 9] using Python.",
                    "Calculate the Fibonacci sequence up to the 20th term.",
                ],
            ),
            "file_reader": cls(
                name="file_reader",
                description="读取文件内容",
                estimated_difficulty=0.3,
                parameter_complexity=2,
                category="file",
                teaching_examples=[
                    "Read the contents of 'data.txt'.",
                    "Read the first 5 lines of 'log.txt'.",
                ],
            ),
            "file_writer": cls(
                name="file_writer",
                description="写入文件内容",
                estimated_difficulty=0.4,
                parameter_complexity=2,
                dependencies=["file_reader"],
                prerequisite_tools=["file_reader"],
                category="file",
                teaching_examples=[
                    "Write 'Hello World' to 'output.txt'.",
                    "Save the calculation results to 'result.txt'.",
                ],
            ),
            "web_downloader": cls(
                name="web_downloader",
                description="从URL下载文件",
                estimated_difficulty=0.5,
                parameter_complexity=3,
                dependencies=["search"],
                prerequisite_tools=["search"],
                category="data",
                teaching_examples=[
                    "Download a CSV file from a URL.",
                    "Fetch JSON data from an API endpoint.",
                ],
            ),
            "data_analyzer": cls(
                name="data_analyzer",
                description="数据分析和统计",
                estimated_difficulty=0.6,
                parameter_complexity=4,
                dependencies=["code_executor", "file_reader"],
                prerequisite_tools=["code_executor", "file_reader"],
                category="data",
                teaching_examples=[
                    "Read sales.csv and calculate total revenue.",
                    "Analyze the distribution of values in data.txt.",
                ],
            ),
            "visualizer": cls(
                name="visualizer",
                description="数据可视化",
                estimated_difficulty=0.7,
                parameter_complexity=4,
                dependencies=["data_analyzer"],
                prerequisite_tools=["data_analyzer"],
                category="data",
                teaching_examples=[
                    "Create a bar chart of monthly sales.",
                    "Plot a histogram of age distribution.",
                ],
            ),
        }


@dataclass
class StageDefinition:
    """课程阶段定义"""

    stage_id: str
    """唯一阶段标识"""
    stage_type: StageType
    """阶段类型"""
    name: str
    """可读名称"""
    description: str
    """阶段描述"""
    tools: List[str]
    """本阶段可用工具列表"""
    min_tools_per_task: int = 1
    """每任务最少工具数"""
    max_tools_per_task: int = 2
    """每任务最多工具数"""
    min_tool_calls: int = 1
    """最少工具调用次数"""
    max_tool_calls: int = 5
    """最多工具调用次数"""
    min_subgoals: int = 1
    """最少子目标数"""
    max_subgoals: int = 3
    """最多子目标数"""
    allowed_subgoal_types: List[str] = field(default_factory=list)
    """允许的子目标类型"""
    num_tasks: int = 100
    """本阶段应生成的任务数量"""
    readiness_threshold: float = 0.75
    """进入下一阶段的阈值"""
    consecutive_evaluations: int = 3
    """连续通过评估次数"""
    difficulty_range: Tuple[float, float] = (0.0, 0.4)
    """难度范围 0.0~1.0"""
    task_templates: List[Dict[str, Any]] = field(default_factory=list)
    """任务模板"""
    hot_start_from: Optional[str] = None
    """从哪个阶段热启动（复用参数）"""

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["stage_type"] = self.stage_type.value
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> StageDefinition:
        d = dict(d)
        d["stage_type"] = StageType(d["stage_type"])
        return cls(**d)


@dataclass
class TaskSample:
    """任务样本 - 包含问题、期望答案、工具链、子目标"""

    task_id: str
    """任务唯一ID"""
    question: str
    """任务问题"""
    expected_answer: Optional[str] = None
    """期望答案"""
    required_tools: List[str] = field(default_factory=list)
    """需要的工具列表"""
    subgoal_hint: List[str] = field(default_factory=list)
    """子目标提示"""
    difficulty: float = 0.5
    """难度 0.0~1.0"""
    stage_id: str = ""
    """所属阶段"""
    category: str = "general"
    """任务类别"""
    metadata: Dict[str, Any] = field(default_factory=dict)
    """额外元数据"""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TaskSample:
        return cls(**d)


@dataclass
class StageProgress:
    """阶段进度"""

    stage_id: str
    tasks_completed: int = 0
    tasks_succeeded: int = 0
    total_steps: int = 0
    optimal_steps: int = 0
    tool_usage: Dict[str, int] = field(default_factory=dict)
    avg_reward: float = 0.0
    avg_efficiency: float = 0.0
    avg_robustness: float = 0.0
    avg_generalization: float = 0.0
    readiness_score: float = 0.0
    bottleneck: str = ""
    is_completed: bool = False
    completed_at: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.tasks_succeeded / max(self.tasks_completed, 1)

    @property
    def efficiency(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return min(1.0, self.optimal_steps / max(self.total_steps, 1))


@dataclass
class CurriculumState:
    """完整课程学习状态"""

    current_stage_index: int = 0
    stages: List[StageProgress] = field(default_factory=list)
    global_tasks_completed: int = 0
    global_avg_reward: float = 0.0
    all_tool_usage: Dict[str, int] = field(default_factory=dict)
    difficulty_level: float = 0.5
    started_at: str = ""
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_stage_index": self.current_stage_index,
            "stages": [s.__dict__ for s in self.stages],
            "global_tasks_completed": self.global_tasks_completed,
            "global_avg_reward": self.global_avg_reward,
            "all_tool_usage": self.all_tool_usage,
            "difficulty_level": self.difficulty_level,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CurriculumState:
        state = cls(**{k: v for k, v in d.items() if k != "stages"})
        state.stages = [StageProgress(**s) for s in d.get("stages", [])]
        return state
