"""
智能股票分析助手 — HelloAgents 资讯搜索工具封装

将东方财富 mx-search Skill 封装为符合 HelloAgents 标准 Tool 接口的工具类。
Agent可通过此工具调用自然语言搜索金融资讯（新闻、研报、公告）。
"""

import sys
from pathlib import Path

# 将HelloAgents框架和skills路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_SKILLS_PATH = _PROJECT_ROOT / "skills" / "资讯搜索" / "mx-search"

for p in [_PROJECT_ROOT, _HELLO_PATH, _SKILLS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import Tool, ToolParameter

from ..text_truncation import truncate_at_natural_boundary

# 单条资讯正文展示上限（字符）；放宽可减少摘要中途截断
MX_SEARCH_CONTENT_MAX_CHARS = 2500


class MXSearchTool(Tool):
    """金融资讯搜索工具 — 封装东方财富妙想mx-search Skill

    支持通过自然语言搜索金融资讯，包括：
    - 个股相关：研报、公告、机构观点
    - 行业/板块：产业新闻、政策解读
    - 宏观/市场：经济分析、资金流向
    - 事件/规则：分红公告、交易规则等

    使用示例:
        tool = MXSearchTool(api_key="your_mx_apikey")
        result = tool.run({"query": "贵州茅台最新研报"})
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="mx_search",
            description=(
                "东方财富金融资讯搜索工具。支持搜索A股相关的新闻、研报、公告、"
                "政策解读、行业分析等金融资讯。适用于获取时效性信息和特定事件信息。"
                "支持自然语言查询，如'贵州茅台最新研报'、'人工智能板块近期新闻'、"
                "'美联储加息对A股影响分析'、'新能源汽车产业政策最新解读'。"
            ),
        )

        # 获取API密钥：优先参数 > 环境变量
        import os
        self.api_key = api_key or os.getenv("MX_APIKEY", "")

        # 延迟导入mx_search模块
        self._mx_module = None

    def _get_mx_module(self):
        """延迟导入mx_search模块（避免初始化时的导入错误）"""
        if self._mx_module is None:
            import mx_search as _mx_search
            self._mx_module = _mx_search
        return self._mx_module

    def get_parameters(self) -> list:
        return [
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "自然语言查询语句。支持中文查询，例如：\n"
                    "- 个股资讯: '贵州茅台最新研报', '比亚迪机构观点汇总'\n"
                    "- 行业新闻: '人工智能板块近期新闻', '新能源汽车产业政策'\n"
                    "- 宏观分析: '美联储加息对A股影响分析', '北向资金最新流向'\n"
                    "- 事件公告: '贵州茅台分红派息实施公告', '宁德时代定增预案'\n"
                    "- 交易规则: '科创板涨跌幅限制', '新股申购规则'"
                ),
                required=True,
            ),
        ]

    def run(self, parameters: dict) -> str:
        """执行金融资讯搜索

        Args:
            parameters: {"query": "自然语言查询"}

        Returns:
            格式化的搜索结果文本
        """
        query = parameters.get("query", "")
        if not query:
            return "错误：查询内容不能为空"

        if not self.api_key:
            return "错误：MX_APIKEY 未配置，无法搜索资讯。请设置环境变量 MX_APIKEY"

        try:
            mx = self._get_mx_module()

            # 创建MXSearch实例并查询
            search_client = mx.MXSearch(api_key=self.api_key)
            result = search_client.search(query)

            # 格式化输出为可读文本
            return self._format_result(result, query)

        except Exception as e:
            return f"资讯搜索异常: {str(e)}"

    def _format_result(self, result: dict, query: str) -> str:
        """将搜索结果格式化为可读文本"""
        lines = []

        # 检查API状态
        status = result.get("status")
        message = result.get("message", "")
        if status != 0:
            lines.append(f"## 资讯搜索结果")
            lines.append(f"查询: {query}")
            lines.append(f"错误: 状态码 {status} - {message}")
            return "\n".join(lines)

        # 解析搜索结果
        data = result.get("data", {})
        inner_data = data.get("data", {})
        search_response = inner_data.get("llmSearchResponse", {})
        items = search_response.get("data", [])

        if not items:
            return f"未找到与'{query}'相关的最新金融资讯"

        # 类型映射
        type_map = {
            "REPORT": "研报",
            "NEWS": "新闻",
            "ANNOUNCEMENT": "公告"
        }

        # 限制输出条数
        max_items = 15
        display_items = items[:max_items]

        lines.append(f"## 资讯搜索结果")
        lines.append(f"查询: {query}")
        lines.append(f"共找到 {len(items)} 条相关资讯\n")

        for i, item in enumerate(display_items):
            title = item.get("title", "无标题")
            content = item.get("content", "")
            date = item.get("date", "")
            ins_name = item.get("insName", "")
            info_type = item.get("informationType", "")
            rating = item.get("rating", "")
            entity_name = item.get("entityFullName", "")

            type_cn = type_map.get(info_type, info_type or "资讯")

            lines.append(f"### {i+1}. {title}")

            meta_parts = []
            if entity_name:
                meta_parts.append(f"证券: {entity_name}")
            if ins_name:
                meta_parts.append(f"机构: {ins_name}")
            if date:
                meta_parts.append(f"日期: {date.split()[0]}")
            lines.append(f"类型: {type_cn} | {' | '.join(meta_parts)}")

            if rating:
                lines.append(f"评级: {rating}")

            if content:
                # 截断过长内容（优先段落/句号）
                if len(content) > MX_SEARCH_CONTENT_MAX_CHARS:
                    content = truncate_at_natural_boundary(
                        content, MX_SEARCH_CONTENT_MAX_CHARS, "..."
                    )
                lines.append("")
                lines.append(content)

            lines.append("")

        if len(items) > max_items:
            lines.append(f"*(仅显示前{max_items}条，共{len(items)}条)*")

        return "\n".join(lines)
