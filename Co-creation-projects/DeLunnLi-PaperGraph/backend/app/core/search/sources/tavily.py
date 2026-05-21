from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _is_noise_title(title: str) -> bool:
    """Reject obvious page/listing titles."""
    t = title.strip()
    if not t or len(t) < 12 or len(t) > 300:
        return True
    low = t.lower()
    if low in {"proceedings", "list of proceedings", "accepted papers", "neurips", "nips"}:
        return True
    if re.match(r"(?i)^(cvpr|iccv|eccv)\s*\d{4}\s*$", t):
        return True
    if re.search(r"(?i)open access repository", t):
        return True
    return False


async def _llm_filter_relevant(
    papers: list[dict[str, Any]], query: str, venue: str, limit: int,
) -> list[dict[str, Any]]:
    """Keep the most query-relevant extracted papers."""
    if not papers or len(papers) <= limit:
        return papers
    try:
        from ....services.llm.llm_service import get_llm, is_llm_configured
        from ....services.llm.agent_runtime import run_json_task

        if not is_llm_configured():
            return papers[:limit]
    except Exception:
        return papers[:limit]

    titles = [f"[{i}] {p['title']}" for i, p in enumerate(papers)]
    prompt = (
        f"用户搜索：{query}\n"
        f"会议：{venue}\n"
        "以下是论文标题列表。选出与搜索主题最相关的论文（最多" + str(limit) + "篇）。\n"
        "输出 JSON：{\"relevant\":[0,3,5,...]}（保留的索引号，从0开始，按相关度降序）\n\n"
        + "\n".join(titles)
    )
    try:
        data = await asyncio.to_thread(
            lambda: run_json_task(
                task_name="paper_relevance_filter",
                agent_name="papergraph_relevance_filter",
                llm=get_llm(),
                system_prompt="你是学术论文相关性判断器。严格筛选，只输出合法JSON。",
                user_prompt=prompt,
                timeout_sec=8,
                retries=0,
                default={"relevant": list(range(min(limit, len(papers))))},
            )
        )
    except Exception:
        return papers[:limit]
    indices = data.get("relevant") if isinstance(data, dict) else list(range(len(papers)))
    if not isinstance(indices, list):
        return papers[:limit]
    result = [papers[i] for i in indices if isinstance(i, int) and 0 <= i < len(papers)]
    return result[:limit] if result else papers[:limit]


