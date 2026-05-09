"""课程学习系统 - 课程规划器

负责自动构建课程阶段序列，基于：
1. 工具依赖图（拓扑排序）
2. 工具难度评分
3. 教学法原则（先易后难、先独立后组合）
"""

from __future__ import annotations

from typing import List, Dict, Optional, Set, Tuple

from .types import ToolMetadata, StageDefinition, StageType


class CurriculumPlanner:
    """课程规划器 - 自动构建课程阶段序列

    规划原则:
    1. 无依赖工具先教（search, calculator, code_executor, file_reader）
    2. 有依赖工具后教（file_writer→file_reader, web_downloader→search）
    3. 单工具掌握后再组合
    4. 简单组合再到复杂链式调用
    5. 最后进行条件分支和错误恢复训练
    """

    def __init__(self, tool_registry: Optional[Dict[str, ToolMetadata]] = None):
        self.tool_registry = tool_registry or ToolMetadata.default_registry()

    def plan_stages(self) -> List[StageDefinition]:
        """自动规划完整的课程阶段序列"""
        sorted_tools = self._topological_sort()
        depth_map = self._compute_depths(sorted_tools)
        stages: List[StageDefinition] = []

        # ── 阶段 1-4: 逐个工具引入与掌握 ──
        for tool_name in sorted_tools:
            meta = self.tool_registry.get(tool_name)
            if not meta:
                continue

            # 引入阶段
            intro = meta.estimated_difficulty <= 0.4
            stage_type = (
                StageType.TOOL_INTRODUCTION if intro else StageType.TOOL_MASTERY
            )

            stages.append(
                StageDefinition(
                    stage_id=f"stage_{len(stages) + 1}_{tool_name}_intro",
                    stage_type=stage_type,
                    name=f"Introduce {tool_name}",
                    description=f"Learn to use the {tool_name} tool: {meta.description}",
                    tools=[tool_name],
                    min_tools_per_task=1,
                    max_tools_per_task=1,
                    min_tool_calls=1,
                    max_tool_calls=3,
                    min_subgoals=1,
                    max_subgoals=1,
                    allowed_subgoal_types=[self._tool_to_subgoal_type(tool_name)],
                    num_tasks=30,
                    difficulty_range=(0.0, 0.3),
                    task_templates=[
                        {"tool": tool_name, "examples": meta.teaching_examples},
                    ],
                )
            )

        # ── 阶段 5: 同深度工具配对 ──
        paired_stages = self._create_paired_stages(sorted_tools, depth_map)
        stages.extend(paired_stages)

        # ── 阶段 6: 多工具链（3+工具） ──
        if len(sorted_tools) >= 3:
            stages.append(
                StageDefinition(
                    stage_id=f"stage_{len(stages) + 1}_multi_tool_chain",
                    stage_type=StageType.TOOL_CHAINING,
                    name="Multi-Tool Chaining",
                    description="Use 3+ tools in sequence to complete complex tasks",
                    tools=sorted_tools[:],
                    min_tools_per_task=3,
                    max_tools_per_task=min(5, len(sorted_tools)),
                    min_tool_calls=3,
                    max_tool_calls=10,
                    min_subgoals=2,
                    max_subgoals=5,
                    num_tasks=150,
                    difficulty_range=(0.5, 0.75),
                )
            )

        # ── 阶段 7: 条件分支 ──
        stages.append(
            StageDefinition(
                stage_id=f"stage_{len(stages) + 1}_conditional",
                stage_type=StageType.CONDITIONAL_BRANCHING,
                name="Conditional Branching & Error Recovery",
                description="Handle conditional logic and recover from tool errors",
                tools=sorted_tools[:],
                min_tools_per_task=2,
                max_tools_per_task=len(sorted_tools),
                min_tool_calls=2,
                max_tool_calls=12,
                min_subgoals=3,
                max_subgoals=6,
                num_tasks=150,
                difficulty_range=(0.6, 0.85),
            )
        )

        # ── 阶段 8: 开放任务 ──
        stages.append(
            StageDefinition(
                stage_id=f"stage_{len(stages) + 1}_open_ended",
                stage_type=StageType.OPEN_ENDED,
                name="Open-Ended Problem Solving",
                description="Solve open-ended problems using all available tools",
                tools=sorted_tools[:],
                min_tools_per_task=1,
                max_tools_per_task=len(sorted_tools),
                min_tool_calls=1,
                max_tool_calls=15,
                min_subgoals=1,
                max_subgoals=8,
                num_tasks=200,
                difficulty_range=(0.7, 1.0),
            )
        )

        # 分配自增ID并检查连续性
        for i, stage in enumerate(stages):
            stage.stage_id = f"stage_{i + 1}_{stage.stage_type.value}"

        return stages

    def get_optimal_subgoals(self, task: str, tools: List[str]) -> List[str]:
        """为给定任务生成最优子目标提示（基于工具依赖关系）"""
        subgoals = []
        for tool in tools:
            meta = self.tool_registry.get(tool)
            if meta:
                subgoals.append(f"Use {tool} to {meta.description}")
        return subgoals

    def _topological_sort(self) -> List[str]:
        """拓扑排序：先教无依赖工具"""
        visited: Set[str] = set()
        result: List[str] = []

        def dfs(tool: str):
            if tool in visited:
                return
            visited.add(tool)
            meta = self.tool_registry.get(tool)
            if meta:
                for dep in meta.dependencies:
                    dfs(dep)
            result.append(tool)

        for tool_name in self.tool_registry:
            dfs(tool_name)

        return result

    def _compute_depths(self, sorted_tools: List[str]) -> Dict[str, int]:
        """计算每个工具的依赖深度"""
        depth: Dict[str, int] = {}
        for tool in sorted_tools:
            meta = self.tool_registry.get(tool)
            if not meta or not meta.dependencies:
                depth[tool] = 0
            else:
                depth[tool] = max(depth.get(d, 0) for d in meta.dependencies) + 1
        return depth

    def _tool_to_subgoal_type(self, tool_name: str) -> str:
        """工具名到子目标类型的映射"""
        mapping = {
            "search": "search",
            "calculator": "calculate",
            "code_executor": "code",
            "file_reader": "read_file",
            "file_writer": "write_file",
            "web_downloader": "search",
            "data_analyzer": "code",
            "visualizer": "code",
        }
        return mapping.get(tool_name, "reason")

    def _create_paired_stages(
        self,
        sorted_tools: List[str],
        depth_map: Dict[str, int],
    ) -> List[StageDefinition]:
        """创建工具配对阶段"""
        stages = []
        depth_groups: Dict[int, List[str]] = {}
        for tool, d in depth_map.items():
            depth_groups.setdefault(d, []).append(tool)

        used_pairs: Set[Tuple[str, str]] = set()
        for depth in sorted(depth_groups.keys()):
            group = depth_groups[depth]
            for i, t1 in enumerate(group):
                for t2 in group[i + 1 :]:
                    pair = tuple(sorted([t1, t2]))
                    if pair not in used_pairs:
                        used_pairs.add(pair)
                        stages.append(
                            StageDefinition(
                                stage_id=f"pair_{t1}_{t2}",
                                stage_type=StageType.TOOL_COMPOSITION,
                                name=f"Compose {t1} + {t2}",
                                description=f"Learn to combine {t1} and {t2} tools",
                                tools=[t1, t2],
                                min_tools_per_task=2,
                                max_tools_per_task=2,
                                min_tool_calls=2,
                                max_tool_calls=5,
                                min_subgoals=2,
                                max_subgoals=2,
                                num_tasks=60,
                                difficulty_range=(0.3, 0.5),
                                task_templates=[
                                    {"description": f"Chain {t1} → {t2}"},
                                    {
                                        "description": f"Use {t1} result as input for {t2}"
                                    },
                                ],
                            )
                        )

            # 不同深度工具配对（依赖关系配对）
            for deeper_depth in range(
                depth + 1, max(depth_map.values(), default=0) + 1
            ):
                if deeper_depth not in depth_groups:
                    continue
                for t1 in group:
                    for t2 in depth_groups[deeper_depth]:
                        pair = tuple(sorted([t1, t2]))
                        if pair not in used_pairs:
                            used_pairs.add(pair)
                            stages.append(
                                StageDefinition(
                                    stage_id=f"chain_{t1}_{t2}",
                                    stage_type=StageType.TOOL_COMPOSITION,
                                    name=f"Chain {t1} → {t2}",
                                    description=f"Chain {t1} result into {t2}",
                                    tools=[t1, t2],
                                    min_tools_per_task=2,
                                    max_tools_per_task=2,
                                    min_tool_calls=2,
                                    max_tool_calls=5,
                                    min_subgoals=2,
                                    max_subgoals=2,
                                    num_tasks=60,
                                    difficulty_range=(0.35, 0.55),
                                    task_templates=[
                                        {"description": f"Sequential: {t1} → {t2}"},
                                    ],
                                )
                            )

        return stages
