"""课程学习系统 - 任务生成引擎

根据课程阶段定义，自动生成多样化的训练任务。
支持参数化模板、随机组合、难度自适应调整。
"""

from __future__ import annotations

import random
from typing import List, Dict, Optional, Set, Any

from .types import TaskSample, StageDefinition, StageType, ToolMetadata


class TaskGenerator:
    """任务生成引擎

    功能：
    1. 根据阶段定义生成训练任务
    2. 管理任务模板库
    3. 支持难度自适应调整
    4. 保证任务多样性（避免重复）
    """

    def __init__(
        self,
        tool_registry: Optional[Dict[str, ToolMetadata]] = None,
        seed: int = 42,
        max_tasks_per_stage: int = 500,
    ):
        self.tool_registry = tool_registry or ToolMetadata.default_registry()
        self.rng = random.Random(seed)
        self.max_tasks_per_stage = max_tasks_per_stage
        self._generated_ids: Set[str] = set()

        # 模板库（按阶段类型组织）
        self._templates: Dict[StageType, List[Dict]] = self._init_templates()

    def generate_tasks(
        self,
        stage: StageDefinition,
        count: int,
        difficulty_override: Optional[float] = None,
        avoid_duplicates: bool = True,
    ) -> List[TaskSample]:
        """为指定阶段生成训练任务"""
        tasks: List[TaskSample] = []
        attempts = 0
        max_attempts = count * 5

        while len(tasks) < count and attempts < max_attempts:
            attempts += 1
            task = self._generate_single_task(stage, difficulty_override)

            if task is None:
                continue

            # 去重
            task_id = f"{stage.stage_id}_{len(self._generated_ids)}"
            task.task_id = task_id
            task.stage_id = stage.stage_id

            if avoid_duplicates and task_id in self._generated_ids:
                continue
            self._generated_ids.add(task_id)

            tasks.append(task)

        return tasks[:count]

    def _generate_single_task(
        self,
        stage: StageDefinition,
        difficulty_override: Optional[float] = None,
    ) -> Optional[TaskSample]:
        """生成单个任务"""
        templates = self._templates.get(stage.stage_type, [])
        if not templates and not stage.task_templates:
            return None

        # 选择模板
        if stage.task_templates:
            tmpl = self.rng.choice(stage.task_templates)
        else:
            tmpl = self.rng.choice(templates)

        difficulty = (
            difficulty_override
            if difficulty_override is not None
            else self.rng.uniform(*stage.difficulty_range)
        )

        return self._render_template(tmpl, stage, difficulty)

    def _render_template(
        self,
        template: Dict,
        stage: StageDefinition,
        difficulty: float,
    ) -> TaskSample:
        """渲染模板生成具体任务"""
        tools = stage.tools[:]
        self.rng.shuffle(tools)

        # 确定本任务使用的工具数量
        n_tools = self.rng.randint(
            min(stage.min_tools_per_task, len(tools)),
            min(stage.max_tools_per_task, len(tools)),
        )
        selected_tools = tools[: max(n_tools, 1)]

        # 构建具体问题
        question = self._build_question(template, selected_tools, difficulty)

        # 构建子目标提示
        subgoal_hint = self._build_subgoal_hint(selected_tools, stage)

        return TaskSample(
            task_id="",
            question=question,
            required_tools=selected_tools,
            subgoal_hint=subgoal_hint,
            difficulty=difficulty,
            stage_id=stage.stage_id,
            metadata={
                "template": template.get("description", "general"),
                "stage_type": stage.stage_type.value,
            },
        )

    def _build_question(
        self,
        template: Dict,
        tools: List[str],
        difficulty: float,
    ) -> str:
        """根据模板和工具构建问题"""
        # 尝试从模板直接获取
        if "question" in template and template["question"]:
            return template["question"]

        # 预定义问题模板
        single_tool_questions = {
            "search": [
                "Search for {topic}.",
                "Find information about {topic}.",
                "Look up {topic} on the internet.",
            ],
            "calculator": [
                "Calculate {expression}.",
                "Compute the value of {expression}.",
                "What is {expression}?",
            ],
            "code_executor": [
                "Write Python code to {task}.",
                "Implement a function that {task}.",
                "Using Python, {task}.",
            ],
            "file_reader": [
                "Read the contents of '{filename}'.",
                "Open '{filename}' and show its content.",
                "Read the first {n} lines of '{filename}'.",
            ],
            "file_writer": [
                "Write '{content}' to '{filename}'.",
                "Save the following data to '{filename}': {content}",
            ],
            "web_downloader": [
                "Download the file from {url}.",
                "Fetch data from the API at {url}.",
            ],
            "data_analyzer": [
                "Analyze the data in '{filename}' and calculate {statistic}.",
                "Read '{filename}' and compute {statistic}.",
            ],
            "visualizer": [
                "Create a {chart_type} of {data_description}.",
                "Visualize the data from '{filename}' as a {chart_type}.",
            ],
        }

        two_tool_questions = {
            ("search", "calculator"): [
                "Search for the population of {country}, then calculate {percentage}% of it.",
                "Find the GDP of {country} and compute its {percentage}%.",
            ],
            ("search", "code_executor"): [
                "Search for the API documentation of {library}, then write a code example.",
                "Find the Python syntax for {task}, then write a working code snippet.",
            ],
            ("calculator", "code_executor"): [
                "Calculate the time complexity of {algorithm} and write code to verify it.",
                "Compute {expression} and write a function that generalizes this calculation.",
            ],
            ("file_reader", "calculator"): [
                "Read the numbers from '{filename}' and calculate their {statistic}.",
                "Load data from '{filename}' and compute the {statistic}.",
            ],
            ("search", "file_writer"): [
                "Search for {topic} and save the result to '{filename}'.",
                "Find information about {topic} and write it to '{filename}'.",
            ],
        }

        if len(tools) == 1:
            tool = tools[0]
            q_templates = single_tool_questions.get(
                tool, [f"Use {tool} to solve this problem."]
            )
            q = self.rng.choice(q_templates)
            return self._fill_single_tool_placeholders(q, tool, difficulty)
        elif len(tools) == 2:
            pair = tuple(sorted(tools))
            q_templates = two_tool_questions.get(
                pair,
                [
                    f"Use {tools[0]} to gather information, then use {tools[1]} to process it.",
                    f"First use {tools[0]}, then use {tools[1]} to complete the task.",
                ],
            )
            q = self.rng.choice(q_templates)
            return self._fill_two_tool_placeholders(q, tools, difficulty)
        else:
            return self._build_multi_tool_question(tools, difficulty)

    def _fill_single_tool_placeholders(
        self, question: str, tool: str, difficulty: float
    ) -> str:
        """填充单工具问题的占位符"""
        placeholders = {
            "search": {
                "{topic}": self.rng.choice(
                    [
                        "the capital of France",
                        "the population of Japan",
                        "the boiling point of water",
                        "the author of '1984'",
                        "the chemical formula of salt",
                        "the speed of light",
                        "the distance from Earth to Moon",
                    ]
                ),
            },
            "calculator": {
                "{expression}": self.rng.choice(
                    [
                        "3.14 * 2.5",
                        "128 + 256",
                        "15% of 200",
                        "the square root of 144",
                        "2**10",
                        "0.1 + 0.2",
                        "(15 + 3) * 2",
                    ]
                ),
            },
            "code_executor": {
                "{task}": self.rng.choice(
                    [
                        "compute factorial of 10",
                        "check if a number is prime",
                        "sort a list of integers",
                        "calculate Fibonacci up to 20",
                        "find all prime numbers up to 100",
                        "reverse a string",
                    ]
                ),
            },
            "file_reader": {
                "{filename}": self.rng.choice(
                    ["data.txt", "config.json", "log.txt", "input.csv"]
                ),
                "{n}": str(self.rng.randint(3, 10)),
            },
            "file_writer": {
                "{content}": self.rng.choice(["Hello World", "Test data", "42"]),
                "{filename}": self.rng.choice(["output.txt", "result.txt", "test.log"]),
            },
            "web_downloader": {
                "{url}": self.rng.choice(
                    [
                        "https://example.com/data.csv",
                        "https://api.example.com/users",
                        "https://raw.githubusercontent.com/dataset.csv",
                    ]
                ),
            },
            "data_analyzer": {
                "{filename}": self.rng.choice(["sales.csv", "data.txt", "stats.json"]),
                "{statistic}": self.rng.choice(
                    ["sum", "average", "median", "standard deviation"]
                ),
            },
            "visualizer": {
                "{chart_type}": self.rng.choice(
                    ["bar chart", "line chart", "histogram", "scatter plot"]
                ),
                "{data_description}": self.rng.choice(
                    [
                        "monthly sales",
                        "temperature readings",
                        "population over time",
                        "stock prices",
                    ]
                ),
                "{filename}": self.rng.choice(
                    ["data.csv", "results.json", "stats.txt"]
                ),
            },
        }

        result = question
        for placeholder, options in placeholders.get(tool, {}).items():
            if placeholder in result:
                result = result.replace(placeholder, options, 1)
        return result

    def _fill_two_tool_placeholders(
        self, question: str, tools: List[str], difficulty: float
    ) -> str:
        """填充双工具问题的占位符"""
        # 对每个工具填充其对应的占位符
        result = question
        for tool in tools:
            result = self._fill_single_tool_placeholders(result, tool, difficulty)
        # 填充通用占位符
        if "{country}" in result:
            result = result.replace(
                "{country}",
                self.rng.choice(["China", "USA", "India", "Japan", "Germany"]),
                1,
            )
        if "{percentage}" in result:
            result = result.replace("{percentage}", str(self.rng.randint(5, 50)), 1)
        if "{library}" in result:
            result = result.replace(
                "{library}",
                self.rng.choice(["requests", "pandas", "numpy", "flask"]),
                1,
            )
        if "{algorithm}" in result:
            result = result.replace(
                "{algorithm}",
                self.rng.choice(["bubble sort", "binary search", "quicksort"]),
                1,
            )
        if "{filename}" in result:
            result = result.replace(
                "{filename}",
                self.rng.choice(["data.txt", "output.csv", "results.txt"]),
                1,
            )
        if "{statistic}" in result:
            result = result.replace(
                "{statistic}", self.rng.choice(["sum", "average", "max", "min"]), 1
            )
        if "{topic}" in result:
            result = result.replace(
                "{topic}",
                self.rng.choice(["Python", "machine learning", "blockchain", "AI"]),
                1,
            )
        return result

    def _build_multi_tool_question(self, tools: List[str], difficulty: float) -> str:
        """构建多工具链问题"""
        chains = [
            "Search for stock symbols of tech companies, fetch their data using code, "
            "calculate average P/E ratio, and create a visualization.",
            "Read a CSV file, clean the data using Python code, "
            "calculate statistics, and save results to a file.",
            "Search for a dataset online, download it, analyze with code, "
            "calculate summary statistics, and visualize the results.",
            "Search for API documentation, write code to call the API, "
            "parse the JSON response, compute metrics, and save to file.",
        ]

        if difficulty > 0.7:
            chains.extend(
                [
                    "Search for multiple sources about a topic, cross-validate the information, "
                    "compute aggregate statistics, and create a comprehensive report.",
                    "Read input data, validate it with code, fix any issues found, "
                    "perform analysis, and generate visualizations.",
                ]
            )

        return self.rng.choice(chains)

    def _build_subgoal_hint(
        self, tools: List[str], stage: StageDefinition
    ) -> List[str]:
        """构建子目标提示"""
        hints = []
        for tool in tools:
            meta = self.tool_registry.get(tool)
            if meta:
                hints.append(f"Use {tool}: {meta.description}")
        return hints

    def _init_templates(self) -> Dict[StageType, List[Dict]]:
        """初始化模板库"""
        return {
            StageType.TOOL_INTRODUCTION: [
                {"description": "single_tool_basic", "question": ""},
            ],
            StageType.TOOL_MASTERY: [
                {"description": "single_tool_advanced", "question": ""},
            ],
            StageType.TOOL_COMPOSITION: [
                {"description": "two_tool_seq"},
                {"description": "two_tool_parallel"},
            ],
            StageType.TOOL_CHAINING: [
                {"description": "three_tool_chain"},
                {"description": "four_tool_pipeline"},
            ],
            StageType.CONDITIONAL_BRANCHING: [
                {"description": "conditional_tool_choice"},
                {"description": "error_fallback"},
            ],
            StageType.ERROR_RECOVERY: [
                {"description": "retry_on_failure"},
                {"description": "alternative_tool_approach"},
            ],
            StageType.OPEN_ENDED: [
                {"description": "open_ended_problem"},
            ],
        }

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务生成统计"""
        return {
            "total_generated": len(self._generated_ids),
            "max_capacity": self.max_tasks_per_stage,
        }
