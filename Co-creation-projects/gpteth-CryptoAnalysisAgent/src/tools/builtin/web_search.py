"""Web search via DuckDuckGo, with optional Brave Search."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text


class WebSearchTool(Tool):
    def __init__(self, max_results: int = 5, timeout: int = 12):
        super().__init__(
            name="web_search",
            description="搜索互联网公开信息。适合查新闻、公告、项目资料。返回标题、链接和摘要。",
        )
        self.max_results = max_results
        self.timeout = timeout
        self.brave_key = os.getenv("BRAVE_API_KEY")

    def run(self, parameters: Dict[str, Any]) -> str:
        query = first_text(parameters, "query")
        if not query:
            return "错误: 请提供 query"
        try:
            count = int(parameters.get("count") or self.max_results)
        except (TypeError, ValueError):
            count = self.max_results
        count = max(1, min(count, 8))
        if self.brave_key:
            try:
                return self._brave(query, count)
            except Exception:
                pass
        try:
            return self._duckduckgo(query, count)
        except Exception as exc:
            return f"搜索失败: {exc}"

    def _brave(self, query: str, count: int) -> str:
        url = "https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": query, "count": count})
        req = Request(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_key,
        })
        with urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        results = payload.get("web", {}).get("results") or []
        if not results:
            return f"未找到与「{query}」相关的结果"
        lines = [f"## 搜索: {query}\n"]
        for item in results[:count]:
            lines.append(f"- **{item.get('title', '')}**\n  {item.get('url', '')}\n  {item.get('description', '')}")
        return "\n".join(lines)

    def _duckduckgo(self, query: str, count: int) -> str:
        instant = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        req = Request(instant, headers={"User-Agent": "CryptoAnalysisAgent/1.0"})
        with urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        lines = [f"## 搜索: {query}\n"]
        abstract = data.get("AbstractText") or data.get("Abstract")
        if abstract:
            source = data.get("AbstractURL") or ""
            lines.append(f"{abstract}\n{source}\n")
        related = data.get("RelatedTopics") or []
        added = 0
        for item in related:
            if added >= count:
                break
            if isinstance(item, dict) and item.get("Text"):
                lines.append(f"- {item.get('Text')}\n  {item.get('FirstURL', '')}")
                added += 1
            elif isinstance(item, dict) and item.get("Topics"):
                for nested in item["Topics"]:
                    if added >= count:
                        break
                    if nested.get("Text"):
                        lines.append(f"- {nested.get('Text')}\n  {nested.get('FirstURL', '')}")
                        added += 1
        if len(lines) == 1:
            return self._duckduckgo_html(query, count)
        return "\n".join(lines)

    def _duckduckgo_html(self, query: str, count: int) -> str:
        url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 CryptoAnalysisAgent/1.0"})
        with urlopen(req, timeout=self.timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, flags=re.S)
        links = re.findall(r'class="result__url"[^>]*>(.*?)</a>', html, flags=re.S) or re.findall(
            r'uddg=([^"&]+)', html
        )
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>', html, flags=re.S)
        if not titles:
            return f"未找到与「{query}」相关的结果"
        lines = [f"## 搜索: {query}\n"]
        for i, title in enumerate(titles[:count]):
            link = _strip_tags(links[i]) if i < len(links) else ""
            snippet = _strip_tags(snippets[i]) if i < len(snippets) else ""
            lines.append(f"- **{_strip_tags(title)}**\n  {link}\n  {snippet}")
        return "\n".join(lines)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string", description="搜索词", required=True),
            ToolParameter(name="count", type="integer", description="返回条数，默认 5", required=False),
        ]


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()
