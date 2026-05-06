"""
智能股票分析助手 — HelloAgents 金融数据工具封装

将东方财富 mx-data Skill 封装为符合 HelloAgents 标准 Tool 接口的工具类。
Agent可通过此工具调用自然语言查询获取行情、财务、关联关系等数据。
"""

import sys
from pathlib import Path

# 将HelloAgents框架和skills路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_SKILLS_PATH = _PROJECT_ROOT / "skills" / "金融数据" / "mx-data"

for p in [_HELLO_PATH, _SKILLS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import Tool, ToolParameter


class MXDataTool(Tool):
    """金融数据查询工具 — 封装东方财富妙想mx-data Skill

    支持通过自然语言查询A股行情、财务指标、公司概况、股东信息等金融数据。

    使用示例:
        tool = MXDataTool(api_key="your_mx_apikey")
        result = tool.run({"query": "贵州茅台最新价 涨跌幅"})
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="mx_data",
            description=(
                "东方财富金融数据查询工具。支持查询A股股票的实时行情、历史行情、"
                "财务指标（净利润、ROE、毛利率等）、公司概况（主营业务、高管信息）、"
                "股东信息（十大股东）、指数行情、板块行情等。"
                "支持自然语言查询，如'贵州茅台近三年净利润 营业收入'、"
                "'沪深300指数最新点位'、'比亚迪公司简介 主营业务'。"
            ),
        )

        # 获取API密钥：优先参数 > 环境变量
        import os
        self.api_key = api_key or os.getenv("MX_APIKEY", "")

        # 延迟导入mx_data模块
        self._mx_module = None

    def _get_mx_module(self):
        """延迟导入mx_data模块（避免初始化时的导入错误）"""
        if self._mx_module is None:
            import mx_data as _mx_data
            self._mx_module = _mx_data
        return self._mx_module

    def get_parameters(self) -> list:
        return [
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "自然语言查询语句。支持中文查询，例如：\n"
                    "- 行情: '贵州茅台最新价 涨跌幅', '比亚迪近一年每个交易日收盘价'\n"
                    "- 财务: '贵州茅台近三年净利润 营业收入 净资产收益率'\n"
                    "- 公司: '比亚迪公司简介 主营业务 董事长是谁'\n"
                    "- 股东: '贵州茅台十大股东'\n"
                    "- 指数: '沪深300指数最新点位'"
                ),
                required=True,
            ),
        ]

    def run(self, parameters: dict) -> str:
        """执行金融数据查询

        Args:
            parameters: {"query": "自然语言查询"}

        Returns:
            格式化的查询结果文本
        """
        query = parameters.get("query", "")
        if not query:
            return "错误：查询内容不能为空"

        if not self.api_key:
            return "错误：MX_APIKEY 未配置，无法查询金融数据。请设置环境变量 MX_APIKEY"

        try:
            mx = self._get_mx_module()

            # 创建MXData实例并查询
            data_querier = mx.MXData(api_key=self.api_key)
            result = data_querier.query(query)

            # 解析结果
            tables, condition_parts, total_rows, error = mx.MXData.parse_result(result)

            if error:
                return f"查询出错: {error}"

            if not tables:
                return "查询未返回任何数据"

            # 格式化输出
            return self._format_result(tables, condition_parts, total_rows)

        except Exception as e:
            return f"金融数据查询异常: {str(e)}"

    def _format_result(self, tables: list, condition_parts: list, total_rows: int) -> str:
        """将查询结果格式化为可读文本"""
        lines = []

        # 查询条件
        if condition_parts:
            lines.append("## 查询条件")
            for part in condition_parts:
                lines.append(part)
            lines.append("")

        # 数据表格
        lines.append(f"## 查询结果（{len(tables)}个表，共{total_rows}行数据）\n")

        for idx, table in enumerate(tables):
            sheet_name = table.get("sheet_name", f"表{idx+1}")
            rows = table.get("rows", [])
            fieldnames = table.get("fieldnames", [])

            lines.append(f"### {sheet_name}")

            if not rows:
                lines.append("(无数据)")
                continue

            # 限制输出行数（避免上下文过长）
            max_rows = 30
            display_rows = rows[:max_rows]

            # 表头
            header = " | ".join(fieldnames[:10])  # 最多显示10列
            lines.append(f"| {header} |")
            lines.append(f"|{'|'.join(['---'] * min(len(fieldnames), 10))}|")

            # 数据行
            for row in display_rows:
                values = [str(row.get(col, "")) for col in fieldnames[:10]]
                lines.append(f"| {' | '.join(values)} |")

            if len(rows) > max_rows:
                lines.append(f"\n*(仅显示前{max_rows}行，共{len(rows)}行)*")

            lines.append("")

        return "\n".join(lines)
