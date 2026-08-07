"""
文献检索工具 — Semantic Scholar API

覆盖 2 亿+ 学术论文，涵盖计算机科学、医学、生物学、物理学、化学、
社会科学、经济学、人文艺术等全学科领域。

API 文档: https://api.semanticscholar.org/api-docs/
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import time
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class LiteratureSearchTool(Tool):
    """全学科文献检索工具

    通过 Semantic Scholar API 在多学科数据库中检索学术论文。
    覆盖 2 亿+ 论文，支持关键词、作者、年份、学科领域等筛选条件。
    返回论文标题、作者、摘要、发表信息、引用次数、PDF 链接等。
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    # 请求的论文字段
    FIELDS = [
        "title", "abstract", "authors", "year", "venue",
        "externalIds", "citationCount", "influentialCitationCount",
        "openAccessPdf", "journal", "publicationTypes", "fieldsOfStudy"
    ]

    # 中文学科关键词映射
    FIELD_ALIASES = {
        "计算机科学": "Computer Science",
        "人工智能": "Artificial Intelligence",
        "机器学习": "Machine Learning",
        "医学": "Medicine",
        "生物学": "Biology",
        "物理学": "Physics",
        "化学": "Chemistry",
        "数学": "Mathematics",
        "经济学": "Economics",
        "心理学": "Psychology",
        "社会学": "Sociology",
        "语言学": "Linguistics",
        "哲学": "Philosophy",
        "历史": "History",
        "工程": "Engineering",
        "环境科学": "Environmental Science",
        "材料科学": "Materials Science",
        "教育学": "Education",
        "法学": "Law",
        "政治学": "Political Science",
        "商学": "Business",
        "艺术": "Art",
        "地理": "Geography",
        "地质": "Geology",
    }

    def __init__(self):
        super().__init__(
            name="literature_search",
            description="通过 Semantic Scholar 在全学科数据库中检索学术论文。"
                        "覆盖 2 亿+ 论文，涵盖计算机科学、医学、生物、物理、化学、"
                        "社会科学、经济学、人文等所有学术领域。"
                        "支持按关键词、作者、年份范围、学科领域筛选。"
                        "返回论文标题、作者、摘要、期刊、引用次数、PDF 链接等信息。"
                        "当需要跨学科检索学术文献时使用此工具，比 arXiv 覆盖面更广。"
        )

    def _map_field(self, field_input: str) -> str:
        """将中文/模糊学科名映射到 Semantic Scholar 领域"""
        if not field_input:
            return ""
        field_input = field_input.strip()
        # 直接匹配
        for cn, en in self.FIELD_ALIASES.items():
            if cn in field_input or field_input.lower() in cn.lower():
                return en
        # 已经是英文则直接返回
        return field_input

    def _build_url(self, parameters: Dict[str, Any]) -> str:
        """构建 Semantic Scholar 搜索 URL"""
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        field = parameters.get("field", "")
        year_from = parameters.get("year_from", "")
        year_to = parameters.get("year_to", "")
        limit = min(parameters.get("max_results", 5), 20)

        # 构建查询字符串
        query_parts = []
        if keyword:
            query_parts.append(keyword.strip())
        if author:
            query_parts.append(f'author:"{author.strip()}"')

        query = " ".join(query_parts) if query_parts else "machine learning"

        params = {
            "query": query,
            "limit": str(limit),
            "fields": ",".join(self.FIELDS)
        }

        # 学科筛选
        mapped_field = self._map_field(field) if field else ""
        if mapped_field:
            params["fieldsOfStudy"] = mapped_field

        # 年份筛选
        if year_from or year_to:
            year_filter = f"{year_from or '1900'}-{year_to or '2026'}"
            params["year"] = year_filter

        return f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

    def _format_paper(self, paper: Dict, index: int, keyword: str = "") -> str:
        """格式化单篇论文为 Markdown"""
        title = paper.get("title", "N/A")
        year = paper.get("year", "N/A")
        venue = paper.get("venue", "")
        journal = paper.get("journal", {})
        journal_name = journal.get("name", "") if journal else ""
        publication_venue = venue or journal_name or "N/A"

        # 作者列表
        authors_list = paper.get("authors", [])
        author_names = [a.get("name", "") for a in authors_list[:5]]
        authors_str = ", ".join(author_names)
        if len(authors_list) > 5:
            authors_str += " et al."

        # 摘要：优先取 TLDR，其次取 abstract
        abstract = paper.get("abstract") or "暂无摘要"
        if len(abstract) > 400:
            abstract = abstract[:400] + "..."

        # 引用次数
        citations = paper.get("citationCount", 0)

        # DOI
        external_ids = paper.get("externalIds", {}) or {}
        doi = external_ids.get("DOI", "")

        # PDF 链接
        open_access = paper.get("openAccessPdf", {}) or {}
        pdf_url = open_access.get("url", "")
        arxiv_id = external_ids.get("ArXiv", "")

        # 领域标签
        fields = paper.get("fieldsOfStudy", []) or []
        fields_str = ", ".join(fields[:3]) if fields else ""

        lines = [f"### {index}. {title}"]
        if authors_str:
            lines.append(f"> 作者: {authors_str}")
        lines.append(f"> 发表: {year} | {publication_venue}")
        if fields_str:
            lines.append(f"> 领域: {fields_str}")
        lines.append(f"> 引用: {citations} 次")

        # 链接
        links = []
        if doi:
            links.append(f"[DOI](https://doi.org/{doi})")
        if pdf_url:
            links.append(f"[PDF]({pdf_url})")
        if arxiv_id:
            links.append(f"[arXiv](https://arxiv.org/abs/{arxiv_id})")
        if links:
            lines.append(f"> {' | '.join(links)}")

        lines.append(f">> {abstract}")
        lines.append("")
        return "\n".join(lines)

    def _make_request(self, url: str, api_key: str, max_retries: int = 3) -> Dict:
        """发送 API 请求，带指数退避重试"""
        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "PaperAssistant/1.0",
                        "Accept": "application/json"
                    }
                )
                if api_key:
                    req.add_header("x-api-key", api_key)

                with urllib.request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # 速率限制：等待后重试
                    wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    raise RuntimeError(
                        "API 请求频率已达上限（429 Too Many Requests）。\n"
                        "Semantic Scholar 免费额度为 100 次/5 分钟。\n"
                        "请稍等 1-5 分钟后重试，或申请免费 API Key：\n"
                        "https://www.semanticscholar.org/product/api\n"
                        "获取后在 .env 中设置 SEMANTIC_SCHOLAR_API_KEY"
                    ) from e
                raise RuntimeError(
                    f"Semantic Scholar API 返回 HTTP {e.code}: {e.reason}"
                ) from e
            except urllib.error.URLError as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise RuntimeError(f"网络连接失败: {str(e.reason)}") from e

        raise RuntimeError(f"请求失败（已重试 {max_retries} 次）: {last_error}")

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        field = parameters.get("field", "")

        if not keyword and not author:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="请至少提供关键词（keyword）或作者（author）"
            )

        url = self._build_url(parameters)
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

        try:
            data = self._make_request(url, api_key)

            papers = data.get("data", [])
            total = data.get("total", 0)
            offset = data.get("offset", 0)

            if not papers:
                # 尝试推荐相似的搜索词
                suggestion = ""
                if keyword:
                    suggestion = f"\n\n建议：尝试更简短的关键词，或更换同义词。如将 '{keyword}' 改为更通用的表述。"
                return ToolResponse.success(
                    text=f"未找到匹配的论文（共 {total} 条结果）。{suggestion}",
                    data={"count": 0, "total": total, "papers": []}
                )

            # 格式化输出
            lines = [f"找到 {total} 篇论文（显示前 {len(papers)} 篇，偏移 {offset}）：\n"]
            for i, paper in enumerate(papers, 1):
                lines.append(self._format_paper(paper, i, keyword))

            lines.append(f"---")
            lines.append(f"*本次检索共 {total} 篇结果。如需更多，请调整关键词或筛选条件。*")
            if total > len(papers):
                lines.append(f"*提示：可通过增加 max_results 获取更多结果（最大 20）。*")

            return ToolResponse.success(
                text="\n".join(lines),
                data={
                    "count": len(papers),
                    "total": total,
                    "offset": offset,
                    "papers": [
                        {
                            "title": p.get("title"),
                            "authors": [a.get("name") for a in p.get("authors", [])],
                            "year": p.get("year"),
                            "venue": p.get("venue", ""),
                            "citationCount": p.get("citationCount", 0),
                            "abstract": (p.get("abstract") or "")[:300],
                            "doi": (p.get("externalIds") or {}).get("DOI", ""),
                            "fieldsOfStudy": p.get("fieldsOfStudy", [])
                        }
                        for p in papers
                    ]
                }
            )

        except RuntimeError as e:
            # _make_request 中已含重试逻辑，此处为最终失败
            return ToolResponse.error(
                code="API_ERROR",
                message=f"[检索失败] {str(e)}\n\n"
                        "请等待 1-2 分钟后重试。在此期间可使用其他数据源（OpenAlex、CrossRef、PubMed）。"
            )
        except json.JSONDecodeError:
            return ToolResponse.error(
                code="INVALID_FORMAT",
                message="解析 API 返回数据失败，请稍后重试。"
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
                description="搜索关键词，支持中英文。如 'transformer attention mechanism' 或 '深度学习 图像分割'",
                required=False
            ),
            ToolParameter(
                name="author", type="string",
                description="作者姓名，如 'Geoffrey Hinton' 或 '何恺明'",
                required=False
            ),
            ToolParameter(
                name="field", type="string",
                description="学科领域，支持中英文。如 '计算机科学'/'Computer Science'、'医学'/'Medicine'、'物理学'/'Physics'",
                required=False
            ),
            ToolParameter(
                name="year_from", type="string",
                description="起始年份，如 '2020'",
                required=False
            ),
            ToolParameter(
                name="year_to", type="string",
                description="截止年份，如 '2026'",
                required=False
            ),
            ToolParameter(
                name="max_results", type="integer",
                description="最大返回结果数（默认5，最大20）",
                required=False
            ),
        ]
