from __future__ import annotations

from typing import Any, Callable, TypeVar

from ....utils.author_query_match import normalize_author_names
from ....utils.common import text_has_cjk
from ..normalize import _score_name_match
from ..paper_searcher import _sanitize_author_list_for_query

T = TypeVar("T")


def json_api_headers(searcher, *, accept: str = "application/json") -> dict[str, str]:
    return {"User-Agent": searcher._user_agent(), "Accept": accept}


def normalize_query_authors(query: str, raw_authors: Any) -> list[str]:
    if isinstance(raw_authors, str):
        raw_authors = [raw_authors]
    return normalize_author_names(
        [
            str(x).strip()
            for x in (_sanitize_author_list_for_query(query, raw_authors or []) or [])
            if str(x).strip()
        ]
    )


def author_names_for_api(names: list[str]) -> list[str]:
    latin = [n for n in names if n.strip() and not text_has_cjk(n)]
    return latin or [n for n in names if n.strip()]


def pick_best_name_match(
    items: list[T],
    query_name: str,
    *,
    display_name: Callable[[T], str],
    score_bonus: Callable[[T, int], int] | None = None,
) -> tuple[T | None, int]:
    best: T | None = None
    best_score = -1
    for it in items:
        try:
            dn = display_name(it)
            if not dn:
                continue
            score = _score_name_match(dn, query_name)
            if score_bonus:
                score = score_bonus(it, score)
            if score > best_score:
                best_score, best = score, it
        except Exception:
            continue
    return best, best_score
