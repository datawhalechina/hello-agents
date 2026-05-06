# Data Analytics MCP Server - 技术方案

## 一、前因

### 1.1 现有架构分析

当前 `protocols/mcp` 目录下的核心实现包括：

- **`server.py`**: 基于 `fastmcp` 的服务器框架，提供 `MCPServer` 和 `MCPServerBuilder` 类
- **`client.py`**: 增强的 MCP 客户端，支持多种传输方式（Memory/stdio/HTTP/SSE）
- **`utils.py`**: 上下文管理和响应构建工具

核心方法：
- `list_tools()`: 列出所有可用工具
- `call_tool(tool_name, arguments)`: 调用指定工具
- `list_resources()` / `read_resource()`: 资源管理
- `list_prompts()` / `get_prompt()`: 提示词模板

### 1.2 需求背景

现有的示例服务器仅提供计算器和问候功能。为了满足企业级数据分析需求，需要扩展以下能力：
1. **数据库查询**: 从关系型数据库提取数据
2. **数据可视化**: 生成图表和数据表示
3. **报表生成**: 输出格式化报告

## 二、技术方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agent                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Client                                  │
│   list_tools() / call_tool() / list_resources()                │
└─────────────────────────────────────────────────────────────────┘
                              │
                    MCP Protocol (stdio/HTTP/SSE)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Data Analytics MCP Server                           │
│  ┌──────────────┬──────────────────┬──────────────────────┐    │
│  │   Database   │   Visualization  │      Reporting       │    │
│  │   Query Tool │   Tool           │      Tool            │    │
│  └──────────────┴──────────────────┴──────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Tool Orchestrator (工具编排器)                │ │
│  │   支持链式调用: Query → Visualize → Report                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 工具定义

#### 2.2.1 数据库查询工具 (`db_query`)

```python
def query_database(
    sql: str,                          # SQL 查询语句
    connection_string: str = None,     # 数据库连接字符串
    limit: int = 1000                 # 结果集上限
) -> Dict[str, Any]
```

**返回值结构:**
```json
{
    "success": true,
    "columns": ["id", "name", "value"],
    "rows": [...],
    "row_count": 100,
    "execution_time_ms": 45
}
```

#### 2.2.2 数据可视化工具 (`visualize_data`)

```python
def visualize_data(
    data: List[Dict],                  # 数据列表
    chart_type: str,                   # 图表类型: bar/line/pie/scatter
    title: str,                        # 图表标题
    x_axis: str,                       # X 轴字段
    y_axis: str,                       # Y 轴字段
    output_format: str = "base64"      # 输出格式: base64/json/markdown
) -> Dict[str, Any]
```

**支持的图表类型:**
- `bar`: 柱状图
- `line`: 折线图
- `pie`: 饼图
- `scatter`: 散点图

#### 2.2.3 报表生成工具 (`generate_report`)

```python
def generate_report(
    title: str,                        # 报表标题
    data: Any,                         # 数据（查询结果或可视化结果）
    sections: List[Dict],              # 报表章节配置
    format: str = "markdown"           # 输出格式: markdown/html/pdf
) -> Dict[str, Any]
```

### 2.3 工具协作机制

为了支持复杂任务，工具之间通过**上下文传递**实现协作：

```
用户: "分析销售数据，生成月销售额图表和报表"

                    ┌─────────────────────────────┐
                    │  Task Orchestrator         │
                    │  分析任务分解               │
                    └─────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
    │ db_query    │         │ visualize   │         │ generate    │
    │ 查询月销售  │────────▶│ data        │────────▶│ report      │
    │ 数据        │ 数据传递│ 生成图表    │ 图表嵌入 │ 输出报告    │
    └─────────────┘         └─────────────┘         └─────────────┘
```

**协作上下文 (AnalysisContext):**
```python
class AnalysisContext:
    query_result: Optional[QueryResult]  # 查询结果
    visualization: Optional[VisualizationResult]  # 可视化结果
    metadata: Dict[str, Any]            # 分析元数据
```

