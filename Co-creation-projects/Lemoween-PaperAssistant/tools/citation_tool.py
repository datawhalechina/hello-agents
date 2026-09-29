"""引用格式化工具（返回 str）"""
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter


class CitationTool(Tool):
    """引用格式化工具（GB/T 7714-2015 与 APA 7th）"""

    def __init__(self):
        super().__init__(
            name="format_citation",
            description="将论文元数据格式化为标准引用格式（gb7714 或 apa）。",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="title", type="string",
                          description="论文标题", required=True),
            ToolParameter(name="authors", type="string",
                          description="作者列表，逗号分隔", required=True),
            ToolParameter(name="year", type="string",
                          description="年份", required=True),
            ToolParameter(name="venue", type="string",
                          description="期刊/会议名", required=False),
            ToolParameter(name="volume", type="string",
                          description="卷号", required=False),
            ToolParameter(name="issue", type="string",
                          description="期号", required=False),
            ToolParameter(name="pages", type="string",
                          description="页码", required=False),
            ToolParameter(name="doi", type="string",
                          description="DOI", required=False),
            ToolParameter(name="style", type="string",
                          description="gb7714 或 apa", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        title = parameters.get("title", "")
        authors_raw = parameters.get("authors", "")
        year = parameters.get("year", "")
        venue = parameters.get("venue", "")
        volume = parameters.get("volume", "")
        issue = parameters.get("issue", "")
        pages = parameters.get("pages", "")
        doi = parameters.get("doi", "")
        style = parameters.get("style", "gb7714")

        if not title or not authors_raw:
            return "❌ title 与 authors 为必填字段"

        author_list = [a.strip() for a in authors_raw.split(",") if a.strip()]
        authors_str = ", ".join(author_list)

        if style == "gb7714":
            parts = [f"{authors_str}. {title}[J]."]
            if venue:
                parts.append(venue)
            if year:
                parts.append(f", {year}")
            if volume:
                parts.append(f", {volume}")
            if issue:
                parts.append(f"({issue})")
            if pages:
                parts.append(f": {pages}")
            citation = "".join(parts) + "."
            if doi:
                citation += f" DOI: {doi}."
        elif style == "apa":
            citation = f"{authors_str} ({year}). {title}."
            if venue:
                citation += f" {venue}"
            if volume:
                citation += f", {volume}"
            if issue:
                citation += f"({issue})"
            if pages:
                citation += f", {pages}"
            citation += "."
            if doi:
                citation += f" https://doi.org/{doi}"
        else:
            citation = f"{authors_str}. {title}. {venue}, {year}."

        return citation