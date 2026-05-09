# Data Analytics MCP Server

## 快速开始

### 安装依赖

```bash
pip install fastmcp pytest pytest-asyncio
```

### 运行服务器

```bash
python -m protocols.mcp.data_analytics.server
```

### 使用示例

```python
from protocols.mcp.data_analytics import (
    DataAnalyticsServer,
    ToolOrchestrator
)

# 方式1: 使用编排器
async def main():
    orchestrator = ToolOrchestrator(task_id="analysis_001")
    
    context = await orchestrator.full_analysis(
        sql="SELECT month, SUM(revenue) FROM sales GROUP BY month",
        chart_type="bar",
        report_title="Monthly Report",
        x_axis="month",
        y_axis="revenue"
    )
    
    print(context.report_result["content"])

# 方式2: 使用 MCP 客户端
from protocols.mcp import MCPClient

async def main():
    async with MCPClient("protocols/mcp/data_analytics/server.py") as client:
        tools = await client.list_tools()
        result = await client.call_tool("db_query", {
            "sql": "SELECT * FROM sales"
        })
```

## 工具列表

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `db_query` | 数据库查询 | `sql`, `connection_string`, `limit` |
| `init_sample_db` | 初始化示例数据库 | `connection_string` |
| `visualize_data` | 生成图表 | `data`, `chart_type`, `title`, `x_axis`, `y_axis` |
| `data_summary` | 数据摘要 | `data`, `title` |
| `generate_report` | 生成报表 | `title`, `data`, `sections`, `format` |
| `create_analysis_report` | 从分析结果创建报表 | `query_result`, `visualization_result`, `title` |
