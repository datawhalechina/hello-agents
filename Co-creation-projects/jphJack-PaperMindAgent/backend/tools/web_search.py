"""联网搜索工具：DuckDuckGo HTML 搜索，用于创新点新颖性去重"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from backend.tools.base import Tool


# ---------- DuckDuckGo HTML 结果解析 ----------

# 结果标题与链接
_TITLE_PATTERN = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
# 结果摘要
_SNIPPET_PATTERN = re.compile(
    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL,
)
# HTML 标签
_TAG_PATTERN = re.compile(r"<[^>]+>")

# 常见 HTML 实体
_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
}


def _strip_html(s: str) -> str:
    """去除 HTML 标签与实体，压缩空白"""
    s = _TAG_PATTERN.sub("", s)
    for entity, char in _HTML_ENTITIES.items():
        s = s.replace(entity, char)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _extract_real_url(href: str) -> str:
    """从 DuckDuckGo 跳转链接中提取真实 URL"""
    if "uddg=" in href:
        # 补全协议头以便解析（DDG 链接常以 // 开头）
        target = href if href.startswith("http") else "https:" + href
        parsed = urlparse(target)
        qs = parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
    return href


def _parse_ddg_html(html: str, max_results: int) -> list[dict]:
    """解析 DuckDuckGo HTML 结果页，提取标题、摘要、URL"""
    titles = _TITLE_PATTERN.findall(html)
    snippets = _SNIPPET_PATTERN.findall(html)

    results: list[dict] = []
    for i, (href, raw_title) in enumerate(titles):
        if i >= max_results:
            break
        title = _strip_html(raw_title)
        snippet = _strip_html(snippets[i]) if i < len(snippets) else ""
        url = _extract_real_url(href)
        if title:
            results.append({"title": title, "snippet": snippet, "url": url})
    return results


# ---------- 异步工具函数 ----------

async def web_search(query: str, max_results: int = 5) -> dict:
    """DuckDuckGo 联网搜索，返回标题与摘要。

    失败时降级返回空结果，不崩溃。

    Returns:
        {"query": query, "results": [{title, snippet, url}]}
    """
    import httpx
    from urllib.parse import quote

    try:
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        results = _parse_ddg_html(html, max_results)
        return {"query": query, "results": results}
    except Exception as e:
        # 降级：返回空结果，不崩溃
        return {"query": query, "results": [], "error": f"联网搜索失败: {e}"}


# ---------- Tool 定义 ----------

_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "搜索查询文本",
        },
        "max_results": {
            "type": "integer",
            "description": "最大返回结果数，默认 5",
            "default": 5,
        },
    },
    "required": ["query"],
}

web_search_tool = Tool(
    name="web_search",
    description=(
        "联网搜索（DuckDuckGo），用于创新点新颖性去重。"
        "返回 {query, results: [{title, snippet, url}]}。失败时降级返回空结果。"
    ),
    parameters=_PARAMETERS,
    func=web_search,
)
