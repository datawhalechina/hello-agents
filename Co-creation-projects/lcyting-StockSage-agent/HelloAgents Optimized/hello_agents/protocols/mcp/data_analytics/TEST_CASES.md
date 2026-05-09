# Data Analytics MCP Server - 测试用例

## 一、单元测试

### 1.1 数据库查询工具测试

```python
# tests/test_database.py
import pytest
from protocols.mcp.data_analytics.tools.database import (
    query_database,
    init_sample_database
)


class TestQueryDatabase:
    """数据库查询工具测试"""
    
    def test_simple_select_query(self):
        """测试简单的 SELECT 查询"""
        result = query_database("SELECT 1 as id, 'test' as name")
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ["id", "name"]
        assert result["rows"][0]["id"] == 1
        assert result["rows"][0]["name"] == "test"
    
    def test_query_with_limit(self):
        """测试带 LIMIT 的查询"""
        init_sample_database()
        result = query_database(
            "SELECT * FROM sales",
            limit=3
        )
        
        assert result["success"] is True
        assert result["row_count"] <= 3
    
    def test_reject_non_select_query(self):
        """测试拒绝非 SELECT 语句"""
        result = query_database("DELETE FROM sales WHERE id = 1")
        
        assert result["success"] is False
        assert "Only SELECT" in result["error"]
    
    def test_reject_multiple_statements(self):
        """测试拒绝多语句"""
        result = query_database("SELECT 1; SELECT 2")
        
        assert result["success"] is False
        assert "Multiple statements" in result["error"]
    
    def test_query_with_aggregation(self):
        """测试聚合查询"""
        init_sample_database()
        result = query_database(
            "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY region"
        )
        
        assert result["success"] is True
        assert len(result["rows"]) == 2  # North, South
    
    def test_invalid_sql_syntax(self):
        """测试无效 SQL 语法"""
        result = query_database("SELEC * FROM nonexistent")
        
        assert result["success"] is False
        assert "error" in result


class TestInitSampleDatabase:
    """示例数据库初始化测试"""
    
    def test_init_sample_database(self):
        """测试初始化示例数据库"""
        result = init_sample_database()
        
        assert result["success"] is True
        
        # 验证数据已插入
        query_result = query_database("SELECT COUNT(*) as cnt FROM sales")
        assert query_result["rows"][0]["cnt"] > 0
```

### 1.2 数据可视化工具测试

