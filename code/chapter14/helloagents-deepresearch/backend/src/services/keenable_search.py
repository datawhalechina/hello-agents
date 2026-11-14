"""Keenable search backend.

Keenable (https://keenable.ai) exposes a public search endpoint that works
without an API key, so this is the one ``SEARCH_API`` option that runs on a
fresh checkout with no credentials. Setting ``KEENABLE_API_KEY`` switches to
the keyed endpoint, which only lifts the per-IP rate limits.

``SearchTool`` in ``hello-agents`` 0.2.9 ships a fixed set of backends and
silently falls back to ``hybrid`` for unknown names, so this backend is
implemented here and selected by :func:`services.search.dispatch_search`.
The returned payload has the same shape as ``SearchTool`` results
(``results`` / ``backend`` / ``answer`` / ``notices``) so the downstream
formatting helpers in ``utils.py`` need no changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

KEENABLE_API_BASE = "https://api.keenable.ai"
# Identifies this application on keyless calls; the public endpoint rejects
# requests without it.
KEENABLE_APP_TITLE = "hello-agents-deepresearch"
KEENABLE_BACKEND = "keenable"
SNIPPET_MAX_LENGTH = 1000
SEARCH_TIMEOUT = 20
FETCH_TIMEOUT = 15
CHARS_PER_TOKEN = 4


def _api_key() -> str | None:
    key = (os.getenv("KEENABLE_API_KEY") or "").strip()
    return key or None


def _endpoint(path: str, api_key: str | None) -> str:
    suffix = "" if api_key else "/public"
    return f"{KEENABLE_API_BASE}/v1/{path}{suffix}"


def _headers(api_key: str | None) -> Dict[str, str]:
    headers = {"X-Keenable-Title": KEENABLE_APP_TITLE}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _limit_text(text: str, token_limit: int) -> str:
    char_limit = token_limit * CHARS_PER_TOKEN
    if len(text) <= char_limit:
        return text
    return f"{text[:char_limit]}... [truncated]"


def _rate_limit_notice(api_key: str | None) -> str:
    if api_key:
        return "Keenable 返回 429（请求过于频繁），请稍后重试。"
    return (
        "Keenable 公共接口返回 429（请求过于频繁）。"
        "请稍后重试，或设置 KEENABLE_API_KEY 以提高频率上限。"
    )


def fetch_page_content(url: str, api_key: str | None = None) -> str | None:
    """Fetch the readable text of ``url`` through Keenable.

    Returns ``None`` when the page cannot be fetched so callers can fall back
    to the search snippet.
    """
    try:
        response = requests.get(
            _endpoint("fetch", api_key),
            params={"url": url},
            headers=_headers(api_key),
            timeout=FETCH_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # pragma: no cover - network dependent
        logger.debug("Keenable fetch failed for %s: %s", url, exc)
        return None

    content = data.get("content") if isinstance(data, dict) else None
    return content if isinstance(content, str) and content.strip() else None


def search_keenable(
    query: str,
    *,
    fetch_full_page: bool = False,
    max_results: int = 5,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Run a Keenable web search and return a ``SearchTool``-shaped payload.

    Args:
        query: Search query.
        fetch_full_page: Also fetch each result's page text into ``raw_content``.
        max_results: Number of results to request (1-50).
        max_tokens: Token budget applied to ``raw_content`` per result.

    Returns:
        Dictionary with ``results``, ``backend``, ``answer`` and ``notices``.
        A rate limit (HTTP 429) yields empty ``results`` and a notice rather
        than raising, so the caller can report it and move on.

    Raises:
        RuntimeError: For network failures and non-429 HTTP errors.
    """
    api_key = _api_key()
    body: Dict[str, Any] = {
        "query": query,
        "max_results": max(1, min(int(max_results), 50)),
        "snippet_max_length": SNIPPET_MAX_LENGTH,
    }

    try:
        response = requests.post(
            _endpoint("search", api_key),
            json=body,
            headers=_headers(api_key),
            timeout=SEARCH_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Keenable 搜索请求失败: {exc}") from exc

    if response.status_code == 429:
        notice = _rate_limit_notice(api_key)
        logger.warning(notice)
        return {
            "results": [],
            "backend": KEENABLE_BACKEND,
            "answer": None,
            "notices": [notice],
        }

    if response.status_code >= 400:
        detail = response.text.strip()[:200]
        raise RuntimeError(f"Keenable 搜索失败: HTTP {response.status_code} {detail}")

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Keenable 搜索失败: 响应不是有效的 JSON") from exc

    results: List[Dict[str, Any]] = []
    notices: List[str] = []

    for entry in data.get("results") or []:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url:
            notices.append(f"忽略缺少 URL 的 Keenable 结果: {entry}")
            continue

        title = entry.get("title") or url
        content = entry.get("snippet") or entry.get("description") or ""

        raw_content = content
        if fetch_full_page:
            fetched = fetch_page_content(url, api_key)
            if fetched:
                raw_content = _limit_text(fetched, max_tokens)

        results.append(
            {
                "title": title,
                "url": url,
                "content": content,
                "raw_content": raw_content,
            }
        )

    return {
        "results": results,
        "backend": KEENABLE_BACKEND,
        "answer": None,
        "notices": notices,
    }
