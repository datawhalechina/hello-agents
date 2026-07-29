"""
学术引用生成工具

支持 GB/T 7714、APA 7th、MLA 9th 三种主流学术引用格式。
"""
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class CitationTool(Tool):
    """学术引用生成工具

    根据论文元数据生成指定格式的学术引用。
    """

    def __init__(self):
        super().__init__(
            name="citation_generator",
            description="根据论文信息生成指定格式的学术引用。"
                        "支持 GB/T 7714（中文期刊标准）、APA 第7版、MLA 第9版。"
                        "当需要生成参考文献引用时使用此工具。"
        )

    def _format_authors(self, authors_str: str, format_type: str) -> str:
        authors = [a.strip() for a in authors_str.split(",")]
        if format_type == "gbt7714":
            return ", ".join(authors)
        elif format_type == "apa":
            if len(authors) == 1:
                return authors[0]
            elif len(authors) == 2:
                return f"{authors[0]}, & {authors[1]}"
            else:
                return ", ".join(authors[:-1]) + f", & {authors[-1]}"
        elif format_type == "mla":
            if len(authors) == 1:
                return authors[0]
            elif len(authors) == 2:
                return f"{authors[0]}, and {authors[1]}"
            else:
                return f"{authors[0]}, et al"
        return authors_str

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        title = parameters.get("title", "")
        authors_str = parameters.get("authors", "")
        journal = parameters.get("journal", "")
        year = parameters.get("year", "")
        volume = parameters.get("volume", "")
        pages = parameters.get("pages", "")
        doi = parameters.get("doi", "")
        format_type = parameters.get("format", "gbt7714")

        if not title or not authors_str:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="标题和作者为必填项"
            )

        formatted_authors = self._format_authors(authors_str, format_type)

        if format_type == "gbt7714":
            citation = f"{formatted_authors}. {title}[J]. {journal}, {year}, {volume}: {pages}."
        elif format_type == "apa":
            citation = f"{formatted_authors} ({year}). {title}. {journal}, {volume}, {pages}."
            if doi:
                citation += f" https://doi.org/{doi}"
        elif format_type == "mla":
            citation = f'{formatted_authors}. "{title}." {journal}, vol. {volume}, {year}, pp. {pages}.'
        else:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message=f"不支持的引用格式: {format_type}，支持: gbt7714, apa, mla"
            )

        return ToolResponse.success(
            text=citation,
            data={"format": format_type, "citation": citation}
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="title", type="string",
                          description="论文标题", required=True),
            ToolParameter(name="authors", type="string",
                          description="作者列表，用逗号分隔",
                          required=True),
            ToolParameter(name="journal", type="string",
                          description="期刊/会议名称", required=False),
            ToolParameter(name="year", type="string",
                          description="发表年份", required=False),
            ToolParameter(name="volume", type="string",
                          description="卷号", required=False),
            ToolParameter(name="pages", type="string",
                          description="页码", required=False),
            ToolParameter(name="doi", type="string",
                          description="DOI 号", required=False),
            ToolParameter(name="format", type="string",
                          description="引用格式：gbt7714 / apa / mla",
                          required=False),
        ]