```python
# tests/test_visualization.py
import pytest
import base64
from protocols.mcp.data_analytics.tools.visualization import (
    visualize_data,
    visualize_summary
)


class TestVisualizeData:
    """数据可视化工具测试"""
    
    def test_bar_chart_generation(self):
        """测试柱状图生成"""
        data = [
            {"month": "Jan", "sales": 100},
            {"month": "Feb", "sales": 150},
            {"month": "Mar", "sales": 120}
        ]
        
        result = visualize_data(
            data=data,
            chart_type="bar",
            title="Monthly Sales",
            x_axis="month",
            y_axis="sales",
            output_format="json"
        )
        
        assert result["success"] is True
        assert result["chart_type"] == "bar"
        assert result["title"] == "Monthly Sales"
        assert result["metadata"]["data_points"] == 3
    
    def test_line_chart_generation(self):
        """测试折线图生成"""
        data = [
            {"x": 1, "y": 10},
            {"x": 2, "y": 20},
            {"x": 3, "y": 15}
        ]
        
        result = visualize_data(
            data=data,
            chart_type="line",
            title="Trend",
            x_axis="x",
            y_axis="y",
            output_format="ascii"
        )
        
        assert result["success"] is True
        assert "●" in result["image_data"]  # ASCII line chart marker
    
    def test_svg_output(self):
        """测试 SVG 输出格式"""
        data = [{"label": "A", "value": 50}]
        
        result = visualize_data(
            data=data,
            chart_type="bar",
            title="Test",
            x_axis="label",
            y_axis="value",
            output_format="svg"
        )
        
        assert result["success"] is True
        assert "<svg" in result["image_data"]
        assert "<rect" in result["image_data"]
    
    def test_base64_output(self):
        """测试 Base64 输出格式"""
        data = [{"label": "A", "value": 50}]
        
        result = visualize_data(
            data=data,
            chart_type="pie",
            title="Test",
            x_axis="label",
            y_axis="value",
            output_format="base64"
        )
        
        assert result["success"] is True
        # 验证是有效的 base64
        decoded = base64.b64decode(result["image_data"])
        assert b"<svg" in decoded
    
    def test_invalid_chart_type(self):
        """测试无效图表类型"""
        data = [{"x": 1, "y": 2}]
        
        result = visualize_data(
            data=data,
            chart_type="invalid_type",
            title="Test",
            x_axis="x",
            y_axis="y"
        )
        
        assert result["success"] is False
        assert "Unsupported chart type" in result["error"]
    
    def test_missing_axis_field(self):
        """测试缺失轴字段"""
        data = [{"x": 1, "y": 2}]
        
        result = visualize_data(
            data=data,
            chart_type="bar",
            title="Test",
            x_axis="nonexistent",
            y_axis="y"
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_empty_data(self):
        """测试空数据"""
        result = visualize_data(
            data=[],
            chart_type="bar",
            title="Empty",
            x_axis="x",
            y_axis="y"
        )
        
        assert result["success"] is False


class TestVisualizeSummary:
    """数据摘要测试"""
    
    def test_summary_generation(self):
        """测试摘要生成"""
        data = [
            {"id": 1, "value": 100, "name": "A"},
            {"id": 2, "value": 200, "name": "B"},
            {"id": 3, "value": 150, "name": "C"}
        ]
        
        result = visualize_summary(data, title="Test Summary")
        
        assert result["success"] is True
        assert result["summary"]["total_records"] == 3
        assert result["summary"]["fields"] == ["id", "value", "name"]
        assert "value" in result["summary"]["numeric_fields"]
        assert result["summary"]["value"]["min"] == 100
        assert result["summary"]["value"]["max"] == 200
```

### 1.3 报表生成工具测试

```python
# tests/test_reporting.py
import pytest
from protocols.mcp.data_analytics.tools.reporting import (
    generate_report,
    create_report_from_analysis
)


class TestGenerateReport:
    """报表生成工具测试"""
    
    def test_markdown_report_with_table(self):
        """测试 Markdown 表格报表"""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
        
        result = generate_report(
            title="User Report",
            data=data,
            format="markdown"
        )
        
        assert result["success"] is True
        assert result["format"] == "markdown"
        assert "# User Report" in result["content"]
        assert "| name | age |" in result["content"]
        assert "Alice" in result["content"]
    
    def test_markdown_report_with_query_result(self):
        """测试包含查询结果的报表"""
        query_result = {
            "sql": "SELECT * FROM users",
            "rows": [{"id": 1, "name": "Test"}],
            "row_count": 1
        }
        
        result = generate_report(
            title="Query Report",
            data=query_result,
            format="markdown"
        )
        
        assert result["success"] is True
        assert "SELECT * FROM users" in result["content"]
        assert "Query Results" in result["content"]
    
    def test_html_report_generation(self):
        """测试 HTML 报表生成"""
        data = [{"col": "value"}]
        
        result = generate_report(
            title="HTML Report",
            data=data,
            format="html"
        )
        
        assert result["success"] is True
        assert "<!DOCTYPE html>" in result["content"]
        assert "<table>" in result["content"]
        assert "<h1>HTML Report</h1>" in result["content"]
    
    def test_custom_sections(self):
        """测试自定义章节"""
        sections = [
            {"type": "text", "title": "Introduction", "content": "This is intro"},
            {"type": "chart", "title": "Chart Section", "data": {"chart_type": "bar"}}
        ]
        
        result = generate_report(
            title="Custom Report",
            data=None,
            sections=sections,
            format="markdown"
        )
        
        assert result["success"] is True
        assert "1. Introduction" in result["content"]
        assert "2. Chart Section" in result["content"]
    
    def test_invalid_format(self):
        """测试无效格式"""
        result = generate_report(
            title="Test",
            data={},
            format="invalid"
        )
        
        assert result["success"] is False
        assert "Unsupported format" in result["error"]


class TestCreateReportFromAnalysis:
    """从分析结果创建报表测试"""
    
    def test_create_report_with_visualization(self):
        """测试创建带可视化的报表"""
        query_result = {
            "success": True,
            "rows": [{"month": "Jan", "sales": 100}],
            "row_count": 1,
            "sql": "SELECT month, sales FROM data"
        }
        
        visualization_result = {
            "success": True,
            "chart_type": "bar",
            "image_data": "<svg>...</svg>"
        }
        
        result = create_report_from_analysis(
            query_result=query_result,
            visualization_result=visualization_result,
            title="Analysis Report",
            format="markdown"
        )
        
        assert result["success"] is True
        assert "Query Results" in result["content"]
        assert "Data Visualization" in result["content"]
    
    def test_create_report_without_visualization(self):
        """测试无可视化报表"""
        query_result = {
            "success": True,
            "rows": [],
            "row_count": 0
        }
        
        result = create_report_from_analysis(
            query_result=query_result,
            title="Query Only Report"
        )
        
        assert result["success"] is True
        assert "Query Results" in result["content"]
```

