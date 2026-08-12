"""Wikipedia image search tool for hello_agents framework"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional

from hello_agents.tools.base import Tool, ToolParameter

logger = logging.getLogger("game.tools")

# Wikipedia REST API endpoints (no auth required)
_ZH_SUMMARY_URL = "https://zh.wikipedia.org/api/rest_v1/page/summary/{title}"
_EN_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Fake browser User-Agent to avoid 403 from Wikipedia
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GuessWhoAmI/1.0; "
        "+https://github.com/ieafei/hello-agents)"
    )
}


class SearchImageTool(Tool):
    """Wikipedia image search tool - fetch figure portrait from Wikipedia page summary."""

    def __init__(self):
        super().__init__(
            name="wikipedia_image_search",
            description=(
                "Search Wikipedia for a portrait image of a historical or fictional figure. "
                "Returns a list of image URLs from the Wikipedia page thumbnail."
            )
        )
        logger.info("[TOOL] SearchImageTool (Wikipedia) initialized")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_summary(self, title: str, lang: str = "zh") -> Optional[Dict]:
        """Fetch Wikipedia page summary (includes thumbnail) by exact title."""
        url_tpl = _ZH_SUMMARY_URL if lang == "zh" else _EN_SUMMARY_URL
        try:
            resp = requests.get(
                url_tpl.format(title=requests.utils.quote(title, safe="")),
                headers=_HEADERS,
                timeout=8,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"[TOOL] Wikipedia summary ({lang}) failed for {title!r}: {e}")
        return None

    def _get_photo_from_summary(self, summary: Dict, query: str) -> Optional[Dict[str, str]]:
        """Extract photo dict from a Wikipedia summary response."""
        thumbnail = summary.get("thumbnail")
        if not thumbnail:
            return None
        original = summary.get("originalimage", {})
        return {
            "url": original.get("source") or thumbnail.get("source", ""),
            "thumb": thumbnail.get("source", ""),
            "description": summary.get("title", query),
            "photographer": "Wikipedia",
        }

    def _lookup(self, query: str) -> List[Dict[str, str]]:
        """
        Directly call REST Summary API with the figure name (zh first, then en).
        Skips the w/api.php search step which is often blocked (403).
        Returns a list with at most 1 photo dict.
        """
        for lang in ("zh", "en"):
            summary = self._fetch_summary(query, lang)
            if not summary:
                continue
            photo = self._get_photo_from_summary(summary, query)
            if photo:
                logger.info(
                    f"[TOOL] Wikipedia image found | lang={lang} title={query!r} url={photo['url']!r}"
                )
                return [photo]
        logger.warning(f"[TOOL] No Wikipedia image found for query={query!r}")
        return []

    # ── Tool interface ────────────────────────────────────────────────────────

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        Search Wikipedia for images matching the query.

        Args:
            parameters: dict with key 'query' - the search keyword (e.g. figure name)

        Returns:
            JSON string with image list, or error message
        """
        query = parameters.get("query", "").strip()
        if not query:
            return "Error: search query cannot be empty"

        logger.info(f"[TOOL] Wikipedia image search | query={query!r}")
        photos = self._lookup(query)
        return json.dumps(photos, ensure_ascii=False)

    def search_photos(self, query: str, per_page: int = 3) -> List[Dict[str, str]]:
        """
        Convenience method: search and return parsed photo list directly.

        Args:
            query: search keyword (figure name)
            per_page: ignored (Wikipedia returns at most 1 portrait per page)

        Returns:
            List of photo dicts with url/thumb/description/photographer
        """
        raw = self.run({"query": query})
        try:
            return json.loads(raw) if raw.startswith("[") else []
        except Exception:
            return []

    def get_first_photo_url(self, query: str) -> Optional[str]:
        """Return the URL of the first matching photo, or None."""
        photos = self.search_photos(query)
        return photos[0]["url"] if photos else None

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search keyword, e.g. the name of a historical figure",
                required=True,
            ),
        ]
