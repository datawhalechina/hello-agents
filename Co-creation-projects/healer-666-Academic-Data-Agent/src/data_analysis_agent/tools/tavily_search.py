"""Web search tool backed by Tavily for domain knowledge lookup."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter

from ..tool_protocol import ToolErrorCode, ToolResponse


class TavilySearchTool(Tool):
    """Research-oriented Tavily search wrapper with graceful degradation."""

    def __init__(self):
        super().__init__(
            name="TavilySearchTool",
            description=(
                "Search the web for scientific background knowledge, domain terminology, acronyms, normal ranges, and contextual references. "
                "Use this tool before analysis whenever dataset columns or indicators contain unfamiliar professional terms or abbreviations. "
                "Provide a concise natural-language search query."
            ),
        )

    def execute(self, parameters: Dict[str, Any]) -> ToolResponse:
        query = parameters.get("query", parameters.get("input", ""))
        if not isinstance(query, str) or not query.strip():
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="TavilySearchTool expected a non-empty 'query' string.",
            )

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return ToolResponse.partial(
                text="No Tavily search credential is configured. Skip online search and proceed with local analysis only.",
                data={"query": query, "results": []},
                context={"query": query},
            )

        try:
            from tavily import TavilyClient
        except Exception:
            return ToolResponse.partial(
                text="The tavily-python dependency is unavailable in the current environment. Skip online search and proceed with local analysis only.",
                data={"query": query, "results": []},
                context={"query": query},
            )

        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, search_depth="advanced")
        except Exception as exc:
            return ToolResponse.partial(
                text=f"Tavily search is temporarily unavailable ({exc}). Skip online search and proceed with local analysis only.",
                data={"query": query, "results": []},
                context={"query": query},
            )

        results = response.get("results", []) if isinstance(response, dict) else []
        lines = [f"Search query: {query}"]
        for index, item in enumerate(results[:5], start=1):
            title = str(item.get("title", "Untitled")).strip()
            url = str(item.get("url", "")).strip()
            content = str(item.get("content", "")).strip()
            snippet = " ".join(content.split())[:500]
            lines.append(f"{index}. {title}")
            if url:
                lines.append(f"   URL: {url}")
            if snippet:
                lines.append(f"   Snippet: {snippet}")

        if len(lines) == 1:
            lines.append("No relevant results were returned.")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"query": query, "results": results, "raw_response": response},
            context={"query": query},
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        return self.execute(parameters).to_json()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Natural-language search query describing the domain term, abbreviation, biomarker, financial metric, or indicator that needs background knowledge.",
                required=True,
            )
        ]
