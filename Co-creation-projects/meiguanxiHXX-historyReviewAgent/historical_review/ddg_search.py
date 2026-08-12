"""仅用 DuckDuckGo 的轻量检索，避免 HelloAgents SearchTool 初始化时打印 Tavily/SerpAPI 提示。"""

from __future__ import annotations


def duckduckgo_search_text(
    query: str,
    *,
    max_results: int = 4,
    max_body_chars: int = 600,
) -> str:
    query = (query or "").strip()
    if not query:
        return "【检索】查询为空。"

    try:
        from ddgs import DDGS
    except ImportError:
        return "【检索】未安装 duckduckgo-search，请执行：pip install duckduckgo-search"

    try:
        with DDGS(timeout=15) as client:  # type: ignore[call-arg]
            rows = client.text(query, max_results=max_results, backend="duckduckgo")
    except Exception as e:  # pragma: no cover
        return f"【检索】DuckDuckGo 请求失败：{e}"

    if not rows:
        return "【检索】无结果。"

    lines: list[str] = ["【DuckDuckGo 检索摘要】"]
    for i, entry in enumerate(rows, 1):
        url = entry.get("href") or entry.get("url") or ""
        title = entry.get("title") or url or "(无标题)"
        body = entry.get("body") or entry.get("content") or ""
        if len(body) > max_body_chars:
            body = body[:max_body_chars] + "…"
        lines.append(f"{i}. {title}\n   {url}\n   {body}")
    return "\n\n".join(lines)
