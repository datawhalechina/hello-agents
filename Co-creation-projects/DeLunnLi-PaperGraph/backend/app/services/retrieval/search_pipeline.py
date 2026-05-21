from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from typing import Any

import anyio

from ...core.paper import Paper as LitPaper
from ...settings import get_settings
from .paper_filters import should_exclude_main_conference_paper
from .paper_ranker import LlmPaperRanker, RankedPaper
from .pipeline_runtime import SearchRuntimeConfig
from .plan_helpers import is_venue_browse_plan, method_acronym_for, primary_venue
from .recall_context import RecallContext, build_recall_context, enrich_recall_context_from_tavily
from .recall_jobs import build_recall_jobs, dedupe_papers, execute_recall_jobs, merge_candidates
from .relevance_guard import apply_relevance_guard
from .search_plan import ResolvedSearchPlan


@dataclass
class SearchPipelineResult:
    effective_query: str
    total_candidates: int
    ranking_method: str
    ranked: list[RankedPaper]
    metadata: dict[str, Any]
    plan: dict[str, Any]
    plan_explanation: str


def _merge_pinned_papers(candidates: list[LitPaper], pinned_ids: list[str], searcher: Any) -> list[LitPaper]:
    if not pinned_ids:
        return candidates
    try:
        if hasattr(searcher, "search_by_arxiv_ids"):
            pinned = searcher.search_by_arxiv_ids(pinned_ids)
        elif hasattr(searcher, "search_async"):
            loop = asyncio.new_event_loop()
            try:
                pinned = loop.run_until_complete(
                    searcher.search_async(
                        "",
                        sources=["arxiv"],
                        arxiv_id_list=pinned_ids,
                        max_results=len(pinned_ids) * 2,
                    )
                )
            finally:
                loop.close()
        else:
            pinned = searcher.search(
                "",
                sources=["arxiv"],
                arxiv_id_list=pinned_ids,
                max_results=len(pinned_ids) * 2,
            )
        pinned = pinned or []
    except Exception:
        pinned = []
    return merge_candidates(candidates, list(pinned), "prepend")


def _merge_target_titles(plan: ResolvedSearchPlan, ctx: RecallContext) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in list(plan.target_titles or []) + list(ctx.canonical_titles or []):
        tl = (t or "").strip()
        if tl and tl.lower() not in seen:
            seen.add(tl.lower())
            out.append(tl)
    return out[:6]


def normalize_and_filter_candidates(
    candidates: list[LitPaper],
    *,
    plan: ResolvedSearchPlan,
    ctx: RecallContext,
    recall_cap: int,
    meta: dict[str, Any],
) -> list[LitPaper]:
    venue = primary_venue(plan)
    ma = method_acronym_for(plan, ctx) or None
    candidates = dedupe_papers(candidates)

    if ma:
        from .method_acronym import paper_matches_method_query

        narrowed = [
            p
            for p in candidates
            if paper_matches_method_query(
                p,
                ma,
                canonical_titles=ctx.canonical_titles,
                pinned_arxiv_ids=ctx.pinned_arxiv_ids,
                venue=venue,
            )
        ]
        if narrowed:
            candidates = narrowed

    guard_threshold = max(36, recall_cap + 8)
    if ma:
        guard_threshold = max(10, min(guard_threshold, len(candidates) + 2))
    if not is_venue_browse_plan(plan):
        candidates, guard_applied = apply_relevance_guard(candidates, plan=plan, guard_threshold=guard_threshold)
        if guard_applied:
            meta["relevance_guard"] = True

    if plan.main_conference_proceedings_only and venue:
        pin_y = plan.year_from if plan.year_from == plan.year_to else None
        # Only require strong venue signal if we actually found venue-verified papers
        from .paper_filters import has_strong_main_conference_venue_signal
        venue_verified_count = sum(1 for p in candidates if has_strong_main_conference_venue_signal(p, venue))
        require_venue_signal = venue_verified_count >= 3
        candidates = [
            p
            for p in candidates
            if not should_exclude_main_conference_paper(
                p,
                venue,
                pinned_year=pin_y,
                require_venue_signal=require_venue_signal,
            )
        ]
    return candidates


