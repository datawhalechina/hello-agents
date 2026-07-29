"""
arXiv API 检索工具

通过 arXiv 官方 API 检索学术论文，返回结构化结果。
文档: https://info.arxiv.org/help/api/
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class ArxivSearchTool(Tool):
    """arXiv 学术论文检索工具

    从 arXiv 数据库检索学术论文，支持关键词搜索、作者筛选、时间范围等条件。
    返回论文的标题、作者、摘要、发表日期和 PDF 链接。
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        super().__init__(
            name="arxiv_search",
            description="在 arXiv 学术论文数据库中搜索论文。"
                        "支持按关键词、作者、时间范围筛选。"
                        "返回论文标题、作者、摘要、发表日期和链接。"
                        "当需要查找最新的学术研究论文时使用此工具。"
        )

    def _build_query(self, parameters: Dict[str, Any]) -> str:
        """构建 arXiv API 查询字符串"""
        parts = []
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        category = parameters.get("category", "")

        if keyword:
            # 对关键词进行 URL 编码并构建查询
            terms = [f"all:{t.strip()}" for t in keyword.split() if t.strip()]
            parts.append("+AND+".join(terms))

        if author:
            parts.append(f'au:{author.replace(" ", "+")}')

        if category:
            # arXiv 分类如 cs.AI, cs.CL, stat.ML
            parts.append(f"cat:{category.strip()}")

        if not parts:
            parts.append("all:machine+learning")  # 默认查询

        return "+AND+".join(parts)

    def _parse_atom_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """解析 arXiv API 返回的 Atom XML"""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom"
        }

        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", ns)

        papers = []
        for entry in entries:
            title = entry.find("atom:title", ns)
            authors = entry.findall("atom:author", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            link = None
            for l in entry.findall("atom:link", ns):
                if l.get("title") == "pdf" or l.get("type") == "application/pdf":
                    link = l.get("href")
                    break
            if not link:
                # 用 id 构造 arXiv 页面链接
                paper_id = entry.find("atom:id", ns)
                if paper_id is not None and paper_id.text:
                    arxiv_id = paper_id.text.split("/abs/")[-1]
                    link = f"https://arxiv.org/pdf/{arxiv_id}"

            paper = {
                "title": title.text.strip().replace("\n", " ") if title is not None and title.text else "N/A",
                "authors": [a.find("atom:name", ns).text
                           for a in authors if a.find("atom:name", ns) is not None],
                "summary": summary.text.strip().replace("\n", " ")[:500]
                          if summary is not None and summary.text else "N/A",
                "published": published.text[:10] if published is not None and published.text else "N/A",
                "pdf_url": link or "N/A"
            }
            papers.append(paper)

        return papers

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        max_results = min(parameters.get("max_results", 5), 20)

        if not keyword and not author:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="请至少提供关键词（keyword）或作者（author）"
            )

        query = self._build_query(parameters)
        url = f"{self.BASE_URL}?search_query={query}&max_results={max_results}&sortBy=relevance"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read().decode("utf-8")

            papers = self._parse_atom_response(xml_data)

            if not papers:
                return ToolResponse.success(
                    text="未找到匹配的论文，请尝试调整关键词。",
                    data={"count": 0, "papers": []}
                )

            # 格式化输出
            lines = [f"找到 {len(papers)} 篇论文：\n"]
            for i, p in enumerate(papers, 1):
                authors_str = ", ".join(p["authors"][:3])
                if len(p["authors"]) > 3:
                    authors_str += " et al."
                lines.append(f"### {i}. {p['title']}")
                lines.append(f"   作者: {authors_str}")
                lines.append(f"   发表: {p['published']}")
                lines.append(f"   摘要: {p['summary'][:300]}...")
                lines.append(f"   PDF: {p['pdf_url']}")
                lines.append("")

            return ToolResponse.success(
                text="\n".join(lines),
                data={"count": len(papers), "papers": papers, "query": query}
            )

        except urllib.error.URLError as e:
            return ToolResponse.error(
                code="NETWORK_ERROR",
                message=f"arXiv API 请求失败: {str(e)}"
            )
        except ET.ParseError as e:
            return ToolResponse.error(
                code="INVALID_FORMAT",
                message=f"解析 arXiv 返回数据失败: {str(e)}"
            )
        except Exception as e:
            return ToolResponse.error(
                code="INTERNAL_ERROR",
                message=f"检索过程出错: {str(e)}"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="keyword", type="string",
                description="搜索关键词，如 'large language model reasoning'",
                required=False
            ),
            ToolParameter(
                name="author", type="string",
                description="作者姓名，如 'Geoffrey Hinton'",
                required=False
            ),
            ToolParameter(
                name="category", type="string",
                description="arXiv 分类，如 cs.AI(人工智能) / cs.CL(计算语言学) / stat.ML(机器学习)",
                required=False
            ),
            ToolParameter(
                name="max_results", type="integer",
                description="最大返回结果数（默认5，最多20）",
                required=False
            ),
        ]