## 三、实现方案

### 3.1 文件结构

```
protocols/mcp/
├── __init__.py
├── server.py
├── client.py
├── utils.py
└── data_analytics/                    # 新增数据分析模块
    ├── __init__.py
    ├── server.py                      # 数据分析服务器
    ├── tools/
    │   ├── __init__.py
    │   ├── database.py                # 数据库查询工具
    │   ├── visualization.py            # 可视化工具
    │   └── reporting.py               # 报表生成工具
    ├── orchestrator.py                # 工具编排器
    └── models.py                      # 数据模型
```

### 3.2 核心类设计

#### 3.2.1 分析上下文 (AnalysisContext)

```python
@dataclass
class AnalysisContext:
    """分析上下文，用于工具间数据传递"""
    task_id: str
    query_result: Optional[QueryResult] = None
    visualization_result: Optional[VisualizationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]
    def from_dict(data: Dict) -> 'AnalysisContext'
```

#### 3.2.2 工具编排器 (ToolOrchestrator)

```python
class ToolOrchestrator:
    """工具编排器，支持复杂任务的链式执行"""
    
    def __init__(self, context: AnalysisContext):
        self.context = context
    
    async def execute_chain(self, steps: List[TaskStep]) -> AnalysisContext:
        """执行任务链"""
    
    async def query_and_visualize(
        self, sql: str, chart_type: str, **kwargs
    ) -> AnalysisContext:
        """查询+可视化一键执行"""
    
    async def full_analysis(
        self, sql: str, chart_type: str, report_title: str, **kwargs
    ) -> AnalysisContext:
        """完整分析流程: 查询+可视化+报表"""
```

## 四、使用示例

### 4.1 基础使用

```python
from protocols.mcp.data_analytics import DataAnalyticsServer

# 创建服务器
server = DataAnalyticsServer()

# 单独使用工具
server.add_tool(query_database, name="db_query")
server.add_tool(visualize_data, name="visualize_data")
server.add_tool(generate_report, name="generate_report")

# 运行服务器
server.run(transport="stdio")
```

### 4.2 客户端调用

```python
from protocols.mcp import MCPClient

async def main():
    async with MCPClient("data_analytics_server.py") as client:
        # 列出工具
        tools = await client.list_tools()
        print(f"可用工具: {[t['name'] for t in tools]}")
        
        # 执行查询
        result = await client.call_tool("db_query", {
            "sql": "SELECT month, sales FROM monthly_sales"
        })
        print(f"查询结果: {result}")
        
        # 生成可视化
        chart = await client.call_tool("visualize_data", {
            "data": result["rows"],
            "chart_type": "bar",
            "x_axis": "month",
            "y_axis": "sales"
        })
        
        # 生成报表
        report = await client.call_tool("generate_report", {
            "title": "月度销售分析报告",
            "data": result,
            "sections": [{"type": "chart", "data": chart}]
        })
```

### 4.3 链式调用

```python
from protocols.mcp.data_analytics import ToolOrchestrator

async def main():
    orchestrator = ToolOrchestrator(task_id="sales_analysis_001")
    
    # 一键执行完整分析流程
    context = await orchestrator.full_analysis(
        sql="SELECT * FROM sales WHERE date >= '2024-01-01'",
        chart_type="line",
        report_title="2024年度销售分析",
        x_axis="month",
        y_axis="revenue"
    )
    
    print(f"分析完成! 报表: {context.visualization_result}")
```

## 五、扩展计划

### 5.1 短期扩展
- [ ] 支持更多数据库 (PostgreSQL, SQLite)
- [ ] 增加更多图表类型 (热力图、雷达图)
- [ ] PDF 报表导出

### 5.2 长期规划
- [ ] 支持流式数据处理
- [ ] 增加机器学习模型集成
- [ ] 多数据源联合查询

## 六、测试用例

详见下方测试用例章节。

---

*文档版本: 1.0.0*  
*更新日期: 2026-04-16*
