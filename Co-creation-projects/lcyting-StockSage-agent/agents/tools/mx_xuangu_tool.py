"""
智能股票分析助手 — HelloAgents 智能选股工具封装

将东方财富 mx-xuangu Skill 封装为符合 HelloAgents 标准 Tool 接口的工具类。
Agent可通过此工具调用自然语言进行多条件智能选股。
"""

import sys
from pathlib import Path

# 将HelloAgents框架和skills路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_SKILLS_PATH = _PROJECT_ROOT / "skills" / "智能选股" / "mx-xuangu"

for p in [_HELLO_PATH, _SKILLS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import Tool, ToolParameter


class MXXuanguTool(Tool):
    """智能选股工具 — 封装东方财富妙想mx-xuangu Skill

    支持通过自然语言描述选股条件，自动筛选符合条件的A股/港股/美股。

    使用示例:
        tool = MXXuanguTool(api_key="your_mx_apikey")
        result = tool.run({"query": "市盈率小于20且ROE大于15%的A股"})
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="mx_xuangu",
            description=(
                "东方财富智能选股工具。支持通过自然语言描述选股条件，自动筛选"
                "符合条件的股票。选股维度包括：行情指标（价格、涨跌幅、成交量等）、"
                "财务指标（市盈率、ROE、净利润增长率、股息率等）、行业/板块筛选等。"
                "支持自然语言查询，如'市盈率小于20且ROE大于15%的A股'、"
                "'新能源板块涨幅大于1%的股票'、'股息率大于3%的银行股'。"
            ),
        )

        # 获取API密钥：优先参数 > 环境变量
        import os
        self.api_key = api_key or os.getenv("MX_APIKEY", "")

        # 延迟导入mx_xuangu模块
        self._mx_module = None

    def _get_mx_module(self):
        """延迟导入mx_xuangu模块（避免初始化时的导入错误）"""
        if self._mx_module is None:
            import mx_xuangu as _mx_xuangu
            self._mx_module = _mx_xuangu
        return self._mx_module

    def get_parameters(self) -> list:
        return [
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "自然语言选股条件。支持中文查询，例如：\n"
                    "- 行情条件: '今日涨幅大于2%的A股', '成交量大于10亿的股票'\n"
                    "- 财务条件: '市盈率小于20且市净率小于2', 'ROE大于15%的公司'\n"
                    "- 行业板块: '新能源板块市盈率小于30的股票', '白酒板块涨幅大于1%'\n"
                    "- 指数成分: '沪深300成分股中分红率最高的10只股票'\n"
                    "- 组合条件: '价格小于20元 市盈率小于20 涨幅大于1% A股'"
                ),
                required=True,
            ),
        ]

    def run(self, parameters: dict) -> str:
        """执行智能选股

        Args:
            parameters: {"query": "自然语言选股条件"}

        Returns:
            格式化的选股结果文本
        """
        query = parameters.get("query", "")
        if not query:
            return "错误：选股条件不能为空"

        if not self.api_key:
            return "错误：MX_APIKEY 未配置，无法执行选股。请设置环境变量 MX_APIKEY"

        try:
            mx = self._get_mx_module()

            # 创建MXSelectStock实例并查询
            screener = mx.MXSelectStock(api_key=self.api_key)
            result = screener.search(query)

            # 提取数据
            rows, data_source, error = mx.MXSelectStock.extract_data(result)

            if error:
                return f"选股出错: {error}"

            if not rows:
                return f"未找到符合条件'{query}'的股票，建议放宽筛选条件"

            # 格式化输出
            return self._format_result(rows, data_source, query)

        except Exception as e:
            return f"选股查询异常: {str(e)}"

    def _format_result(self, rows: list, data_source: str, query: str) -> str:
        """将选股结果格式化为可读文本"""
        lines = []

        lines.append(f"## 智能选股结果")
        lines.append(f"选股条件: {query}")
        lines.append(f"符合条件数量: {len(rows)} 只（数据来源: {data_source}）\n")

        if not rows:
            lines.append("(无符合条件的股票)")
            return "\n".join(lines)

        # 限制输出行数
        max_rows = 20
        display_rows = rows[:max_rows]

        # 表头（使用第一行的key）
        fieldnames = list(rows[0].keys())
        display_fields = fieldnames[:12]  # 最多显示12列

        header = " | ".join(display_fields)
        lines.append(f"| {header} |")
        lines.append(f"|{'|'.join(['---'] * len(display_fields))}|")

        # 数据行
        for row in display_rows:
            values = [str(row.get(col, "")).strip() for col in display_fields]
            lines.append(f"| {' | '.join(values)} |")

        if len(rows) > max_rows:
            lines.append(f"\n*(仅显示前{max_rows}只，共{len(rows)}只)*")

        return "\n".join(lines)
