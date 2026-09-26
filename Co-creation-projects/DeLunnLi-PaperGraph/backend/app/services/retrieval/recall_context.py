"""Plan → RecallContext：查询词、约束 kwargs、召回源。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ...core.search import sanitize_pinned_topic_keywords
from ...utils.author_query_match import pick_primary_english_author_for_query
from .plan_helpers import (
    is_pinned_single_year,
    is_strict_venue_match,
    is_venue_browse_plan,
    method_acronym_for,
    primary_venue,
    use_venue_proceedings_journal,
)
from .search_plan import ResolvedSearchPlan
from .search_recipe import SearchRecipe

_ACADEMIC_SOURCES = frozenset({"arxiv", "dblp", "openalex"})


@dataclass
class RecallContext:
    effective_query: str
    rank_query: str
    merged_keywords: list[str] = field(default_factory=list)
    search_kwargs: dict[str, Any] = field(default_factory=dict)
    ranking_profile: str = "accuracy"
    recall_sources: list[str] = field(default_factory=list)
    intent_source_message: str = ""
    pinned_arxiv_ids: list[str] = field(default_factory=list)
    tavily_keywords: list[str] = field(default_factory=list)
    canonical_titles: list[str] = field(default_factory=list)
    source_plan: dict[str, Any] = field(default_factory=dict)


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _latin_keywords(keywords: list[str]) -> list[str]:
    out: list[str] = []
    for kw in keywords:
        t = str(kw).strip()
        if not t or not re.search(r"[A-Za-z]", t):
            continue
        if _has_cjk(t) and sum(1 for ch in t if ord(ch) > 127) > max(2, len(t) // 3):
            continue
        out.append(t)
    return out[:8]


def _resolve_query_terms(plan: ResolvedSearchPlan) -> tuple[str, str, list[str], list[str], list[str]]:
    raw_msg = (plan.raw_user_message or plan.query or "").strip()
    query = (plan.query or "").strip()
    target_titles = [str(t).strip() for t in (plan.target_titles or []) if str(t).strip()][:6]
    authors = [str(a).strip() for a in (plan.authors or []) if str(a).strip()][:8]
    author_low = {a.lower() for a in authors}

    keywords: list[str] = []
    for k in plan.keywords or []:
        t = str(k).strip()
        if not t:
            continue
        tl = t.lower()
        if tl in author_low or any(a in tl for a in author_low if len(a) > 2):
            continue
        keywords.append(t)

    effective_query = query
    rank_query = query or raw_msg
    merged_keywords = list(keywords)

    if target_titles:
        effective_query = target_titles[0]
        rank_query = target_titles[0]
        seen: set[str] = set()
        merged_keywords = []
        for t in target_titles + keywords:
            tl = t.lower()
            if tl not in seen:
                merged_keywords.append(t)
                seen.add(tl)
        merged_keywords = merged_keywords[:16]
    elif authors and not target_titles:
        eng = pick_primary_english_author_for_query(authors) or query
        effective_query = (eng or query).strip()
        rank_query = raw_msg or effective_query
    elif _has_cjk(query):
        latin = _latin_keywords(keywords)
        effective_query = (" ".join(latin)[:200].strip() if latin else (keywords[0] if keywords else query))
        rank_query = raw_msg or query
    elif not effective_query and keywords:
        effective_query = keywords[0]
        rank_query = raw_msg or effective_query

    effective_query, rank_query, merged_keywords = _apply_venue_browse_query_defaults(
        plan,
        effective_query=effective_query,
        rank_query=rank_query,
        merged_keywords=merged_keywords,
    )
    return effective_query, rank_query, merged_keywords, target_titles, authors


def _apply_venue_browse_query_defaults(
    plan: ResolvedSearchPlan,
    *,
    effective_query: str,
    rank_query: str,
    merged_keywords: list[str],
) -> tuple[str, str, list[str]]:
    if not is_venue_browse_plan(plan):
        return effective_query, rank_query, merged_keywords
    venue = primary_venue(plan) or ""
    year = plan.year_from
    rank_query = (plan.raw_user_message or "").strip() or f"{venue} {year or ''}".strip()
    return "", rank_query, []


def build_recall_context(plan: ResolvedSearchPlan) -> RecallContext:
    raw_msg = (plan.raw_user_message or plan.query or "").strip()
    effective_query, rank_query, merged_keywords, target_titles, authors = _resolve_query_terms(plan)

    ma = method_acronym_for(plan)
    if ma and plan.recipe == SearchRecipe.METHOD and not target_titles:
        merged_keywords = [ma]
        effective_query = ma
        rank_query = raw_msg or f"{ma} {primary_venue(plan) or ''}".strip()

    ranking_profile = str(plan.ranking_profile or "accuracy").strip().lower()
    if ranking_profile not in ("accuracy", "novelty", "classic"):
        ranking_profile = "accuracy"
    if target_titles or (ma and plan.recipe == SearchRecipe.METHOD):
        ranking_profile = "classic"

    recall_sources = [
        str(s).strip().lower()
        for s in (plan.sources or [])
        if str(s).strip().lower() in _ACADEMIC_SOURCES
    ] or ["arxiv", "dblp", "openalex"]

    venue = primary_venue(plan)
    search_kwargs: dict[str, Any] = {
        "llm_keywords": merged_keywords[:8],
        "target_titles": target_titles,
        "authors": authors,
        "venue": venue,
        "year_from": plan.year_from,
        "year_to": plan.year_to,
        "main_conference_proceedings_only": bool(plan.main_conference_proceedings_only),
        "venue_proceedings_journal": use_venue_proceedings_journal(plan),
        "strict_venue_match": is_strict_venue_match(plan),
        "wants_recent": bool(plan.wants_recent),
        "sort": plan.sort or "relevance",
        "arxiv_id_list": list(plan.arxiv_id_list or [])[:16],
    }

    if is_pinned_single_year(plan) and venue:
        search_kwargs["pinned_topic_terms"] = sanitize_pinned_topic_keywords(
            list(merged_keywords) + list(plan.keywords or [])
        )
    if is_pinned_single_year(plan) and plan.main_conference_proceedings_only and venue:
        search_kwargs["venue_fallback_if_empty"] = False
        search_kwargs["openalex_relax_host_venue_on_empty"] = False
    if is_venue_browse_plan(plan):
        search_kwargs["venue_browse"] = True
    if ma:
        search_kwargs.update(method_acronym=ma, llm_keywords=[ma], dblp_use_llm_keywords=False)

    pinned = [str(x).strip() for x in (plan.arxiv_id_list or []) if str(x).strip()]

    return RecallContext(
        effective_query=effective_query,
        rank_query=rank_query,
        merged_keywords=merged_keywords,
        search_kwargs=search_kwargs,
        ranking_profile=ranking_profile,
        recall_sources=recall_sources,
        intent_source_message=raw_msg,
        pinned_arxiv_ids=pinned,
        source_plan={
            "sources": recall_sources,
            "effective_query": effective_query[:200],
            "rank_query": rank_query[:200],
            "ranking_profile": ranking_profile,
            "recipe": plan.recipe.value,
        },
    )


async def enrich_recall_context_from_tavily(ctx: RecallContext, plan: ResolvedSearchPlan) -> RecallContext:
    if not plan.use_tavily:
        return ctx
    try:
        from ...settings import get_settings
        from .web_presearch import extract_anchor_ids, pick_anchor_title, tavily_search_async

        api_key = str(getattr(get_settings(), "tavily_api_key", "") or "").strip()
        if not api_key:
            return ctx

        ma = method_acronym_for(plan, ctx)
        venue = primary_venue(plan) or ""
        tq = (f"{ma} {venue} paper".strip() if ma and venue else (ctx.effective_query or ctx.rank_query or plan.query or "")).strip()
        if not tq:
            return ctx

        items = await tavily_search_async(api_key=api_key, query=tq[:400], max_results=5)
        anchors = extract_anchor_ids(items or [])

        arxiv_ids = list(ctx.pinned_arxiv_ids)
        for aid in anchors.get("arxiv_ids") or []:
            if aid and aid not in arxiv_ids:
                arxiv_ids.append(aid)
        ctx.pinned_arxiv_ids = arxiv_ids[:16]

        if title := pick_anchor_title(items or []):
            if len(title) >= 12:
                ctx.canonical_titles.insert(0, title[:240])
        for it in items or []:
            t = str(it.get("title") or "").strip()
            if len(t) >= 12 and t.lower() not in {x.lower() for x in ctx.canonical_titles}:
                if not any(x in t.lower() for x in ("home", "login", "index of", "schedule")):
                    ctx.canonical_titles.append(t[:240])

        ctx.search_kwargs["arxiv_id_list"] = ctx.pinned_arxiv_ids
        tt = list(ctx.search_kwargs.get("target_titles") or [])
        for title in ctx.canonical_titles:
            if title and title not in tt:
                tt.append(title)
        if tt:
            ctx.search_kwargs["target_titles"] = tt[:6]
        if dois := anchors.get("dois"):
            ctx.search_kwargs["dois"] = dois[:5]
        ctx.tavily_keywords = list(ctx.canonical_titles)[:4]
    except Exception:
        pass
    return ctx
