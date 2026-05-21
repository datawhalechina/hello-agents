"""Tavily 自动发现会议官网 proceedings 域名（无需事先写入 JSON 映射）。"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from .tavily_venue_config import get_official_proceedings_hosts, tavily_include_domains_for_venue

logger = logging.getLogger(__name__)

_PROCEEDINGS_PATH_HINTS = (
    "proceedings",
    "openaccess",
    "/papers/",
    "papers.nips",
    "thecvf.com",
    "mlr.press",
    "aclanthology",
    "openreview.net",
    "program",
    "main_conference",
    "main-conference",
)
_BAD_DISCOVERY_HOSTS = (
    "dblp.org",
    "arxiv.org",
    "openalex.org",
    "semanticscholar.org",
    "google.",
    "youtube.",
    "twitter.",
    "x.com",
    "facebook.",
    "wikipedia.org",
    "paperswithcode.com",
    "github.com",
    "reddit.com",
    "medium.com",
    "linkedin.com",
    "scholar.google",
)


def _normalize_host(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower().removeprefix("www.")
    except ValueError:
        return ""
    return host


def _score_proceedings_url(url: str, *, venue: str, year: int | None) -> float:
    if not url:
        return 0.0
    low = url.lower()
    host = _normalize_host(url)
    if not host:
        return 0.0
    if any(b in host or b in low for b in _BAD_DISCOVERY_HOSTS):
        return 0.0

    score = 0.0
    official = get_official_proceedings_hosts()
    if any(h in host for h in official):
        score += 50.0
    if any(h in low for h in _PROCEEDINGS_PATH_HINTS):
        score += 25.0
    if year is not None and str(year) in low:
        score += 20.0
    vl = (venue or "").strip().lower()
    if vl and vl in low:
        score += 15.0
    if re.search(r"/(paper|publication|content|html)/", low):
        score += 8.0
    if "workshop" in low or "challenge" in low or "ntire" in low:
        score -= 30.0
    return score


@lru_cache(maxsize=128)
def _discovery_queries(venue: str, year: int | None) -> tuple[str, ...]:
    v = (venue or "").strip()
    y = f" {year}" if year is not None else ""
    return (
        f"{v}{y} official proceedings open access papers site",
        f"{v}{y} conference accepted papers list main conference",
        f"{v}{y} openaccess proceedings {v} papers",
        f"{v}{y} main conference track accepted papers",
        f"site:papers.nips.cc {v}{y} accepted papers main conference",
        f"site:openreview.net {v}{y} accepted papers",
    )


async def discover_proceedings_domains(
    *,
    api_key: str,
    venue: str,
    year: int | None = None,
    httpx_client: Any = None,
    max_domains: int = 3,
) -> list[str]:
    """用 Tavily 开放搜索会议名+年份，从结果 URL 推断官方 proceedings 站点域名。"""
    venue = (venue or "").strip()
    if not venue or not (api_key or "").strip():
        return []

    static = tavily_include_domains_for_venue(venue)
    if static:
        return list(static)[:max_domains]

    from .web_presearch import tavily_search_async

    host_scores: dict[str, float] = {}
    for q in _discovery_queries(venue, year):
        try:
            items = await tavily_search_async(
                api_key=api_key,
                query=q,
                max_results=8,
                include_domains=None,
                httpx_client=httpx_client,
            )
        except Exception as e:
            logger.debug("[proceedings_discovery] query failed %r: %s", q[:60], e)
            continue

        for it in items or []:
            link = str(it.get("link") or it.get("url") or "").strip()
            if not link:
                continue
            host = _normalize_host(link)
            if not host or "." not in host:
                continue
            sc = _score_proceedings_url(link, venue=venue, year=year)
            if sc <= 0:
                continue
            host_scores[host] = max(host_scores.get(host, 0.0), sc)

    ranked = sorted(host_scores.items(), key=lambda x: x[1], reverse=True)
    domains = [h for h, sc in ranked if sc >= 20.0][:max_domains]
    if domains:
        logger.info(
            "[proceedings_discovery] venue=%s year=%s → domains %s (scores=%s)",
            venue,
            year,
            domains,
            [round(host_scores[d], 1) for d in domains],
        )
    return domains


async def discover_proceedings_links(
    *,
    api_key: str,
    venue: str,
    year: int | None = None,
    httpx_client: Any = None,
    max_links: int = 5,
) -> list[dict[str, Any]]:
    """用 Tavily 找具体 proceedings/accepted-papers 页面，保留 link/raw_content 供后续抽取。"""
    venue = (venue or "").strip()
    if not venue or not (api_key or "").strip():
        return []

    from .web_presearch import tavily_search_async

    static_domains = tavily_include_domains_for_venue(venue) or None
    scored: dict[str, dict[str, Any]] = {}
    domain_passes = [static_domains, None] if static_domains else [None]
    for domain_pass in domain_passes:
        if scored and max(float(x.get("score") or 0) for x in scored.values()) >= 70:
            break
        for q in _discovery_queries(venue, year):
            try:
                items = await tavily_search_async(
                    api_key=api_key,
                    query=q,
                    max_results=8,
                    include_domains=domain_pass,
                    httpx_client=httpx_client,
                )
            except Exception as e:
                logger.debug("[proceedings_discovery] link query failed %r: %s", q[:60], e)
                continue
            for it in items or []:
                link = str(it.get("link") or it.get("url") or "").strip()
                if not link:
                    continue
                sc = _score_proceedings_url(link, venue=venue, year=year)
                if sc <= 0:
                    continue
                prev = scored.get(link)
                if prev and float(prev.get("score") or 0) >= sc:
                    continue
                scored[link] = {
                    "link": link,
                    "title": str(it.get("title") or "").strip(),
                    "snippet": str(it.get("snippet") or it.get("content") or "").strip(),
                    "raw_content": str(it.get("raw_content") or "")[:24000],
                    "score": sc,
                }

    ranked = sorted(scored.values(), key=lambda x: float(x.get("score") or 0), reverse=True)
    out = ranked[: max(1, int(max_links or 5))]
    if out:
        logger.info(
            "[proceedings_discovery] venue=%s year=%s → links=%s",
            venue,
            year,
            [x.get("link") for x in out],
        )
    return out
