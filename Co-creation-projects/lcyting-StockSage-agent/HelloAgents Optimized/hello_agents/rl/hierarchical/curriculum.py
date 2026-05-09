"""课程学习系统 (Curriculum Learning System)

从简单任务（使用少量工具）开始训练，逐步增加任务难度和工具数量。
包含课程顺序生成、阶段过渡评估、动态难度调整。
"""

import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class StageID(Enum):
    """课程阶段标识"""

    SINGLE_TOOL = "single_tool"  # 单工具掌握
    TWO_TOOL_COMPOSITION = "two_tool"  # 双工具组合
    MULTI_TOOL_PIPELINE = "multi_tool"  # 多工具链
    CONDITIONAL_RECOVERY = "conditional"  # 条件分支与错误恢复


@dataclass
class StageConfig:
    """课程阶段配置"""

    stage_id: StageID
    tools: List[str]  # 本阶段可用工具
    min_tools_per_task: int = 1  # 每任务最少工具数
    max_tools_per_task: int = 2  # 每任务最多工具数
    task_templates: List[Dict] = field(default_factory=list)
    min_subgoals: int = 1  # 最少子目标数
    max_subgoals: int = 3  # 最多子目标数
    num_tasks: int = 100  # 任务数
    readiness_threshold: float = 0.75  # 进入下一阶段的阈值
    consecutive_evaluations: int = 3  # 连续评估次数要求


class ToolDependencyGraph:
    """工具依赖图 - 自动构建课程顺序

    根据工具之间的依赖关系自动确定教学顺序：
    无依赖的工具先教，有依赖的工具后教。
    """

    def __init__(self, dependencies: Dict[str, List[str]] = None):
        self.dependencies = dependencies or {
            "search": [],
            "calculator": [],
            "code_executor": [],
            "file_reader": [],
            "file_writer": ["file_reader"],
            "web_downloader": ["search"],
            "data_analyzer": ["code_executor", "file_reader"],
            "visualizer": ["data_analyzer"],
        }

    def get_stages(self) -> List[StageConfig]:
        """根据依赖图自动生成课程阶段"""
        sorted_tools = self._topological_sort()
        stages = []

        # Stage 1: 单工具（每个工具独立学习）
        for tool in sorted_tools:
            if not self.dependencies.get(tool):
                stage = StageConfig(
                    stage_id=StageID.SINGLE_TOOL,
                    tools=[tool],
                    task_templates=self._generate_templates_for_tool(tool),
                    num_tasks=50,
                )
                stages.append(stage)

        # Stage 2: 双工具组合（相邻深度工具配对）
        depth_map = self._compute_depths(sorted_tools)
        paired_tools = []
        for depth in set(depth_map.values()):
            tools_at_depth = [t for t, d in depth_map.items() if d == depth]
            for t1 in tools_at_depth:
                for t2 in tools_at_depth:
                    if t1 < t2:
                        paired_tools.append([t1, t2])
        if paired_tools:
            stages.append(
                StageConfig(
                    stage_id=StageID.TWO_TOOL_COMPOSITION,
                    tools=list(set(sum(paired_tools, []))),
                    min_tools_per_task=2,
                    max_tools_per_task=2,
                    task_templates=[
                        {"description": "串联: tool1 → tool2"},
                    ],
                    num_tasks=100,
                )
            )

        # Stage 3: 多工具链（3+ 工具组合）
        all_tools = sorted_tools[:]
        if len(all_tools) >= 3:
            stages.append(
                StageConfig(
                    stage_id=StageID.MULTI_TOOL_PIPELINE,
                    tools=all_tools[:],
                    min_tools_per_task=3,
                    max_tools_per_task=min(5, len(all_tools)),
                    num_tasks=150,
                )
            )

        # Stage 4: 条件分支
        stages.append(
            StageConfig(
                stage_id=StageID.CONDITIONAL_RECOVERY,
                tools=sorted_tools[:],
                min_tools_per_task=2,
                max_tools_per_task=len(sorted_tools),
                task_templates=[
                    {"description": "条件分支 + 错误恢复"},
                    {"description": "多源交叉验证"},
                    {"description": "规划-执行-验证-回溯"},
                ],
                min_subgoals=3,
                max_subgoals=8,
                num_tasks=200,
            )
        )

        return stages

    def _topological_sort(self) -> List[str]:
        """拓扑排序：确定工具教学顺序"""
        visited = set()
        result = []

        def dfs(tool):
            if tool in visited:
                return
            visited.add(tool)
            for dep in self.dependencies.get(tool, []):
                dfs(dep)
            result.append(tool)

        for tool in self.dependencies:
            dfs(tool)

        return result

    def _compute_depths(self, sorted_tools: List[str]) -> Dict[str, int]:
        """计算每个工具的依赖深度"""
        depth = {}
        for tool in sorted_tools:
            deps = self.dependencies.get(tool, [])
            if not deps:
                depth[tool] = 0
            else:
                depth[tool] = max(depth.get(d, 0) for d in deps) + 1
        return depth

    def _generate_templates_for_tool(self, tool: str) -> List[Dict]:
        """为单个工具生成任务模板"""
        templates = {
            "search": [
                {"description": "搜索特定信息", "subgoals": 1},
                {"description": "搜索并筛选结果", "subgoals": 1},
            ],
            "calculator": [
                {"description": "计算数学表达式", "subgoals": 1},
            ],
            "code_executor": [
                {"description": "运行Python代码", "subgoals": 1},
                {"description": "实现并运行函数", "subgoals": 1},
            ],
            "file_reader": [
                {"description": "读取文件内容", "subgoals": 1},
            ],
        }
        return templates.get(tool, [{"description": f"使用 {tool}", "subgoals": 1}])


