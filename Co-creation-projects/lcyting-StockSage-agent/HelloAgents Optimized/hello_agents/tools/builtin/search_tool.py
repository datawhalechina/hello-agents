"""搜索工具 - HelloAgents 原生搜索实现。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List

import requests

from ..base import Tool, ToolParameter

try:  # 可选依赖，缺失时降级能力
    from markdownify import markdownify
except Exception:  # pragma: no cover - 可选依赖
    markdownify = None  # type: ignore

try:
    from ddgs import DDGS  # type: ignore
except Exception:  # pragma: no cover - 可选依赖
    DDGS = None  # type: ignore

try:
    from tavily import TavilyClient  # type: ignore
except Exception:  # pragma: no cover - 可选依赖
    TavilyClient = None  # type: ignore

try:
    from serpapi import GoogleSearch  # type: ignore
except Exception:  # pragma: no cover - 可选依赖
    GoogleSearch = None  # type: ignore

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4
DEFAULT_MAX_RESULTS = 5
SUPPORTED_RETURN_MODES = {"text", "structured", "json", "dict"}
SUPPORTED_BACKENDS = {
    "hybrid",
    "advanced",
    "tavily",
    "serpapi",
    "duckduckgo",
    "searxng",
    "perplexity",
}


def _limit_text(text: str, token_limit: int) -> str:
    char_limit = token_limit * CHARS_PER_TOKEN
    if len(text) <= char_limit:
        return text
    return text[:char_limit] + "... [truncated]"


def _fetch_raw_content(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - 网络环境不稳定
        logger.debug("Failed to fetch raw content for %s: %s", url, exc)
        return None

    if markdownify is not None:
        try:
            return markdownify(response.text)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - 可选依赖失败
            logger.debug("markdownify failed for %s: %s", url, exc)
    return response.text


def _normalized_result(
    *,
    title: str,
    url: str,
    content: str,
    raw_content: str | None,
) -> Dict[str, str]:
    payload: Dict[str, str] = {
        "title": title or url,
        "url": url,
        "content": content or "",
    }
    if raw_content is not None:
        payload["raw_content"] = raw_content
    return payload


def _structured_payload(
    results: Iterable[Dict[str, Any]],
    *,
    backend: str,
    answer: str | None = None,
    notices: Iterable[str] | None = None,
) -> Dict[str, Any]:
    return {
        "results": list(results),
        "backend": backend,
        "answer": answer,
        "notices": list(notices or []),
    }


class SearchTool(Tool):
    """支持多后端、可返回结构化结果的搜索工具。"""

    def __init__(
        self,
        backend: str = "hybrid",
        tavily_key: str | None = None,
        serpapi_key: str | None = None,
        perplexity_key: str | None = None,
    ) -> None:
        super().__init__(
            name="search",
            description=(
                "智能网页搜索引擎，支持 Tavily、SerpApi、DuckDuckGo、SearXNG、"
                "Perplexity 等后端，可返回结构化或文本化的搜索结果。"
            ),
        )
        self.backend = (backend or "hybrid").lower()
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
        self.perplexity_key = perplexity_key or os.getenv("PERPLEXITY_API_KEY")

        self.available_backends: list[str] = []
        self.tavily_client = None
        self._setup_backends()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, parameters: Dict[str, Any]) -> str | Dict[str, Any]:  # type: ignore[override]
        query = (parameters.get("input") or parameters.get("query") or "").strip()
        if not query:
            return "错误：搜索查询不能为空"

        backend = str(parameters.get("backend", self.backend) or "hybrid").lower()
        backend = backend if backend in SUPPORTED_BACKENDS else "hybrid"

        mode = str(
            parameters.get("mode") or parameters.get("return_mode") or "text"
        ).lower()
        if mode not in SUPPORTED_RETURN_MODES:
            mode = "text"

        fetch_full_page = bool(parameters.get("fetch_full_page", False))
        max_results = int(parameters.get("max_results", DEFAULT_MAX_RESULTS))
        max_tokens = int(parameters.get("max_tokens_per_source", 2000))
        loop_count = int(parameters.get("loop_count", 0))

        payload = self._structured_search(
            query=query,
            backend=backend,
            fetch_full_page=fetch_full_page,
            max_results=max_results,
            max_tokens=max_tokens,
            loop_count=loop_count,
        )

        if mode in {"structured", "json", "dict"}:
            return payload

        return self._format_text_response(query=query, payload=payload)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="搜索查询关键词",
                required=True,
            ),
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _setup_backends(self) -> None:
        if self.tavily_key and TavilyClient is not None:
            try:
                self.tavily_client = TavilyClient(api_key=self.tavily_key)
                self.available_backends.append("tavily")
                print("✅ Tavily 搜索引擎已初始化")
            except Exception as exc:  # pragma: no cover - 第三方库初始化失败
                print(f"⚠️ Tavily 初始化失败: {exc}")
        elif self.tavily_key:
            print("⚠️ 未安装 tavily-python，无法使用 Tavily 搜索")
        else:
            print("⚠️ TAVILY_API_KEY 未设置")

        if self.serpapi_key:
            if GoogleSearch is not None:
                self.available_backends.append("serpapi")
                print("✅ SerpApi 搜索引擎已初始化")
            else:
                print("⚠️ 未安装 google-search-results，无法使用 SerpApi 搜索")
        else:
            print("⚠️ SERPAPI_API_KEY 未设置")

        if self.backend not in SUPPORTED_BACKENDS:
            print("⚠️ 不支持的搜索后端，将使用 hybrid 模式")
            self.backend = "hybrid"
        elif self.backend == "tavily" and "tavily" not in self.available_backends:
            print("⚠️ Tavily 不可用，将使用 hybrid 模式")
            self.backend = "hybrid"
        elif self.backend == "serpapi" and "serpapi" not in self.available_backends:
            print("⚠️ SerpApi 不可用，将使用 hybrid 模式")
            self.backend = "hybrid"

        if self.backend == "hybrid":
            if self.available_backends:
                print(
                    "🔧 混合搜索模式已启用，可用后端: "
                    + ", ".join(self.available_backends)
                )
            else:
                print("⚠️ 没有可用的 Tavily/SerpApi 搜索源，将回退到通用模式")

    def _structured_search(
        self,
        *,
        query: str,
        backend: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
        loop_count: int,
    ) -> Dict[str, Any]:
        # 统一将 hybrid 视作 advanced，以保持向后兼容的优先级逻辑
        target_backend = "advanced" if backend == "hybrid" else backend

        if target_backend == "tavily":
            return self._search_tavily(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
            )
        if target_backend == "serpapi":
            return self._search_serpapi(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
            )
        if target_backend == "duckduckgo":
            return self._search_duckduckgo(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
            )
        if target_backend == "searxng":
            return self._search_searxng(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
            )
        if target_backend == "perplexity":
            return self._search_perplexity(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
                loop_count=loop_count,
            )
        if target_backend == "advanced":
            return self._search_advanced(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
                loop_count=loop_count,
            )

        raise ValueError(f"Unsupported search backend: {backend}")

    def _search_tavily(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
    ) -> Dict[str, Any]:
        if not self.tavily_client:
            message = "TAVILY_API_KEY 未配置或 tavily 未安装"
            raise RuntimeError(message)

        response = self.tavily_client.search(  # type: ignore[call-arg]
            query=query,
            max_results=max_results,
            include_raw_content=fetch_full_page,
        )

        results = []
        for item in response.get("results", [])[:max_results]:
            raw = item.get("raw_content") if fetch_full_page else item.get("content")
            if raw and fetch_full_page:
                raw = _limit_text(raw, max_tokens)
            results.append(
                _normalized_result(
                    title=item.get("title") or item.get("url", ""),
                    url=item.get("url", ""),
                    content=item.get("content") or "",
                    raw_content=raw,
                )
            )

        return _structured_payload(
            results,
            backend="tavily",
            answer=response.get("answer"),
        )

    def _search_serpapi(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
    ) -> Dict[str, Any]:
        if not self.serpapi_key:
            raise RuntimeError("SERPAPI_API_KEY 未配置，无法使用 SerpApi 搜索")
        if GoogleSearch is None:
            raise RuntimeError("未安装 google-search-results，无法使用 SerpApi")

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_key,
            "gl": "cn",
            "hl": "zh-cn",
            "num": max_results,
        }

        response = GoogleSearch(params).get_dict()

        answer_box = response.get("answer_box") or {}
        answer = answer_box.get("answer") or answer_box.get("snippet")

        results = []
        for item in response.get("organic_results", [])[:max_results]:
            raw_content = item.get("snippet")
            if raw_content and fetch_full_page:
                raw_content = _limit_text(raw_content, max_tokens)
            results.append(
                _normalized_result(
                    title=item.get("title") or item.get("link", ""),
                    url=item.get("link", ""),
                    content=item.get("snippet") or "",
                    raw_content=raw_content,
                )
            )

        return _structured_payload(results, backend="serpapi", answer=answer)

    def _search_duckduckgo(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
    ) -> Dict[str, Any]:
        if DDGS is None:
            raise RuntimeError("未安装 ddgs，无法使用 DuckDuckGo 搜索")

        results: List[Dict[str, Any]] = []
        notices: List[str] = []

        try:
            with DDGS(timeout=10) as client:  # type: ignore[call-arg]
                search_results = client.text(
                    query, max_results=max_results, backend="duckduckgo"
                )
        except Exception as exc:  # pragma: no cover - 网络异常
            raise RuntimeError(f"DuckDuckGo 搜索失败: {exc}")

        for entry in search_results:
            url = entry.get("href") or entry.get("url")
            title = entry.get("title") or url or ""
            content = entry.get("body") or entry.get("content") or ""

            if not url or not title:
                notices.append(f"忽略不完整的 DuckDuckGo 结果: {entry}")
                continue

            raw_content = content
            if fetch_full_page and url:
                fetched = _fetch_raw_content(url)
                if fetched:
                    raw_content = _limit_text(fetched, max_tokens)

            results.append(
                _normalized_result(
                    title=title,
                    url=url,
                    content=content,
                    raw_content=raw_content,
                )
            )

        return _structured_payload(results, backend="duckduckgo", notices=notices)

    def _search_searxng(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
    ) -> Dict[str, Any]:
        host = os.getenv("SEARXNG_URL", "http://localhost:8888").rstrip("/")
        endpoint = f"{host}/search"

        try:
            response = requests.get(
                endpoint,
                params={
                    "q": query,
                    "format": "json",
                    "language": "zh-CN",
                    "safesearch": 1,
                    "categories": "general",
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - 网络异常
            raise RuntimeError(f"SearXNG 搜索失败: {exc}")

        results = []
        for entry in payload.get("results", [])[:max_results]:
            url = entry.get("url") or entry.get("link")
            title = entry.get("title") or url or ""
            if not url or not title:
                continue
            content = entry.get("content") or entry.get("snippet") or ""
            raw_content = content
            if fetch_full_page and url:
                fetched = _fetch_raw_content(url)
                if fetched:
                    raw_content = _limit_text(fetched, max_tokens)
            results.append(
                _normalized_result(
                    title=title,
                    url=url,
                    content=content,
                    raw_content=raw_content,
                )
            )

        return _structured_payload(results, backend="searxng")

    def _search_perplexity(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
        loop_count: int,
    ) -> Dict[str, Any]:
        if not self.perplexity_key:
            raise RuntimeError("PERPLEXITY_API_KEY 未配置，无法使用 Perplexity 搜索")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.perplexity_key}",
        }
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources.",
                },
                {"role": "user", "content": query},
            ],
        }

        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", []) or ["https://perplexity.ai"]

        results = []
        for idx, url in enumerate(citations[:max_results], start=1):
            snippet = content if idx == 1 else "See main Perplexity response above."
            raw = (
                _limit_text(content, max_tokens)
                if fetch_full_page and idx == 1
                else None
            )
            results.append(
                _normalized_result(
                    title=f"Perplexity Source {loop_count + 1}-{idx}",
                    url=url,
                    content=snippet,
                    raw_content=raw,
                )
            )

        return _structured_payload(results, backend="perplexity", answer=content)

    def _search_advanced(
        self,
        *,
        query: str,
        fetch_full_page: bool,
        max_results: int,
        max_tokens: int,
        loop_count: int,
    ) -> Dict[str, Any]:
        notices: List[str] = []
        aggregated: List[Dict[str, Any]] = []
        answer: str | None = None
        backend_used = "advanced"

        if self.tavily_client:
            try:
                tavily_payload = self._search_tavily(
                    query=query,
                    fetch_full_page=fetch_full_page,
                    max_results=max_results,
                    max_tokens=max_tokens,
                )
                if tavily_payload["results"]:
                    return tavily_payload
                notices.append("⚠️ Tavily 未返回有效结果，尝试其他搜索源")
            except Exception as exc:  # pragma: no cover - 第三方库异常
                notices.append(f"⚠️ Tavily 搜索失败：{exc}")

        if self.serpapi_key and GoogleSearch is not None:
            try:
                serp_payload = self._search_serpapi(
                    query=query,
                    fetch_full_page=fetch_full_page,
                    max_results=max_results,
                    max_tokens=max_tokens,
                )
                if serp_payload["results"]:
                    serp_payload["notices"] = notices + serp_payload.get("notices", [])
                    return serp_payload
                notices.append("⚠️ SerpApi 未返回有效结果，回退到通用搜索")
            except Exception as exc:  # pragma: no cover - 第三方库异常
                notices.append(f"⚠️ SerpApi 搜索失败：{exc}")

        try:
            ddg_payload = self._search_duckduckgo(
                query=query,
                fetch_full_page=fetch_full_page,
                max_results=max_results,
                max_tokens=max_tokens,
            )
            aggregated.extend(ddg_payload["results"])
            notices.extend(ddg_payload.get("notices", []))
            backend_used = ddg_payload.get("backend", backend_used)
        except Exception as exc:  # pragma: no cover - 通用兜底
            notices.append(f"⚠️ DuckDuckGo 搜索失败：{exc}")

        return _structured_payload(
            aggregated,
            backend=backend_used,
            answer=answer,
            notices=notices,
        )

    def _format_text_response(self, *, query: str, payload: Dict[str, Any]) -> str:
        answer = payload.get("answer")
        notices = payload.get("notices") or []
        results = payload.get("results") or []
        backend = payload.get("backend", self.backend)

        lines = [f"🔍 搜索关键词：{query}", f"🧭 使用搜索源：{backend}"]
        if answer:
            lines.append(f"💡 直接答案：{answer}")

        if results:
            lines.append("")
            lines.append("📚 参考来源：")
            for idx, item in enumerate(results, start=1):
                title = item.get("title") or item.get("url", "")
                lines.append(f"[{idx}] {title}")
                if item.get("content"):
                    lines.append(f"    {item['content']}")
                if item.get("url"):
                    lines.append(f"    来源: {item['url']}")
                lines.append("")
        else:
            lines.append("❌ 未找到相关搜索结果。")

        if notices:
            lines.append("⚠️ 注意事项：")
            for notice in notices:
                if notice:
                    lines.append(f"- {notice}")

        return "\n".join(line for line in lines if line is not None)


# 便捷函数


def search(query: str, backend: str = "hybrid") -> str:
    tool = SearchTool(backend=backend)
    return tool.run({"input": query, "backend": backend})  # type: ignore[return-value]


def search_tavily(query: str) -> str:
    tool = SearchTool(backend="tavily")
    return tool.run({"input": query, "backend": "tavily"})  # type: ignore[return-value]


def search_serpapi(query: str) -> str:
    tool = SearchTool(backend="serpapi")
    return tool.run({"input": query, "backend": "serpapi"})  # type: ignore[return-value]


def search_hybrid(query: str) -> str:
    tool = SearchTool(backend="hybrid")
    return tool.run({"input": query, "backend": "hybrid"})  # type: ignore[return-value]