def _clean_abstract(text: str) -> str:
    """Remove citation/HTML boilerplate from snippets."""
    t = (text or "").strip()
    if not t:
        return ""
    t = re.sub(r"@\w+\{[^}]*\}?", "", t, flags=re.S)
    # BibTeX field fragments can appear without closing braces.
    t = re.sub(r",?\s*\b(author|title|booktitle|journal|year|pages|volume|number|publisher|editor|series|address|month|note|url|doi|isbn)\s*=\s*\{[^}]*\}?,?", "", t, flags=re.I)
    t = re.sub(r"These (?:CVPR|ICCV|ECCV)\s*(?:20\d{2})?\s*papers are the Open Access versions?, provided by the Computer Vision Foundation\.?", "", t, flags=re.I)
    t = re.sub(r"Except for the watermark,? they are identical to the accepted versions?;? the final published version of the proceedings is available on IEEE Xplore\.?", "", t, flags=re.I)
    t = re.sub(r"All persons copying this information are expected to adhere to the terms and constraints invoked by each author'?s? copyright\.?", "", t, flags=re.I)
    t = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\(?(?:CVPR|ICCV|ECCV|NeurIPS|ICLR|ICML|AAAI|IJCAI|ACL|EMNLP|NAACL|SIGIR|KDD)\)?\s*(?:Workshops?|Conference|Proceedings)?,?\s*(?:19|20)\d{2},?\s*pp?\.?\s*[\d\-–]+\.?", "", t, flags=re.I)
    t = re.sub(r"\bpp\.\s*[\d\-–]+\b", "", t)
    t = re.sub(r"\bvol\.?\s*\d+\b", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&#?\w+;", " ", t)
    t = re.sub(r"\{\s*\}", "", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r",\s*,", ",", t)
    t = t.strip(" ,;:")
    if not t or len(t) < 30:
        return ""
    if re.match(r"(?i)(all persons copying|these \w+ papers are|except for the watermark)", t):
        return ""
    return t[:800] if len(t) > 800 else t


async def _llm_extract_papers_from_raw(
    raw_text: str,
    *,
    query: str,
    venue: str = "",
    year: Any = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Extract paper records from raw Tavily page text."""
    try:
        from ....services.llm.llm_service import get_llm, is_llm_configured
        from ....services.llm.agent_runtime import run_json_task

        if not is_llm_configured():
            return []
    except Exception:
        return []

    cleaned = re.sub(r"<[^>]+>", " ", raw_text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:14000]
    if len(cleaned) < 100:
        return []

    prompt = (
        "从下面的网页文本中提取学术论文的标题、作者和摘要。\n"
        "文本中可能混有 BibTeX 引用、版权声明等。只抽取真实论文信息。\n"
        "标题是研究成果名称，摘要是一段连续的学术描述文字。\n"
        "不要抽取：论文集名称、导航链接、Workshop/Challenge/Tutorial 论文、\n"
        "版权声明、BibTeX 字段值、残缺文字。\n"
        f"用户搜索主题：{query}。只提取与主题相关的论文。\n"
        f"会议：{venue or '未知'}，年份：{year or '未知'}，最多 {limit} 篇。\n"
        '输出 JSON：{"papers":[{"title":"...","authors":["..."],"abstract":"..."}]}\n\n'
        f"页面文本：\n{cleaned}"
    )
    try:
        data = await asyncio.to_thread(
            lambda: run_json_task(
                task_name="tavily_page_extract",
                agent_name="papergraph_tavily_extractor",
                llm=get_llm(),
                system_prompt="你是严格的信息抽取器。只输出合法 JSON，不得编造文本中不存在的论文。",
                user_prompt=prompt,
                timeout_sec=15,
                retries=0,
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
        title = str(it.get("title") or "").strip()
        title = re.sub(r"^\s*\[PDF\]\s*", "", title, flags=re.I)
        title = re.sub(r"^\s*#+\s*", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) < 8 or len(title) > 300:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        authors = it.get("authors") if isinstance(it.get("authors"), list) else []
        out.append({"title": title, "authors": [str(a)[:120] for a in authors[:12] if str(a).strip()]})
        if len(out) >= limit:
            break

    # Keep LLM extraction broad, then trim by relevance.
    if len(out) > limit // 2:
        out = await _llm_filter_relevant(out, query, venue, limit)
    return out


async def _tavily_proceedings_fetch(
    *,
    api_key: str,
    query: str,
    domains: list[str] | None,
    max_results: int,
    httpx_client: Any,
    searcher: Any,
    year: Any,
    journal: str = "",
) -> list:
    from ....services.retrieval.web_presearch import tavily_search_async as _tv

    n = max(1, min(10, int(max_results or 5)))
    items = await _tv(
        api_key=api_key, query=query, max_results=n,
        include_domains=domains, httpx_client=httpx_client,
    )
    if not items and domains:
        items = await _tv(
            api_key=api_key, query=query, max_results=n,
            include_domains=None, httpx_client=httpx_client,
        )

    papers: list = []
    for it in items or []:
        title = str(it.get("title") or "").strip()
        link = str(it.get("link") or it.get("url") or "").strip()
        raw = str(it.get("raw_content") or "")
        snippet = str(it.get("content") or it.get("snippet") or "")

        llm_papers = await _llm_extract_papers_from_raw(
            raw, query=query or "", venue=journal, year=year, limit=max_results,
        )
        for lp in llm_papers:
            t = lp["title"].strip()
            if _is_noise_title(t):
                continue
            tl = t.lower()
            if any(w in tl for w in ("workshop", "challenge", "tutorial", "demo track", "competition")):
                continue
            abs_text = _clean_abstract(lp.get("abstract", ""))
            if not abs_text:
                abs_text = _clean_abstract(snippet)
            papers.append(
                searcher._make_paper(
                    title=t,
                    authors=lp.get("authors", []),
                    abstract=abs_text,
                    source_url=link,
                    source="tavily",
                    journal=journal or None,
                    year=int(year) if year else None,
                )
            )
        # Empty extraction usually means the page is not a paper listing.
    return papers


async def search_tavily_proceedings(
    searcher: Any,
    query: str,
    venue: str,
    year: Any,
    max_results: int,
    *,
    venue_browse: bool = False,
) -> list:
    """会议官网召回：优先配置域名；不足则 Tavily 自动发现站点再搜对应年份论文。"""
    try:
        from ....settings import get_settings as _gs
        from ....services.retrieval.tavily_venue_config import tavily_include_domains_for_venue as _td
        from ....services.retrieval.proceedings_discovery import discover_proceedings_domains

        _ak = getattr(_gs(), "tavily_api_key", "").strip()
        if not _ak:
            return []

        _client = await searcher._ensure_async_client()
        year_i = int(year) if year is not None else None
        topic = (query or "").strip()
        if topic.lower() == (venue or "").strip().lower():
            topic = ""
        base_q = f"{venue} {year_i} proceedings {topic}".strip() if year_i else f"{venue} proceedings {topic}".strip()
        _q = base_q.strip() or f"{venue} {year_i or ''} papers".strip()

        static_dom = list(_td(venue) or [])
        domains = static_dom[:3]

        if not domains:
            domains = await discover_proceedings_domains(
                api_key=_ak, venue=venue, year=year_i,
                httpx_client=_client, max_domains=3,
            )

        journal = venue.strip().upper()
        papers: list = []
        if venue_browse:
            browse_queries = [
                f"{venue} {year_i} main conference accepted papers",
                f"{venue} {year_i} oral papers proceedings",
                f"{venue} {year_i} conference papers list",
            ]
            seen_titles: set[str] = set()
            for bq in browse_queries:
                batch = await _tavily_proceedings_fetch(
                    api_key=_ak, query=bq, domains=domains or None,
                    max_results=10, httpx_client=_client,
                    searcher=searcher, year=year, journal=journal,
                )
                for p in batch:
                    t = (getattr(p, "title", None) or "").strip().lower()
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        papers.append(p)
                if len(papers) >= max(20, int(max_results)):
                    break
        else:
            seen_titles: set[str] = set()
            for tq in [base_q]:
                batch = await _tavily_proceedings_fetch(
                    api_key=_ak, query=tq, domains=domains or None,
                    max_results=max_results, httpx_client=_client,
                    searcher=searcher, year=year, journal=journal,
                )
                for p in batch:
                    t = (getattr(p, "title", None) or "").strip().lower()
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        papers.append(p)

        if not papers and not domains:
            papers = await _tavily_proceedings_fetch(
                api_key=_ak,
                query=f"{venue} {year_i or ''} official conference papers accepted".strip(),
                domains=None, max_results=max_results,
                httpx_client=_client, searcher=searcher, year=year, journal=journal,
            )

        if not papers:
            discovered = await discover_proceedings_domains(
                api_key=_ak, venue=venue, year=year_i,
                httpx_client=_client, max_domains=3,
            )
            if discovered:
                extra = await _tavily_proceedings_fetch(
                    api_key=_ak, query=_q, domains=discovered,
                    max_results=max_results, httpx_client=_client,
                    searcher=searcher, year=year, journal=journal,
                )
                if len(extra) > len(papers):
                    papers = extra
                    logger.info(
                        "[tavily_proceedings] venue=%s year=%s rediscovered domains=%s -> %d papers",
                        venue, year_i, discovered, len(papers),
                    )

        searcher._bump_stat("total_results", len(papers))
        return papers
    except Exception as e:
        logger.warning("[tavily_proceedings] failed venue=%s year=%s: %s", venue, year, e)
        return []