## 二、集成测试

### 2.1 工具协作测试

```python
# tests/test_orchestrator.py
import pytest
import asyncio
from protocols.mcp.data_analytics.orchestrator import (
    ToolOrchestrator,
    AnalysisContext,
    create_analysis_pipeline
)


class TestToolOrchestrator:
    """工具编排器测试"""
    
    @pytest.mark.asyncio
    async def test_query_and_visualize_chain(self):
        """测试查询+可视化链式调用"""
        # 初始化示例数据
        from protocols.mcp.data_analytics.tools.database import init_sample_database
        init_sample_database()
        
        orchestrator = ToolOrchestrator(task_id="test_001")
        
        context = await orchestrator.query_and_visualize(
            sql="SELECT month, SUM(revenue) as total FROM sales GROUP BY month",
            chart_type="bar",
            title="Monthly Revenue",
            x_axis="month",
            y_axis="total"
        )
        
        assert context.has_query_result()
        assert context.query_result["success"] is True
        assert context.has_visualization()
        assert context.visualization_result["chart_type"] == "bar"
    
    @pytest.mark.asyncio
    async def test_full_analysis_chain(self):
        """测试完整分析流程"""
        from protocols.mcp.data_analytics.tools.database import init_sample_database
        init_sample_database()
        
        orchestrator = ToolOrchestrator(task_id="test_002")
        
        context = await orchestrator.full_analysis(
            sql="SELECT region, SUM(revenue) as rev FROM sales GROUP BY region",
            chart_type="pie",
            report_title="Regional Sales Report",
            x_axis="region",
            y_axis="rev",
            report_format="markdown"
        )
        
        assert context.has_query_result()
        assert context.has_visualization()
        assert context.has_report()
        assert context.report_result["format"] == "markdown"
    
    def test_analysis_context_state(self):
        """测试分析上下文状态"""
        context = AnalysisContext(task_id="test_003")
        
        assert not context.has_query_result()
        assert not context.has_visualization()
        assert not context.has_report()
        
        context.query_result = {"success": True, "rows": []}
        assert context.has_query_result()
        
        context.visualization_result = {"success": True, "chart_type": "bar"}
        assert context.has_visualization()
    
    def test_get_summary(self):
        """测试获取分析摘要"""
        orchestrator = ToolOrchestrator(task_id="test_004")
        
        orchestrator.context.query_result = {
            "success": True,
            "row_count": 10
        }
        orchestrator.context.visualization_result = {
            "success": True,
            "chart_type": "line"
        }
        orchestrator.context.report_result = {
            "success": True,
            "format": "html"
        }
        
        summary = orchestrator.get_summary()
        
        assert summary["task_id"] == "test_004"
        assert summary["has_query"] is True
        assert summary["has_visualization"] is True
        assert summary["has_report"] is True
        assert summary["query_row_count"] == 10


class TestCreateAnalysisPipeline:
    """分析管道测试"""
    
    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        """测试创建分析管道"""
        from protocols.mcp.data_analytics.tools.database import init_sample_database
        init_sample_database()
        
        steps = [
            {
                "step_id": "step1",
                "tool_name": "db_query",
                "parameters": {
                    "sql": "SELECT * FROM sales LIMIT 5"
                }
            },
            {
                "step_id": "step2",
                "tool_name": "visualize_data",
                "parameters": {
                    "chart_type": "bar",
                    "title": "Sales",
                    "x_axis": "month",
                    "y_axis": "revenue"
                },
                "depends_on": ["query_result"]
            }
        ]
        
        context = await create_analysis_pipeline(
            task_id="pipeline_test",
            steps=steps
        )
        
        assert context.task_id == "pipeline_test"
        assert context.has_query_result()
```

