"""工具编排器

支持工具间协作，实现复杂数据分析任务的链式执行。
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .models import TaskStep
from .tools.database import query_database
from .tools.visualization import visualize_data
from .tools.reporting import generate_report, create_report_from_analysis


@dataclass
class AnalysisContext:
    """分析上下文，用于工具间数据传递"""

    task_id: str
    query_result: Optional[Dict[str, Any]] = None
    visualization_result: Optional[Dict[str, Any]] = None
    report_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "query_result": self.query_result,
            "visualization_result": self.visualization_result,
            "report_result": self.report_result,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisContext":
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())),
            query_result=data.get("query_result"),
            visualization_result=data.get("visualization_result"),
            report_result=data.get("report_result"),
            metadata=data.get("metadata", {}),
        )

    def has_query_result(self) -> bool:
        return self.query_result is not None and self.query_result.get("success", False)

    def has_visualization(self) -> bool:
        return self.visualization_result is not None and self.visualization_result.get(
            "success", False
        )

    def has_report(self) -> bool:
        return self.report_result is not None and self.report_result.get(
            "success", False
        )


class ToolOrchestrator:
    """工具编排器，支持复杂任务的链式执行"""

    def __init__(self, task_id: Optional[str] = None):
        self.context = AnalysisContext(
            task_id=task_id or str(uuid.uuid4()),
            metadata={"created_at": datetime.now().isoformat()},
        )
        self._tools = {
            "db_query": query_database,
            "visualize_data": visualize_data,
            "generate_report": generate_report,
        }

    def register_tool(self, name: str, func: Callable) -> None:
        """注册自定义工具"""
        self._tools[name] = func

    def set_context(self, context: AnalysisContext) -> None:
        """设置分析上下文"""
        self.context = context

    def get_context(self) -> AnalysisContext:
        """获取当前分析上下文"""
        return self.context

    async def execute_step(self, step: TaskStep) -> Dict[str, Any]:
        """执行单个任务步骤"""
        tool_name = step.tool_name
        parameters = step.parameters.copy()

        for dep in step.depends_on:
            if dep == "query_result" and self.context.has_query_result():
                parameters.setdefault("data", self.context.query_result.get("rows", []))
            elif dep == "visualization" and self.context.has_visualization():
                parameters.setdefault("data", self.context.visualization_result)

        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_name}"}

        try:
            result = tool(**parameters)
            self.context.metadata[f"step_{step.step_id}"] = {
                "tool": tool_name,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            }
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_chain(self, steps: List[TaskStep]) -> AnalysisContext:
        """执行任务链

        Args:
            steps: 任务步骤列表

        Returns:
            更新后的分析上下文
        """
        for step in steps:
            result = await self.execute_step(step)

            if step.tool_name == "db_query":
                self.context.query_result = result
            elif step.tool_name == "visualize_data":
                self.context.visualization_result = result
            elif step.tool_name == "generate_report":
                self.context.report_result = result

            if not result.get("success", False):
                self.context.metadata["error"] = result.get("error")
                break

        self.context.metadata["completed_at"] = datetime.now().isoformat()
        return self.context

    async def query_and_visualize(
        self,
        sql: str,
        chart_type: str,
        title: str = "Data Visualization",
        x_axis: str = "x",
        y_axis: str = "y",
        **kwargs,
    ) -> AnalysisContext:
        """查询+可视化一键执行

        Args:
            sql: SQL 查询语句
            chart_type: 图表类型
            title: 图表标题
            x_axis: X 轴字段
            y_axis: Y 轴字段

        Returns:
            更新后的分析上下文
        """
        self.context.metadata["chain_type"] = "query_and_visualize"

        query_result = query_database(sql, **kwargs)
        self.context.query_result = query_result

        if not query_result.get("success", False):
            return self.context

        data = query_result.get("rows", [])
        visualization = visualize_data(
            data=data, chart_type=chart_type, title=title, x_axis=x_axis, y_axis=y_axis
        )
        self.context.visualization_result = visualization

        self.context.metadata["completed_at"] = datetime.now().isoformat()
        return self.context

    async def full_analysis(
        self,
        sql: str,
        chart_type: str,
        report_title: str,
        x_axis: str = "x",
        y_axis: str = "y",
        report_format: str = "markdown",
        **kwargs,
    ) -> AnalysisContext:
        """完整分析流程: 查询+可视化+报表

        Args:
            sql: SQL 查询语句
            chart_type: 图表类型
            report_title: 报表标题
            x_axis: X 轴字段
            y_axis: Y 轴字段
            report_format: 报表格式

        Returns:
            更新后的分析上下文
        """
        self.context.metadata["chain_type"] = "full_analysis"

        self.context = await self.query_and_visualize(
            sql=sql,
            chart_type=chart_type,
            title=report_title,
            x_axis=x_axis,
            y_axis=y_axis,
            **kwargs,
        )

        if self.context.has_query_result():
            report = create_report_from_analysis(
                query_result=self.context.query_result,
                visualization_result=self.context.visualization_result,
                title=report_title,
                format=report_format,
            )
            self.context.report_result = report

        self.context.metadata["completed_at"] = datetime.now().isoformat()
        return self.context

    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "task_id": self.context.task_id,
            "has_query": self.context.has_query_result(),
            "has_visualization": self.context.has_visualization(),
            "has_report": self.context.has_report(),
            "query_row_count": (
                self.context.query_result.get("row_count", 0)
                if self.context.has_query_result()
                else 0
            ),
            "chart_type": (
                self.context.visualization_result.get("chart_type")
                if self.context.has_visualization()
                else None
            ),
            "report_format": (
                self.context.report_result.get("format")
                if self.context.has_report()
                else None
            ),
            "metadata": self.context.metadata,
        }


async def create_analysis_pipeline(
    task_id: str, steps: List[Dict[str, Any]]
) -> AnalysisContext:
    """创建并执行分析管道（便捷函数）

    Args:
        task_id: 任务 ID
        steps: 步骤定义列表

    Returns:
        最终的分析上下文
    """
    orchestrator = ToolOrchestrator(task_id=task_id)

    task_steps = [
        TaskStep(
            step_id=step.get("step_id", f"step_{i}"),
            tool_name=step["tool_name"],
            parameters=step.get("parameters", {}),
            depends_on=step.get("depends_on", []),
        )
        for i, step in enumerate(steps)
    ]

    return await orchestrator.execute_chain(task_steps)
