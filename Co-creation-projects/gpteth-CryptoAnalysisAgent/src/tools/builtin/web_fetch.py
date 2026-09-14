"""Fetch a web page and return readable text."""

from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.request import Request, urlopen

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text


class WebFetchTool(Tool):
    def __init__(self, timeout: int = 15, max_chars: int = 12000):
        super().__init__(
            name="web_fetch",
            description="抓取指定 URL 的正文并转成纯文本。用于阅读公告、文档或新闻原文。",
        )
        self.timeout = timeout
        self.max_chars = max_chars

    def run(self, parameters: Dict[str, Any]) -> str:
        url = first_text(parameters, "url")
        if not url:
            return "错误: 请提供 url"
        if not url.startswith(("http://", "https://")):
            return "URL 必须以 http:// 或 https:// 开头"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 CryptoAnalysisAgent/1.0"})
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read(self.max_chars * 4)
                content_type = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="ignore")
            if "html" in content_type.lower() or "<html" in text[:500].lower():
                text = _html_to_text(text)
            text = text.strip()
            if len(text) > self.max_chars:
                text = text[:self.max_chars] + "\n…(truncated)"
            return f"# {url}\n\n{text or '(空页面)'}"
        except Exception as exc:
            return f"抓取失败: {exc}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="url", type="string", description="要抓取的网页地址", required=True),
        ]


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)</(p|div|h1|h2|h3|li|br|tr)>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"[ \t]+\n", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return re.sub(r"[ \t]{2,}", " ", html).strip()
