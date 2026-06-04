"""Search helper compatible with the chapter 14 project."""

from __future__ import annotations

import os
from typing import Any


class SearchTool:
    """Small search facade returning the structured payload expected by the app."""

    def __init__(self, backend: str = "duckduckgo") -> None:
        self.backend = backend

    def run(self, parameters: dict[str, Any]) -> dict[str, Any] | str:
        query = str(parameters.get("input") or parameters.get("query") or "").strip()
        backend = str(parameters.get("backend") or self.backend or "duckduckgo").lower()
        max_results = int(parameters.get("max_results") or 5)

        if not query:
            return {"results": [], "backend": backend, "answer": None, "notices": ["empty query"]}

        if backend in {"duckduckgo", "advanced", "hybrid"}:
            return self._duckduckgo(query, max_results=max_results, backend=backend)
        if backend == "tavily":
            return self._tavily(query, max_results=max_results)

        notice = f"当前搜索后端 {backend} 暂未实现，已降级为 DuckDuckGo。"
        payload = self._duckduckgo(query, max_results=max_results, backend="duckduckgo")
        payload.setdefault("notices", []).append(notice)
        return payload

    def _duckduckgo(self, query: str, *, max_results: int, backend: str) -> dict[str, Any]:
        try:
            from ddgs import DDGS

            rows = DDGS().text(query, max_results=max_results)
            results = []
            for row in rows:
                results.append(
                    {
                        "title": row.get("title") or "",
                        "url": row.get("href") or row.get("url") or "",
                        "content": row.get("body") or row.get("content") or "",
                        "raw_content": row.get("body") or row.get("content") or "",
                    }
                )

            return {"results": results, "backend": backend, "answer": None, "notices": []}
        except Exception as exc:
            return {
                "results": [],
                "backend": backend,
                "answer": None,
                "notices": [f"DuckDuckGo search failed: {exc}"],
            }

    def _tavily(self, query: str, *, max_results: int) -> dict[str, Any]:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {
                "results": [],
                "backend": "tavily",
                "answer": None,
                "notices": ["TAVILY_API_KEY is not set"],
            }

        try:
            from tavily import TavilyClient

            response = TavilyClient(api_key=api_key).search(
                query=query,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False,
            )
            results = [
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "content": item.get("content") or "",
                    "raw_content": item.get("raw_content") or item.get("content") or "",
                }
                for item in response.get("results", [])
            ]
            return {
                "results": results,
                "backend": "tavily",
                "answer": response.get("answer"),
                "notices": [],
            }
        except Exception as exc:
            return {
                "results": [],
                "backend": "tavily",
                "answer": None,
                "notices": [f"Tavily search failed: {exc}"],
            }
