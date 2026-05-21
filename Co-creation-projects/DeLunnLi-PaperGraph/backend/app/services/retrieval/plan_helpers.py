"""Derived helpers for ResolvedSearchPlan."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .method_acronym import resolve_method_acronym


def _venues(plan: "ResolvedSearchPlan") -> list[str]:
    return [str(v).strip() for v in (plan.venues or []) if str(v).strip()]


def _keywords(plan: "ResolvedSearchPlan") -> list[str]:
    return [str(k).strip() for k in (plan.keywords or []) if str(k).strip()]

if TYPE_CHECKING:
    from .recall_context import RecallContext
    from .search_plan import ResolvedSearchPlan


def primary_venue(plan: "ResolvedSearchPlan") -> str | None:
    v = _venues(plan)
    return v[0] if v else None


def method_acronym_for(plan: "ResolvedSearchPlan", ctx: "RecallContext | None" = None) -> str:
    if (plan.method_acronym or "").strip():
        return str(plan.method_acronym).strip()
    if ctx is not None:
        return str(ctx.search_kwargs.get("method_acronym") or "").strip()
    return ""


def is_pinned_single_year(plan: "ResolvedSearchPlan") -> bool:
    yf, yt = plan.year_from, plan.year_to
    return bool(_venues(plan) and isinstance(yf, int) and isinstance(yt, int) and yf == yt)


def is_strict_venue_match(plan: "ResolvedSearchPlan") -> bool:
    return is_pinned_single_year(plan) and bool(plan.main_conference_proceedings_only)


def use_venue_proceedings_journal(plan: "ResolvedSearchPlan") -> bool:
    return bool(_venues(plan))


def pinned_research_topic(plan: "ResolvedSearchPlan") -> str:
    """Search topic after removing pinned venue/year terms."""
    from ...core.search.normalize import extract_pinned_topic_terms

    venue = primary_venue(plan) or ""
    year = plan.year_from if isinstance(plan.year_from, int) else None
    return extract_pinned_topic_terms(
        query=plan.query or "",
        merged_kw=list(plan.keywords or []),
        venue=venue,
        year=year,
    ).strip()


def is_venue_browse_plan(plan: "ResolvedSearchPlan") -> bool:
    """True for pure venue+year browsing."""
    if not is_pinned_single_year(plan) or not plan.main_conference_proceedings_only or not _venues(plan):
        return False
    if method_acronym_for(plan) or resolve_method_acronym(plan.query or "", _keywords(plan)):
        return False
    if plan.target_titles or plan.authors:
        return False
    return not bool(pinned_research_topic(plan))


def effective_max_results(plan: "ResolvedSearchPlan", requested: int) -> int:
    return max(int(requested), 30) if is_venue_browse_plan(plan) else int(requested)


def effective_recall_max_candidates(plan: "ResolvedSearchPlan", current: int) -> int:
    cur = int(current or 24)
    return max(cur, 24) if is_venue_browse_plan(plan) else cur


def tavily_configured() -> bool:
    try:
        from ...settings import get_settings

        return bool(str(getattr(get_settings(), "tavily_api_key", "") or "").strip())
    except Exception:
        return False


def should_supplement_from_proceedings_site(plan: "ResolvedSearchPlan") -> bool:
    """Venue searches can use proceedings supplement when Tavily is configured."""
    return (
        bool(_venues(plan))
        and tavily_configured()
    )


def should_supplement_from_intent_dict(intent: dict[str, Any]) -> bool:
    venues = [str(v).strip() for v in (intent.get("venues") or []) if str(v).strip()]
    if not venues:
        return False
    yf, yt = intent.get("year_from"), intent.get("year_to")
    try:
        pinned = yf is not None and yt is not None and int(yf) == int(yt)
    except (TypeError, ValueError):
        pinned = False
    return pinned and bool(intent.get("main_conference_proceedings_only")) and tavily_configured()