### 2.2 MCP 服务器测试

```python
# tests/test_server.py
import pytest
from protocols.mcp.data_analytics.server import DataAnalyticsServer


class TestDataAnalyticsServer:
    """数据分析服务器测试"""
    
    def test_server_creation(self):
        """测试服务器创建"""
        server = DataAnalyticsServer(name="test-server")
        
        assert server.name == "test-server"
        info = server.get_info()
        assert info["name"] == "test-server"
        assert "tools" in info
        assert len(info["tools"]) >= 6
    
    def test_default_tools_registered(self):
        """测试默认工具注册"""
        server = DataAnalyticsServer()
        
        expected_tools = [
            "db_query",
            "init_sample_db",
            "visualize_data",
            "data_summary",
            "generate_report",
            "create_analysis_report"
        ]
        
        for tool in expected_tools:
            assert tool in server.get_info()["tools"]
    
    def test_custom_tool_registration(self):
        """测试自定义工具注册"""
        server = DataAnalyticsServer()
        
        def custom_tool(param: str) -> dict:
            return {"result": param}
        
        server.add_tool(custom_tool, name="custom_tool")
        
        assert "custom_tool" in server.get_info()["tools"]
```

## 三、端到端测试

### 3.1 完整分析流程测试

```python
# tests/test_e2e.py
import pytest
import asyncio


class TestEndToEndAnalysis:
    """端到端分析测试"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """测试完整分析工作流"""
        from protocols.mcp.data_analytics.server import DataAnalyticsServer
        from protocols.mcp.data_analytics.orchestrator import ToolOrchestrator
        from protocols.mcp.data_analytics.tools.database import init_sample_database
        
        # 1. 初始化数据
        init_sample_database()
        
        # 2. 创建编排器执行完整分析
        orchestrator = ToolOrchestrator(task_id="e2e_001")
        
        context = await orchestrator.full_analysis(
            sql="""
                SELECT 
                    month,
                    region,
                    SUM(revenue) as total_revenue,
                    SUM(quantity) as total_quantity
                FROM sales 
                GROUP BY month, region
                ORDER BY month, region
            """,
            chart_type="bar",
            report_title="Sales Analysis Report",
            x_axis="month",
            y_axis="total_revenue",
            report_format="markdown"
        )
        
        # 3. 验证结果
        assert context.has_query_result()
        assert context.has_visualization()
        assert context.has_report()
        
        # 4. 验证报表内容
        report = context.report_result
        assert "Sales Analysis Report" in report["content"]
        assert "Query Results" in report["content"]
        assert "Data Visualization" in report["content"]
        
        # 5. 验证可视化数据
        viz = context.visualization_result
        assert viz["chart_type"] == "bar"
        assert viz["y_axis"] == "total_revenue"
    
    @pytest.mark.asyncio
    async def test_multi_chart_analysis(self):
        """测试多图表分析"""
        from protocols.mcp.data_analytics.orchestrator import ToolOrchestrator
        from protocols.mcp.data_analytics.tools.database import init_sample_database
        from protocols.mcp.data_analytics.tools.visualization import visualize_data
        from protocols.mcp.data_analytics.tools.reporting import generate_report
        
        init_sample_database()
        
        orchestrator = ToolOrchestrator(task_id="multi_chart")
        
        # 查询不同维度数据
        region_data = await orchestrator.execute_step({
            "step_id": "region_query",
            "tool_name": "db_query",
            "parameters": {
                "sql": "SELECT region, SUM(revenue) as rev FROM sales GROUP BY region"
            }
        })
        
        product_data = await orchestrator.execute_step({
            "step_id": "product_query",
            "tool_name": "db_query",
            "parameters": {
                "sql": "SELECT product, SUM(revenue) as rev FROM sales GROUP BY product"
            }
        })
        
        # 生成多个图表
        region_chart = visualize_data(
            data=region_data["rows"],
            chart_type="pie",
            title="Revenue by Region",
            x_axis="region",
            y_axis="rev"
        )
        
        product_chart = visualize_data(
            data=product_data["rows"],
            chart_type="bar",
            title="Revenue by Product",
            x_axis="product",
            y_axis="rev"
        )
        
        # 生成综合报表
        report = generate_report(
            title="Comprehensive Sales Analysis",
            data=None,
            sections=[
                {"type": "chart", "title": "By Region", "data": region_chart},
                {"type": "chart", "title": "By Product", "data": product_chart}
            ],
            format="markdown"
        )
        
        assert report["success"] is True
        assert "By Region" in report["content"]
        assert "By Product" in report["content"]
```

