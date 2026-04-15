"""Tavily web search tool for hello_agents framework"""

import logging
import re
from typing import Dict, Any, List

from hello_agents.tools.base import Tool, ToolParameter

logger = logging.getLogger("game.tools")


class TavilySearchTool(Tool):
    """Tavily web search tool - search-only, no AI answer generation"""

    def __init__(self, api_key: str):
        super().__init__(
            name="tavily_search",
            description=(
                "Search the web for information about a historical figure. "
                "Input the figure's name to retrieve relevant biographical information."
            )
        )
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required for TavilySearchTool")

        from tavily import TavilyClient
        self._client = TavilyClient(api_key=api_key)
        logger.info("[TOOL] TavilySearchTool initialized")

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        Execute web search

        Args:
            parameters: dict with key 'query' - the search query string

        Returns:
            Concatenated search result snippets as a single string
        """
        query = parameters.get("query", "").strip()
        if not query:
            return "Error: search query cannot be empty"

        logger.info(f"[TOOL] Tavily search | query={query!r}")
        try:
            response = self._client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                include_answer=False,   # raw search only, no AI answer
            )
            results = response.get("results", [])
            if not results:
                logger.warning("[TOOL] Tavily returned no results")
                return "No search results found."

            # Take top 1 result, clean and truncate content to 300 chars
            MAX_RESULTS = 1
            MAX_CONTENT_LEN = 300

            def _clean(text: str) -> str:
                """Remove noise: extra whitespace, URLs, repeated punctuation."""
                text = re.sub(r'https?://\S+', '', text)          # strip URLs
                text = re.sub(r'\s+', ' ', text)                   # collapse whitespace
                text = re.sub(r'[。，、]{2,}', '。', text)          # deduplicate punctuation
                text = re.sub(r'[\.]{3,}', '...', text)            # normalize ellipsis
                return text.strip()

            snippets = []
            for item in results[:MAX_RESULTS]:
                content = _clean(item.get("content", ""))
                if content:
                    if len(content) > MAX_CONTENT_LEN:
                        content = content[:MAX_CONTENT_LEN] + "..."
                    snippets.append(content)

            combined = "\n".join(snippets)
            logger.info(
                f"[TOOL] Tavily search completed | results={len(results)} "
                f"used={len(snippets)} total_chars={len(combined)}"
            )
            return combined

        except Exception as e:
            logger.error(f"[TOOL] Tavily search failed: {e}", exc_info=True)
            return f"Search failed: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query, e.g. the name of a historical figure",
                required=True
            )
        ]
