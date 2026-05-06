"""Data Analytics MCP Server

数据分析 MCP 服务器，整合数据库查询、数据可视化和报表生成工具。
支持工具间协作完成复杂的数据分析任务。
"""

from typing import Dict, Any, Optional, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from fastmcp import FastMCP

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None


def _create_data_analytics_server() -> "DataAnalyticsServer":
    """工厂函数：创建数据分析服务器"""
    return DataAnalyticsServer()


class DataAnalyticsServer:
    """数据分析 MCP 服务器

    提供以下核心工具：
    - query_database: 数据库查询
    - visualize_data: 数据可视化
    - generate_report: 报表生成

    支持工具间协作：
    - ToolOrchestrator: 任务编排器
    - 支持链式调用: Query → Visualize → Report
    """

    def __init__(self, name: str = "data-analytics"):
        if not FASTMCP_AVAILABLE:
            raise ImportError(
                "Data Analytics Server requires 'fastmcp' library. "
                "Install it with: pip install fastmcp"
            )

        self.mcp = FastMCP(name=name)
        self.name = name
        self._register_tools()

    def _register_tools(self):
        """注册所有内置工具"""
        from .tools.database import query_database, init_sample_database
        from .tools.visualization import visualize_data, visualize_summary
        from .tools.reporting import generate_report, create_report_from_analysis

        self.mcp.tool(name="db_query", description="Execute SQL query on database")(
            query_database
        )
        self.mcp.tool(
            name="init_sample_db", description="Initialize sample database for testing"
        )(init_sample_database)
        self.mcp.tool(name="visualize_data", description="Generate chart from data")(
            visualize_data
        )
        self.mcp.tool(
            name="data_summary", description="Generate data summary statistics"
        )(visualize_summary)
        self.mcp.tool(
            name="generate_report",
            description="Generate formatted report from analysis results",
        )(generate_report)
        self.mcp.tool(
            name="create_analysis_report",
            description="Create report from query and visualization results",
        )(create_report_from_analysis)

    def add_tool(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """添加工具到服务器

        Args:
            func: 工具函数
            name: 工具名称（可选）
            description: 工具描述（可选）
        """
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""

        self.mcp.tool(name=tool_name, description=tool_desc)(func)

    def add_custom_tool(self, name: str, func: Callable, description: str = "") -> None:
        """添加自定义工具（便捷方法）

        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
        """
        self.mcp.tool(name=name, description=description)(func)

    def run(self, transport: str = "stdio", **kwargs):
        """运行服务器

        Args:
            transport: 传输方式 ("stdio", "http", "sse")
            **kwargs: 传输特定的参数
        """
        self.mcp.run(transport=transport, **kwargs)

    def get_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return {
            "name": self.name,
            "description": "Data Analytics MCP Server - Query, Visualize, Report",
            "protocol": "MCP",
            "tools": [
                "db_query",
                "init_sample_db",
                "visualize_data",
                "data_summary",
                "generate_report",
                "create_analysis_report",
            ],
        }


def run_server():
    """运行数据分析服务器（入口点）"""
    server = DataAnalyticsServer()
    print("Data Analytics MCP Server")
    print(f"Name: {server.name}")
    print("Transport: stdio")
    print(f"Tools: {', '.join(server.get_info()['tools'])}")
    server.run(transport="stdio")


if __name__ == "__main__":
    run_server()
