"""数据模型定义"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QueryResult:
    """数据库查询结果"""

    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    sql: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "sql": self.sql,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResult":
        return cls(
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            row_count=data.get("row_count", 0),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            sql=data.get("sql", ""),
        )


@dataclass
class VisualizationResult:
    """数据可视化结果"""

    chart_type: str
    title: str
    image_data: str
    format: str
    x_axis: str
    y_axis: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "chart_type": self.chart_type,
            "title": self.title,
            "image_data": self.image_data,
            "format": self.format,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "metadata": self.metadata,
        }


@dataclass
class ReportResult:
    """报表生成结果"""

    title: str
    content: str
    format: str
    sections: List[Dict[str, Any]]
    generated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "title": self.title,
            "content": self.content,
            "format": self.format,
            "sections": self.sections,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }


@dataclass
class TaskStep:
    """任务步骤定义"""

    step_id: str
    tool_name: str
    parameters: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskStep":
        return cls(
            step_id=data["step_id"],
            tool_name=data["tool_name"],
            parameters=data["parameters"],
            depends_on=data.get("depends_on", []),
        )
