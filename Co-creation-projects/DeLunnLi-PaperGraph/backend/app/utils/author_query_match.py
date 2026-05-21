
from __future__ import annotations

from .common import text_has_cjk

def normalize_author_names(raw: list[str | None]) -> list[str]:
    """Deduplicate parsed author names."""
    seen: set[str] = set()
    out: list[str] = []
    for x in raw or []:
        s = str(x or "").strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
        if len(out) >= 8:
            break
    return out

def pick_primary_english_author_for_query(authors: list[str]) -> str | None:
    """Pick the first Latin-script author for API queries."""
    for a in authors:
        s = str(a).strip()
        if s and not text_has_cjk(s):
            return s
    return None

def is_author_centric_search(query: str, authors: list[str | None]) -> bool:
    """Fast check for author-only searches."""
    auth = normalize_author_names([str(x) for x in (authors or []) if str(x).strip()])
    return bool(auth) and not bool((query or "").strip())

def author_phrase_matches_canonical_line(line: str, phrase: str) -> bool:
    """Match a normalized author phrase against a paper author list."""
    pl = (line or "").strip().lower()
    ph = (phrase or "").strip().lower()
    return bool(pl and ph) and ph in pl
