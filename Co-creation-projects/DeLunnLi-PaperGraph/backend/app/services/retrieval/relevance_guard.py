"""Score-based relevance guard before LLM rank (only when candidate pool is large)."""

from __future__ import annotations

from ...core.paper import Paper as LitPaper
from ...core.search.paper_searcher import PaperSearcher, _has_any_author
from ...utils.author_query_match import normalize_author_names
from .method_acronym import is_method_acronym_token, title_matches_method_acronym
from .search_plan import ResolvedSearchPlan

_DEFAULT_THRESHOLD = 40
_MIN_KEEP = 8

_SCORE_TITLE = 5
_SCORE_AUTHOR = 4
_SCORE_VENUE = 3
_SCORE_KEYWORD = 2
_SCORE_YEAR = 1
_SCORE_METHOD_ACRONYM = 6


def apply_relevance_guard(
    candidates: list[LitPaper],
    *,
    plan: ResolvedSearchPlan,
    guard_threshold: int = _DEFAULT_THRESHOLD,
    min_keep: int = _MIN_KEEP,
) -> tuple[list[LitPaper], bool]:
    """候选过多时按相关性打分软过滤；过滤后过少则回退原列表。"""
    if len(candidates) <= guard_threshold:
        return candidates, False

    target_titles = [t.lower() for t in (plan.target_titles or []) if t.strip()]
    keywords = [
        k.lower()
        for k in (plan.keywords or [])
        if len(str(k).strip()) >= 2
    ]
    venues = [v for v in (plan.venues or []) if v.strip()]
    author_phrases = normalize_author_names(plan.authors or [])
    yf, yt = plan.year_from, plan.year_to
    method_acronym = (getattr(plan, "method_acronym", None) or "").strip() or None
    if not method_acronym and len(keywords) == 1 and is_method_acronym_token(keywords[0]):
        method_acronym = keywords[0]

    kept: list[LitPaper] = []
    for p in candidates:
        score = _relevance_score(
            p,
            target_titles=target_titles,
            keywords=keywords,
            venues=venues,
            author_phrases=author_phrases,
            year_from=yf,
            year_to=yt,
            method_acronym=method_acronym,
        )
        if _passes_guard_threshold(
            score,
            plan=plan,
            has_target_titles=bool(target_titles),
            has_strong_constraints=bool(venues or author_phrases or yf is not None),
            method_acronym=method_acronym,
        ):
            kept.append(p)

    if len(kept) < min_keep:
        return candidates, False
    return kept, True


def _passes_guard_threshold(
    score: int,
    *,
    plan: ResolvedSearchPlan,
    has_target_titles: bool,
    has_strong_constraints: bool,
    method_acronym: str | None = None,
) -> bool:
    if method_acronym:
        return score >= _SCORE_METHOD_ACRONYM
    if has_target_titles:
        return score >= _SCORE_TITLE
    if has_strong_constraints:
        return score >= (_SCORE_VENUE + _SCORE_KEYWORD - 2)  # >= 3
    return score >= (_SCORE_KEYWORD)  # >= 2 for broad keyword queries


def _relevance_score(
    p: LitPaper,
    *,
    target_titles: list[str],
    keywords: list[str],
    venues: list[str],
    author_phrases: list[str],
    year_from: int | None,
    year_to: int | None,
    method_acronym: str | None = None,
) -> int:
    score = 0
    title = (getattr(p, "title", None) or "").lower()
    abstract = (getattr(p, "abstract", None) or "").lower()
    journal = (getattr(p, "journal", None) or getattr(p, "venue", None) or "").lower()
    blob = f"{title} {abstract} {journal}"

    if target_titles and any(
        (len(tt) > 8 and (tt in title or title in tt)) for tt in target_titles
    ):
        score += _SCORE_TITLE

    if method_acronym:
        if title_matches_method_acronym(f"{title} {abstract}", method_acronym):
            score += _SCORE_METHOD_ACRONYM
        elif target_titles and any(
            len(tt) >= 12 and (tt in title or title in tt) for tt in target_titles
        ):
            score += _SCORE_METHOD_ACRONYM

    if author_phrases and _has_any_author(p, author_phrases):
        score += _SCORE_AUTHOR

    if venues:
        for v in venues:
            if PaperSearcher._paper_matches_venue_proceedings(p, v) or v.lower() in blob:
                score += _SCORE_VENUE
                break

    if keywords:
        kw_hits = sum(1 for kw in keywords if kw in blob)
        if kw_hits >= 2 or (kw_hits >= 1 and len(keywords) <= 3):
            score += _SCORE_KEYWORD
        elif kw_hits == 1:
            score += 1

    if year_from is not None or year_to is not None:
        try:
            py = int(getattr(p, "year", 0) or 0)
        except (TypeError, ValueError):
            py = 0
        if py:
            in_range = True
            if year_from is not None and py < int(year_from):
                in_range = False
            if year_to is not None and py > int(year_to):
                in_range = False
            if in_range:
                score += _SCORE_YEAR

    return score