async def rank_candidates(
    candidates: list[LitPaper],
    *,
    plan: ResolvedSearchPlan,
    ctx: RecallContext,
    runtime: SearchRuntimeConfig,
    meta: dict[str, Any],
) -> tuple[list[RankedPaper], str, dict[str, Any]]:
    if not candidates:
        return [], "recall_only", {}
    if not plan.use_llm_rank:
        return [RankedPaper(paper=p) for p in candidates[: runtime.max_results]], "recall_only", {}

    venue = primary_venue(plan)
    ranker = LlmPaperRanker(recall_max=runtime.recall_max, fine_top_k=runtime.max_results)
    prefer_rec = (plan.sort or "").strip().lower() == "date" or bool(plan.year_from) or bool(venue)
    try:
        with anyio.fail_after(runtime.rank_wall):
            ranked, ranking_metadata = await anyio.to_thread.run_sync(
                lambda: ranker.rank(
                    candidates,
                    ctx.rank_query,
                    runtime.max_results,
                    ranking_profile=ctx.ranking_profile,
                    target_venue=venue,
                    target_titles=_merge_target_titles(plan, ctx),
                    authors=list(plan.authors or []),
                    venues=list(plan.venues or []),
                    year_from=plan.year_from,
                    year_to=plan.year_to,
                    sort=plan.sort,
                    prefer_recency=prefer_rec,
                    main_conference_proceedings_only=bool(plan.main_conference_proceedings_only),
                    intent_source_message=ctx.intent_source_message,
                    method_acronym=ctx.search_kwargs.get("method_acronym"),
                )
            )
        return ranked, ranking_metadata.get("ranking_method", "llm_rank"), ranking_metadata
    except TimeoutError:
        meta["ranking_timeout"] = True
        from .paper_ranker import _papers_to_ranked_pool

        pool = _papers_to_ranked_pool(candidates, cap=runtime.recall_max, prefer_recency=prefer_rec)
        return pool[: runtime.max_results], "recall_fallback_timeout", {}


async def run_search_pipeline_async(
    *,
    searcher: Any,
    plan: ResolvedSearchPlan,
    max_results: int | None = None,
) -> SearchPipelineResult:
    runtime = SearchRuntimeConfig.from_settings(get_settings(), plan, max_results)
    ctx = await enrich_recall_context_from_tavily(build_recall_context(plan), plan)

    meta: dict[str, Any] = {
        "ranking_profile": ctx.ranking_profile,
        "source_plan": ctx.source_plan,
        "recall_context": {
            "effective_query": ctx.effective_query[:200],
            "rank_query": ctx.rank_query[:200],
            "merged_keywords": ctx.merged_keywords[:12],
        },
        "search_recipe": plan.recipe.value,
    }
    fallbacks: list[dict[str, Any]] = []

    constraint_kwargs = {**ctx.search_kwargs, "sort": plan.sort or ctx.search_kwargs.get("sort") or "relevance"}
    jobs = build_recall_jobs(plan, ctx, runtime=runtime, constraint_kwargs=constraint_kwargs)
    candidates = await execute_recall_jobs(
        searcher, jobs, plan=plan, ctx=ctx, runtime=runtime, meta=meta, fallbacks=fallbacks
    )

    pinned_ids = list(ctx.pinned_arxiv_ids or [])
    if pinned_ids and searcher is not None:
        try:
            with anyio.fail_after(3.0):
                candidates = await anyio.to_thread.run_sync(
                    _merge_pinned_papers, candidates, pinned_ids, searcher
                )
        except TimeoutError:
            pass

    candidates = normalize_and_filter_candidates(
        candidates, plan=plan, ctx=ctx, recall_cap=runtime.recall_cap, meta=meta
    )
    ranked, ranking_method, ranking_metadata = await rank_candidates(
        candidates, plan=plan, ctx=ctx, runtime=runtime, meta=meta
    )

    if not candidates and plan.fallback.allow_arxiv_only:
        fallbacks.append({"type": "arxiv_only", "reason": "no_candidates_after_recall"})

    sc = Counter(getattr(p, "source", "unknown") or "unknown" for p in candidates)
    rsc = Counter(getattr(rp.paper, "source", "unknown") or "unknown" for rp in ranked)
    metadata = {
        "tavily_enabled": plan.use_tavily,
        "tavily_keywords_count": len(ctx.tavily_keywords),
        "anchor_title": ctx.canonical_titles[0] if ctx.canonical_titles else None,
        "anchor_arxiv_ids": pinned_ids,
        "pinned_arxiv_ids": pinned_ids,
        "fallbacks": fallbacks,
        "candidates_by_source": dict(sc),
        "ranked_by_source": dict(rsc),
        "deduped_total": len(candidates),
        "final_ranked": len(ranked),
        **meta,
    }
    if ranking_metadata:
        metadata["ranking"] = ranking_metadata

    return SearchPipelineResult(
        effective_query=ctx.effective_query,
        total_candidates=len(candidates),
        ranking_method=ranking_method,
        ranked=ranked,
        metadata=metadata,
        plan={
            "llm_keywords": ctx.merged_keywords,
            "tavily_keywords": ctx.tavily_keywords,
            "canonical_titles": ctx.canonical_titles,
            "recipe": plan.recipe.value,
        },
        plan_explanation="",
    )
