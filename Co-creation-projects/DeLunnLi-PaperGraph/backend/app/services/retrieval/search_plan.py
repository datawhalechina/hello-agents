"""Resolved search plan + FallbackPolicy — single source of truth between intent and pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from .search_recipe import SearchRecipe, finalize_plan_recipe


@dataclass
class FallbackPolicy:
    allow_arxiv_only: bool = True
    reason: str = "auto"


@dataclass
class ResolvedSearchPlan:
    """All search parameters resolved once, used by pipeline. No LLM calls in retrieval layer."""
    query: str = ""
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    venues: list[str] = field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    sources: list[str] = field(default_factory=list)
    sort: str = "relevance"
    ranking_profile: str = "accuracy"
    use_llm_rank: bool = True
    recall_max_candidates: int = 24
    target_titles: list[str] = field(default_factory=list)
    arxiv_id_list: list[str] = field(default_factory=list)
    main_conference_proceedings_only: bool = False
    raw_user_message: str = ""
    wants_recent: bool = False
    wants_classic: bool = False
    fallback: FallbackPolicy = field(default_factory=FallbackPolicy)
    use_tavily: bool = False
    max_results: int = 10
    recipe: SearchRecipe = SearchRecipe.GENERAL
    method_acronym: str | None = None

    @classmethod
    def from_search_intent(cls, intent) -> "ResolvedSearchPlan":
        plan = cls(
            query=(intent.query or "").strip()[:500],
            keywords=list(intent.keywords or [])[:16],
            authors=list(getattr(intent, "authors", []) or [])[:8],
            venues=list(intent.venues or []),
            year_from=_norm_year(intent.year_from),
            year_to=_norm_year(intent.year_to),
            sources=_resolve_sources(intent),
            sort=_resolve_sort(intent),
            ranking_profile=_resolve_profile(intent),
            use_llm_rank=bool(getattr(intent, "use_llm_rank", True)),
            recall_max_candidates=_resolve_recall_max(intent),
            target_titles=list(getattr(intent, "target_titles", []) or [])[:6],
            arxiv_id_list=list(getattr(intent, "arxiv_id_list", []) or [])[:16],
            main_conference_proceedings_only=bool(getattr(intent, "main_conference_proceedings_only", False)),
            raw_user_message=(getattr(intent, "raw_user_message", "") or "")[:3200],
            wants_recent=bool(getattr(intent, "wants_recent", False)),
            wants_classic=bool(getattr(intent, "wants_classic", False)),
            use_tavily=_resolve_use_tavily(intent),
            max_results=max(5, min(30, int(getattr(intent, "max_results", 10) or 10))),
        )
        return _finalize_plan_for_retrieval(plan)


def _finalize_plan_for_retrieval(plan: ResolvedSearchPlan) -> ResolvedSearchPlan:
    """RECIPE_RULES 判定并应用策略；派生状态见 plan_helpers。"""
    return finalize_plan_recipe(plan)


def _resolve_sort(intent) -> str:
    rk = getattr(intent, "ranking_strategy", None)
    if rk == "date":
        return "date"
    if rk == "relevance":
        return "relevance"
    if getattr(intent, "wants_recent", False):
        return "date"
    if getattr(intent, "wants_classic", False):
        return "relevance"
    return str(getattr(intent, "sort", "relevance") or "relevance")


def _resolve_profile(intent) -> str:
    if getattr(intent, "wants_classic", False):
        return "classic"
    if getattr(intent, "wants_recent", False):
        return "novelty"
    return "accuracy"


def _resolve_sources(intent) -> list[str]:
    llm_src = getattr(intent, "sources", []) or []
    allowed = {"arxiv", "dblp", "openalex"}
    if llm_src:
        resolved = [s for s in llm_src if s in allowed]
        if resolved:
            return resolved
    return ["arxiv", "dblp", "openalex"]


def _resolve_use_tavily(intent) -> bool:
    llm_src = [str(s).strip().lower() for s in (getattr(intent, "sources", []) or [])]
    return "tavily" in llm_src or bool(getattr(intent, "use_tavily_presearch", False))


def _resolve_recall_max(intent) -> int:
    try:
        from ...settings import get_settings

        cap = int(get_settings().papergraph_recall_max_candidates)
    except Exception:
        cap = 24
    raw = int(getattr(intent, "rerank_recall_max", 24) or 24)
    return max(8, min(cap, raw))


def _norm_year(y) -> int | None:
    if y is None:
        return None
    try:
        yi = int(y)
        return yi if 1900 <= yi <= 2100 else None
    except (TypeError, ValueError):
        return None
