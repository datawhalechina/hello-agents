"""
CrossRef 期刊论文检索工具

通过 CrossRef REST API 检索已发表的学术期刊论文。
CrossRef 是学术出版物的 DOI 注册机构，覆盖 1.5 亿+ 记录。

API 文档: https://api.crossref.org/
"""
import urllib.request
import urllib.parse
import urllib.error
import json
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class CrossRefSearchTool(Tool):
    """CrossRef 期刊论文检索工具

    通过 CrossRef REST API 检索正式发表的期刊论文、会议论文、书籍等。
    覆盖 1.5 亿+ 学术作品，拥有最完整的期刊论文元数据（DOI、ISSN、页码等）。
    特别适合检索正式发表的期刊论文和获取引用元数据。
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self):
        super().__init__(
            name="crossref_search",
            description="通过 CrossRef API 检索正式发表的期刊论文和会议论文。"
                        "覆盖 1.5 亿+ 记录，拥有最完整的引用元数据（DOI、期刊名、"
                        "卷号、页码等）。特别适合按 DOI 查找论文或检索特定期刊的文献。"
                        "当需要精确的引用信息时使用此工具。"
        )

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        doi = parameters.get("doi", "")
        journal = parameters.get("journal", "")
        max_results = min(parameters.get("max_results", 5), 20)
        year_from = parameters.get("year_from", "")
        year_to = parameters.get("year_to", "")

        # DOI 精确查询（最高效）
        if doi:
            url = f"{self.BASE_URL}/{urllib.parse.quote(doi.strip(), safe='')}"
        else:
            if not keyword and not author and not journal:
                return ToolResponse.error(
                    code="INVALID_PARAM",
                    message="请提供关键词(keyword)、作者(author)、DOI(doi)或期刊名(journal)"
                )

            # 构建过滤条件
            filters = []
            if year_from or year_to:
                f = f"from-pub-date:{year_from or '1900'}"
                if year_to:
                    f += f",until-pub-date:{year_to}"
                filters.append(f)

            # 查询字段
            query_parts = []
            if keyword:
                query_parts.append(keyword.strip())
            if author:
                query_parts.append(author.strip())
            if journal:
                query_parts.append(journal.strip())

            params = {
                "query": " ".join(query_parts),
                "rows": str(max_results),
            }
            if filters:
                params["filter"] = ",".join(filters)

            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "PaperAssistant/1.0 (mailto:1793636425@qq.com)",
                    "Accept": "application/json"
                }
            )

            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # 解析结果
            if doi:
                # 单篇论文查询
                msg = data.get("message", {})
                items = [msg] if msg else []
                total = len(items)
            else:
                msg = data.get("message", {})
                items = msg.get("items", [])
                total = msg.get("total-results", 0)

            if not items:
                return ToolResponse.success(
                    text=f"在 CrossRef 中未找到匹配的论文。"
                         f"{' DOI 可能不正确。' if doi else ' 请尝试更换关键词。'}",
                    data={"count": 0, "papers": []}
                )

            # 格式化输出
            lines = [f"找到 {total} 篇论文（显示前 {len(items)} 篇）：\n"]
            for i, item in enumerate(items, 1):
                title_list = item.get("title", ["N/A"])
                title = title_list[0] if title_list else "N/A"

                # 作者
                authors = item.get("author", [])
                author_names = []
                for a in authors[:5]:
                    given = a.get("given", "")
                    family = a.get("family", "")
                    if given or family:
                        author_names.append(f"{family} {given}".strip())
                authors_str = ", ".join(author_names)
                if len(authors) > 5:
                    authors_str += " et al."

                # 发表信息
                published = item.get("published-print", {}) or item.get("published-online", {})
                pub_date = "-".join(str(v) for v in published.get("date-parts", [["?"]])[0]) if published else "N/A"

                # 期刊
                container = item.get("container-title", [])
                venue = container[0] if container else item.get("publisher", "N/A")

                # 引用次数
                ref_count = item.get("is-referenced-by-count", 0)

                item_doi = item.get("DOI", "")

                lines.append(f"### {i}. {title}")
                if authors_str:
                    lines.append(f"> 作者: {authors_str}")
                lines.append(f"> 发表: {pub_date} | {venue}")
                lines.append(f"> 引用: {ref_count} 次")
                if item_doi:
                    lines.append(f"> DOI: [{item_doi}](https://doi.org/{item_doi})")
                lines.append("")

            lines.append(f"---")
            lines.append(f"*数据来源: CrossRef API*")

            return ToolResponse.success(
                text="\n".join(lines),
                data={"count": len(items), "total": total, "papers": items}
            )

        except urllib.error.HTTPError as e:
            return ToolResponse.error(
                code="NETWORK_ERROR",
                message=f"CrossRef API 请求失败 (HTTP {e.code})"
            )
        except json.JSONDecodeError:
            return ToolResponse.error(
                code="INVALID_FORMAT",
                message="解析 CrossRef 返回数据失败"
            )
        except Exception as e:
            return ToolResponse.error(
                code="INTERNAL_ERROR",
                message=f"CrossRef 检索出错: {str(e)}"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="keyword", type="string",
                         description="搜索关键词", required=False),
            ToolParameter(name="author", type="string",
                         description="作者姓名", required=False),
            ToolParameter(name="doi", type="string",
                         description="DOI 号码（精确查询，优先级最高）", required=False),
            ToolParameter(name="journal", type="string",
                         description="期刊名称", required=False),
            ToolParameter(name="year_from", type="string",
                         description="起始年份", required=False),
            ToolParameter(name="year_to", type="string",
                         description="截止年份", required=False),
            ToolParameter(name="max_results", type="integer",
                         description="最大返回结果数（默认5，最大20）", required=False),
        ]