@dataclass
class ReadinessScore:
    """阶段过渡就绪度评分"""

    success_rate: float
    efficiency: float
    robustness: float
    generalization: float
    overall: float
    bottleneck: str  # 最弱维度

    def is_ready(self, threshold: float = 0.75) -> bool:
        return self.overall >= threshold


class StageReadinessEvaluator:
    """阶段过渡评估器 - 判断智能体是否准备好进入下一阶段

    使用多维度综合评分:
    - 任务成功率 (S_success)
    - 效率比 (S_efficiency)
    - 鲁棒性 (S_robustness)
    - 泛化能力 (S_generalization)

    要求连续 N 次评估超过阈值才允许过渡。
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.75,
        consecutive_count: int = 3,
    ):
        self.weights = weights or {
            "success_rate": 0.4,
            "efficiency": 0.25,
            "robustness": 0.15,
            "generalization": 0.2,
        }
        self.threshold = threshold
        self.consecutive_count = consecutive_count
        self.history: List[ReadinessScore] = []

    def evaluate(
        self,
        success_rate: float,
        steps_taken: int,
        optimal_steps: int,
        tool_usage_counts: Dict[str, int],
        total_attempts: int,
        held_out_success_rate: float,
    ) -> ReadinessScore:
        """计算综合就绪度评分"""
        # 效率
        efficiency = min(1.0, optimal_steps / max(steps_taken, 1))

        # 鲁棒性：所有工具都被使用且使用次数均匀
        if tool_usage_counts:
            min_count = min(tool_usage_counts.values())
            robustness = min_count / max(total_attempts, 1)
        else:
            robustness = 0.0

        # 综合评分
        overall = (
            self.weights["success_rate"] * success_rate
            + self.weights["efficiency"] * efficiency
            + self.weights["robustness"] * robustness
            + self.weights["generalization"] * held_out_success_rate
        )

        # 识别瓶颈
        scores = {
            "success_rate": success_rate,
            "efficiency": efficiency,
            "robustness": robustness,
            "generalization": held_out_success_rate,
        }
        bottleneck = min(scores, key=scores.get)

        score = ReadinessScore(
            success_rate=success_rate,
            efficiency=efficiency,
            robustness=robustness,
            generalization=held_out_success_rate,
            overall=overall,
            bottleneck=bottleneck,
        )

        self.history.append(score)
        return score

    def should_advance(self) -> bool:
        """判断是否应该进入下一阶段"""
        if len(self.history) < self.consecutive_count:
            return False
        recent = self.history[-self.consecutive_count :]
        return all(s.overall >= self.threshold for s in recent) and all(
            s.is_ready(self.threshold) for s in recent
        )

    def get_weakness_report(self) -> Dict[str, float]:
        """获取弱项报告：各维度的平均分"""
        if not self.history:
            return {}
        recent = self.history[-self.consecutive_count :]
        return {
            "success_rate": sum(s.success_rate for s in recent) / len(recent),
            "efficiency": sum(s.efficiency for s in recent) / len(recent),
            "robustness": sum(s.robustness for s in recent) / len(recent),
            "generalization": sum(s.generalization for s in recent) / len(recent),
        }


class CurriculumTaskGenerator:
    """课程任务生成器

    根据当前阶段和可用工具，自动生成符合要求的训练任务。
    支持动态难度调整：如果智能体表现好，增加难度；表现差，降低难度。
    """

    def __init__(
        self,
        tool_dep_graph: Optional[ToolDependencyGraph] = None,
        seed: int = 42,
    ):
        self.graph = tool_dep_graph or ToolDependencyGraph()
        self.rng = random.Random(seed)
        self.current_difficulty = 0.5  # 0.0~1.0

    def get_stages(self) -> List[StageConfig]:
        """获取课程阶段列表"""
        return self.graph.get_stages()

    def generate_tasks(
        self,
        stage: StageConfig,
        count: Optional[int] = None,
    ) -> List[str]:
        """为指定阶段生成训练任务"""
        n = count or stage.num_tasks
        tasks = []

        # 根据阶段选择策略
        if stage.stage_id == StageID.SINGLE_TOOL:
            tasks = self._generate_single_tool_tasks(stage, n)
        elif stage.stage_id == StageID.TWO_TOOL_COMPOSITION:
            tasks = self._generate_two_tool_tasks(stage, n)
        elif stage.stage_id == StageID.MULTI_TOOL_PIPELINE:
            tasks = self._generate_multi_tool_tasks(stage, n)
        elif stage.stage_id == StageID.CONDITIONAL_RECOVERY:
            tasks = self._generate_conditional_tasks(stage, n)

        # 应用难度调整
        tasks = self._adjust_difficulty(tasks)

        return tasks

    def _generate_single_tool_tasks(self, stage: StageConfig, n: int) -> List[str]:
        """生成单工具任务"""
        templates = {
            "search": [
                "Search for the capital of France.",
                "Find the population of Japan.",
                "Search for the latest Mars rover mission name.",
                "Find the author of the book '1984'.",
                "Search for the chemical formula of water.",
            ],
            "calculator": [
                "Calculate 3.14 * 2.5.",
                "What is 128 + 256?",
                "Calculate 15 percent of 200.",
                "Compute the square root of 144.",
                "What is 2^10?",
            ],
            "code_executor": [
                "Write Python code to compute factorial of 10.",
                "Implement a function to check if a number is prime.",
                "Sort the list [3, 1, 4, 1, 5, 9] using Python.",
                "Calculate the Fibonacci sequence up to the 20th term.",
                "Write code to find all prime numbers up to 100.",
            ],
            "file_reader": [
                "Read the contents of 'data.txt'.",
                "Read the first 5 lines of 'log.txt'.",
                "Read the configuration from 'config.json'.",
            ],
        }

        tasks = []
        for tool in stage.tools:
            tool_templates = templates.get(
                tool, [f"Use {tool} to solve a basic problem."]
            )
            for _ in range(n // max(len(stage.tools), 1)):
                tmpl = self.rng.choice(tool_templates)
                tasks.append(tmpl)

        return tasks[:n]

    def _generate_two_tool_tasks(self, stage: StageConfig, n: int) -> List[str]:
        """生成双工具组合任务"""
        combos = [
            (
                ["search", "calculator"],
                "Search for the population of China, then calculate what 10 percent of it is.",
            ),
            (["search", "calculator"], "Find the GDP of USA and calculate its 5%."),
            (
                ["search", "code_executor"],
                "Search for the API documentation of Python requests library, then write a code example.",
            ),
            (
                ["calculator", "code_executor"],
                "Calculate the time complexity of bubble sort and write code to verify.",
            ),
            (
                ["file_reader", "calculator"],
                "Read the numbers from 'numbers.txt' and calculate their sum.",
            ),
            (["search", "file_writer"], "Search for a poem and save it to 'poem.txt'."),
        ]

        tasks = []
        for _ in range(n):
            combo = self.rng.choice(combos)
            if all(t in stage.tools for t in combo[0]):
                tasks.append(combo[1])

        return tasks[: max(n, 1)]

    def _generate_multi_tool_tasks(self, stage: StageConfig, n: int) -> List[str]:
        """生成多工具链任务"""
        chains = [
            "Search for stock symbols of tech companies, fetch their data, calculate average P/E ratio.",
            "Read a CSV file, clean the data using code, then calculate statistics.",
            "Search for a dataset, download it, analyze with code, and visualize the results.",
            "Search for API documentation, write code to call the API, parse the JSON response, and compute metrics.",
        ]

        tasks = [self.rng.choice(chains) for _ in range(n)]
        return tasks

    def _generate_conditional_tasks(self, stage: StageConfig, n: int) -> List[str]:
        """生成条件分支任务"""
        tasks = [
            "Read a file that may not exist. If it doesn't exist, search for the information instead.",
            "Search for information from multiple sources, cross-validate, and pick the most reliable answer.",
            "Plan a data analysis pipeline, execute it, verify results, and fix any errors found.",
            "If the first tool fails, try an alternative approach. Report which method succeeded.",
        ]
        return [self.rng.choice(tasks) for _ in range(n)]

    def _adjust_difficulty(self, tasks: List[str]) -> List[str]:
        """根据当前难度调整任务"""
        if not tasks:
            return tasks

        # 简单任务不变，复杂任务按难度缩放
        if self.current_difficulty < 0.3:
            # 低难度：减少组合复杂度
            tasks = [t for t in tasks if len(t.split()) < 20][: max(len(tasks), 1)]
        elif self.current_difficulty > 0.7:
            # 高难度：增加要求
            tasks = [t + " Also explain your reasoning step by step." for t in tasks]

        return tasks

    def update_difficulty(self, success_rate: float):
        """根据最近成功率调整难度"""
        target_rate = 0.6  # 目标成功率
        delta = (success_rate - target_rate) * 0.1
        self.current_difficulty = max(0.0, min(1.0, self.current_difficulty + delta))
