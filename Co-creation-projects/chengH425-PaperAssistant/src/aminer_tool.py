"""
AMiner 中文学术检索工具

通过 AMiner API 检索中文学术论文，补充知网/万方无法免费接入的缺口。
AMiner 由清华大学开发，覆盖 3.2 亿+ 论文和 1.3 亿+ 学者。

注册地址: https://open.aminer.cn/
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import os
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class AminerSearchTool(Tool):
    """AMiner 中文学术检索工具

    通过 AMiner API 检索学术论文，特别擅长中文文献和中文作者。
    覆盖 3.2 亿+ 论文，是 Semantic Scholar 的中文补充。
    """

    SEARCH_URL = "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search"

    def __init__(self):
        super().__init__(
            name="aminer_search",
            description="通过 AMiner API 检索中英文学术论文。"
                        "覆盖 3.2 亿+ 论文，擅长中文文献和中文作者搜索。"
                        "当需要检索中文学术论文或中国学者的英文论文时使用此工具。"
                        "需要先注册获取 API Key: https://open.aminer.cn/"
        )

    def _get_api_key(self) -> str:
        """获取 AMiner API Key"""
        key = os.getenv("AMINER_API_KEY", "")
        if not key:
            raise RuntimeError(
                "未配置 AMiner API Key。请前往 https://open.aminer.cn/ 注册获取，"
                "然后在 .env 中设置: AMINER_API_KEY=你的key"
            )
        return key

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        keyword = parameters.get("keyword", "")
        author = parameters.get("author", "")
        max_results = min(parameters.get("max_results", 5), 20)

        if not keyword and not author:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="请至少提供关键词（keyword）或作者（author）"
            )

        # AMiner 用 title 参数做关键词搜索
        query = keyword or author
        params = {
            "title": query.strip(),
            "page": "1",
            "size": str(max_results)
        }

        url = f"{self.SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            api_key = self._get_api_key()
            req = urllib.request.Request(url, headers={
                "User-Agent": "PaperAssistant/1.0",
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            })

            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            code = data.get("code", -1)
            if code != 200 and code != 0:
                msg = data.get("msg", data.get("message", "未知错误"))
                return ToolResponse.error(
                    code="API_ERROR",
                    message=f"AMiner API 返回错误 (code={code}): {msg}"
                )

            papers = data.get("data", [])
            if isinstance(papers, dict):
                papers = papers.get("list", papers.get("results", []))

            total = data.get("total", len(papers))

            if not papers:
                return ToolResponse.success(
                    text=f"在 AMiner 中未找到匹配的论文（共 {total} 条结果）。",
                    data={"count": 0, "total": total, "papers": []}
                )

            # 格式化输出
            lines = [f"在 AMiner 中找到 {len(papers)} 篇论文（共 {total} 条结果）：\n"]
            for i, paper in enumerate(papers, 1):
                title = paper.get("title") or paper.get("name") or "N/A"
                paper_id = paper.get("id") or paper.get("paper_id") or ""
                doi = paper.get("doi") or ""
                year = paper.get("year") or paper.get("pub_year") or "N/A"

                # 作者
                authors_raw = paper.get("authors") or paper.get("author") or []
                if isinstance(authors_raw, list):
                    author_names = []
                    for a in authors_raw:
                        if isinstance(a, dict):
                            author_names.append(a.get("name", ""))
                        elif isinstance(a, str):
                            author_names.append(a)
                    authors_str = ", ".join(author_names[:5])
                    if len(authors_raw) > 5:
                        authors_str += " et al."
                elif isinstance(authors_raw, str):
                    authors_str = authors_raw
                else:
                    authors_str = "N/A"

                # 期刊/会议
                venue = paper.get("venue") or paper.get("journal") or ""
                if isinstance(venue, dict):
                    venue = venue.get("name", "") or venue.get("raw", "")

                # 引用次数
                citations = paper.get("n_citation") or paper.get("citation_count") or 0

                lines.append(f"### {i}. {title}")
                if authors_str and authors_str != "N/A":
                    lines.append(f"> 作者: {authors_str}")
                lines.append(f"> 发表: {year} | {venue or 'N/A'}")
                lines.append(f"> 引用: {citations} 次")
                if doi:
                    lines.append(f"> DOI: [{doi}](https://doi.org/{doi})")
                if paper_id:
                    lines.append(f"> AMiner ID: {paper_id}")
                lines.append("")

            return ToolResponse.success(
                text="\n".join(lines),
                data={
                    "count": len(papers),
                    "total": total,
                    "source": "AMiner",
                    "papers": [
                        {
                            "title": p.get("title", ""),
                            "authors": p.get("authors", []),
                            "year": p.get("year", ""),
                            "doi": p.get("doi", ""),
                            "venue": str(p.get("venue", "")),
                        }
                        for p in papers
                    ]
                }
            )

        except urllib.error.HTTPError as e:
            if e.code == 401:
                return ToolResponse.error(
                    code="ACCESS_DENIED",
                    message="AMiner API Key 无效或已过期。请检查 .env 中的 AMINER_API_KEY。"
                )
            return ToolResponse.error(
                code="NETWORK_ERROR",
                message=f"AMiner API 请求失败 (HTTP {e.code})"
            )
        except RuntimeError as e:
            return ToolResponse.error(code="ACCESS_DENIED", message=str(e))
        except Exception as e:
            return ToolResponse.error(
                code="INTERNAL_ERROR",
                message=f"AMiner 检索出错: {str(e)}"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="keyword", type="string",
                         description="搜索关键词，支持中文和英文",
                         required=False),
            ToolParameter(name="author", type="string",
                         description="作者姓名，支持中文名和英文名",
                         required=False),
            ToolParameter(name="max_results", type="integer",
                         description="最大返回结果数（默认5，最大20）",
                         required=False),
        ]