### 3.2 错误处理测试

```python
# tests/test_error_handling.py
import pytest


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_sql_in_chain(self):
        """测试链式调用中的无效 SQL"""
        from protocols.mcp.data_analytics.orchestrator import ToolOrchestrator
        
        orchestrator = ToolOrchestrator(task_id="error_test")
        
        context = await orchestrator.query_and_visualize(
            sql="INVALID SQL",
            chart_type="bar",
            x_axis="x",
            y_axis="y"
        )
        
        # 查询应该失败
        assert not context.has_query_result()
        # 可视化不应执行
        assert not context.has_visualization()
    
    def test_visualization_with_invalid_data(self):
        """测试无效数据的可视化"""
        from protocols.mcp.data_analytics.tools.visualization import visualize_data
        
        # 空数据
        result = visualize_data(
            data=[],
            chart_type="bar",
            title="Empty",
            x_axis="x",
            y_axis="y"
        )
        assert result["success"] is False
        
        # 缺失字段
        result = visualize_data(
            data=[{"a": 1}],
            chart_type="bar",
            title="Missing",
            x_axis="nonexistent",
            y_axis="y"
        )
        assert result["success"] is False
    
    def test_report_with_invalid_format(self):
        """测试无效格式的报表"""
        from protocols.mcp.data_analytics.tools.reporting import generate_report
        
        result = generate_report(
            title="Test",
            data={},
            format="xml"  # 不支持的格式
        )
        assert result["success"] is False
```

## 四、性能测试

```python
# tests/test_performance.py
import pytest
import time


class TestPerformance:
    """性能测试"""
    
    def test_query_performance(self):
        """测试查询性能"""
        from protocols.mcp.data_analytics.tools.database import init_sample_database, query_database
        
        init_sample_database()
        
        # 创建大量测试数据
        insert_sql = " UNION ALL ".join([
            f"SELECT {i} as id, 'data_{i}' as value" for i in range(1000)
        ])
        query_database(f"WITH data AS (SELECT {insert_sql}) SELECT * FROM data")
        
        # 测试查询时间
        start = time.time()
        result = query_database("SELECT * FROM sales")
        elapsed = (time.time() - start) * 1000
        
        assert result["success"] is True
        assert elapsed < 1000, f"Query took {elapsed}ms, expected < 1000ms"
    
    def test_visualization_performance(self):
        """测试可视化性能"""
        from protocols.mcp.data_analytics.tools.visualization import visualize_data
        
        # 创建大量数据点
        data = [{"x": i, "y": i * 2} for i in range(10000)]
        
        start = time.time()
        result = visualize_data(
            data=data,
            chart_type="line",
            title="Performance Test",
            x_axis="x",
            y_axis="y",
            output_format="json"
        )
        elapsed = (time.time() - start) * 1000
        
        assert result["success"] is True
        assert elapsed < 2000, f"Visualization took {elapsed}ms, expected < 2000ms"
```

---

*测试用例版本: 1.0.0*  
*最后更新: 2026-04-16*
