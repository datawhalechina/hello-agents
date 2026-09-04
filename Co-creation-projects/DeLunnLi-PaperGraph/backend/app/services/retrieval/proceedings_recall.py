"""Proceedings recall from official/discovered pages."""

from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import Any

import anyio

from ...core.paper import Paper as LitPaper
from ...core.search.normalize import extract_pinned_topic_terms
from .paper_filters import should_exclude_main_conference_paper
from .plan_helpers import is_venue_browse_plan
from .recall_context import RecallContext
from .search_plan import ResolvedSearchPlan

logger = logging.getLogger(__name__)


def _clean_html_text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))).strip()


def _paper_from_title(
    searcher: Any,
    *,
    title: str,
    venue: str,
    year: int | None,
    source_url: str = "",
    authors: list[Any] | None = None,
    source: str = "tavily",
) -> LitPaper:
    journal = venue.strip().upper() or "Official Proceedings"
    return searcher._make_paper(
        title=title, authors=authors or [], abstract="",
        journal=journal, year=int(year) if year else None,
        source_url=source_url or None, source=source,
    )


async def _llm_extract_papers_from_page(
    page_text: str,
    *,
    venue: str,
    year: int | None,
    topic: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Extract main-track paper titles and authors from a page."""
    try:
        from ..llm.llm_service import get_llm, is_llm_configured
        from ..llm.agent_runtime import run_json_task

        if not is_llm_configured():
            return []
    except Exception:
        return []

    clipped = _clean_html_text(page_text)[:12000]
    if len(clipped) < 200:
        return []

    prompt = (
        "从下面的会议页面文本中抽取主会论文的标题和作者。\n"
        "重要：只抽取真实的学术论文，标题应该是具体的研究成果名称。\n"
        "绝对不要抽取以下内容：\n"
        "- 论文集名称（如 Advances in Neural Information Processing Systems）\n"
        "- 导航链接（如 Proceedings、List of Proceedings、Accepted Papers）\n"
        "- Workshop、Challenge、Tutorial、Demonstration 论文\n"
        "- 关于会议本身的元分析/综述论文\n"
        "- 数据集/代码包/Benchmark 描述文档\n"
        "- 日程表、征文通知、委员会名单\n"
        "- 网页导航、页眉页脚、版权声明\n"
        f"会议：{venue}，年份：{year or '未知'}，最多 {limit} 篇。\n"
        "输出 JSON：{\"papers\":[{\"title\":\"...\",\"authors\":[\"...\"]}]}\n\n"
        f"页面文本：\n{clipped}"
    )
    try:
        data = await anyio.to_thread.run_sync(
            lambda: run_json_task(
                task_name="proceedings_page_extract",
                agent_name="papergraph_proceedings_extractor",
                llm=get_llm(),
                system_prompt="你是严格的信息抽取器，只输出合法 JSON，不得编造页面文本中没有的论文。",
                user_prompt=prompt, timeout_sec=15, retries=0,
                default={"papers": []},
            )
        )
    except Exception:
        return []
    arr = data.get("papers") if isinstance(data, dict) else []
    if not isinstance(arr, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for it in arr:
        if not isinstance(it, dict):
            continue
        title = _clean_paper_title(_clean_html_text(str(it.get("title") or "")))
        if not title or len(title) < 8 or len(title) > 300:
            continue
        tl = title.lower()
        if any(w in tl for w in ("workshop", "challenge", "tutorial", "demo track", "competition")):
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        authors = it.get("authors") if isinstance(it.get("authors"), list) else []
        out.append({"title": title, "authors": [str(a)[:120] for a in authors[:12] if str(a).strip()]})
        if len(out) >= limit:
            break
    return out


async def _fetch_discovered_page(searcher: Any, url: str) -> str:
    await searcher._ensure_async_client()
    resp = await searcher._async_http_get_with_retry(
        url, params={},
        headers={"User-Agent": searcher._user_agent()},
        timeout=30.0, max_attempts=2,
    )
    return resp.text or ""


def _clean_paper_title(raw_title: str) -> str:
    """Strip common title prefixes."""
    t = (raw_title or "").strip()
    t = re.sub(r"^\s*\[PDF\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*\[pdf\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*#+\s*", "", t)
    t = re.sub(r"^\s*\d+[\.\)]\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _dedupe_by_title(papers: list[LitPaper]) -> list[LitPaper]:
    seen: set[str] = set()
    out: list[LitPaper] = []
    for p in papers:
        key = (getattr(p, "title", "") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(p)
    return out


async def _recall_from_discovered_links(
    searcher: Any,
    *,
    links: list[dict[str, Any]],
    venue: str,
    year: int | None,
    topic: str,
    max_results: int,
) -> list[LitPaper]:
    """Extract papers from discovered proceedings links."""
    papers: list[LitPaper] = []
    seen_titles: set[str] = set()
    link_limit = min(len(links), max(8, max_results // 3))

    for item in links[:link_limit]:
        link = str(item.get("link") or "").strip()
        if not link:
            continue

        page = str(item.get("raw_content") or "").strip()
        if len(page) < 200:
            try:
                page = await _fetch_discovered_page(searcher, link)
            except Exception:
                page = ""

        llm_items = await _llm_extract_papers_from_page(
            page, venue=venue, year=year, topic=topic, limit=max_results,
        )
        # Empty extraction usually means this is not a paper listing.

        for lp in llm_items:
            title = _clean_paper_title(lp["title"].strip())
            if not title or len(title) < 8 or len(title) > 300:
                continue
            tl = title.lower()
            if any(w in tl for w in ("workshop", "challenge", "tutorial", "demo track", "competition")):
                continue
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            papers.append(
                _paper_from_title(
                    searcher, title=title, venue=venue, year=year,
                    source_url=link, authors=lp.get("authors", []),
                    source="tavily",
                )
            )
            if len(papers) >= max(8, int(max_results)):
                return papers
    return papers


async def recall_from_proceedings_site(
    searcher: Any,
    *,
    plan: ResolvedSearchPlan,
    ctx: RecallContext | None = None,
    max_results: int = 24,
) -> list[LitPaper]:
    """Recall papers through discovery and configured proceedings domains."""
    if not plan.venues:
        return []
    venue = str(plan.venues[0]).strip()
    if not venue:
        return []

    year = plan.year_from if plan.year_from is not None else plan.year_to
    q = (ctx.effective_query if ctx else None) or (plan.query or "").strip()
    if not q and plan.keywords:
        q = " ".join(str(k) for k in plan.keywords[:4])
    if not q:
        q = venue

    topic = extract_pinned_topic_terms(
        query=q, merged_kw=list(plan.keywords or []),
        venue=venue, year=year if isinstance(year, int) else None,
    )
    if not topic and is_venue_browse_plan(plan):
        topic = ""

    from ...settings import get_settings

    tavily_key = str(getattr(get_settings(), "tavily_api_key", "") or "").strip()
    if not tavily_key:
        logger.info("[proceedings_recall] skip tavily: no tavily_api_key")
        return []

    venue_browse = is_venue_browse_plan(plan)
    y = year if isinstance(year, int) else None

    from .proceedings_discovery import discover_proceedings_links
    from ...core.search.sources.tavily import search_tavily_proceedings

    async def _discover() -> list[LitPaper]:
        try:
            links = await discover_proceedings_links(
                api_key=tavily_key, venue=venue, year=y,
                httpx_client=getattr(searcher, "_async_client", None),
                max_links=max(5, max_results // 2),
            )
            if not links:
                return []
            logger.info("[proceedings_recall] discovered %d links, LLM extracting…", len(links))
            return await _recall_from_discovered_links(
                searcher, links=links, venue=venue, year=y,
                topic=topic, max_results=max_results,
            )
        except Exception:
            logger.debug("[proceedings_recall] discovery failed", exc_info=True)
            return []

    async def _domain_search() -> list[LitPaper]:
        try:
            proc_cap = max(24, min(40, int(max_results))) if venue_browse else max(8, min(30, int(max_results)))
            papers = list(
                await search_tavily_proceedings(
                    searcher, q, venue, year, proc_cap, venue_browse=venue_browse,
                ) or []
            )
            logger.info("[proceedings_recall] domain search → %d papers", len(papers))
            return papers
        except Exception as e:
            logger.warning("[proceedings_recall] domain search failed: %s", e)
            return []

    discovered, domain_papers = await asyncio.gather(_discover(), _domain_search())
    all_papers = _dedupe_by_title(discovered + domain_papers)

    if plan.main_conference_proceedings_only:
        pin_y = plan.year_from if plan.year_from == plan.year_to else None
        all_papers = [
            p for p in all_papers
            if not should_exclude_main_conference_paper(p, venue, pinned_year=pin_y)
        ]

    logger.info(
        "[proceedings_recall] venue=%s year=%s → %d total (discovered=%d, domain=%d)",
        venue, year, len(all_papers), len(discovered), len(domain_papers),
    )
    return all_papers
