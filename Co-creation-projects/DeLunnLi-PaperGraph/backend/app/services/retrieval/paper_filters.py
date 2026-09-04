"""Fast filters for non-main-track papers."""

from __future__ import annotations

import re

from app.core.paper import Paper as LitPaper

_JOURNAL_LIKE_VENUE_RE = re.compile(
    r"(?i)\b(?:trans\.|transactions|journal|magazine|letters|pattern anal)\b"
)

_VENUE_ALIASES: dict[str, tuple[str, ...]] = {
    "neurips": (
        "neurips", "nips",
        "neural information processing systems",
        "advances in neural information processing systems",
    ),
    "nips": (
        "neurips", "nips",
        "neural information processing systems",
        "advances in neural information processing systems",
    ),
    "cvpr": ("cvpr", "computer vision and pattern recognition"),
    "iccv": ("iccv", "international conference on computer vision"),
    "eccv": ("eccv", "european conference on computer vision"),
    "iclr": ("iclr", "international conference on learning representations"),
    "icml": ("icml", "international conference on machine learning"),
    "acl": ("acl", "annual meeting of the association for computational linguistics"),
    "emnlp": ("emnlp", "empirical methods in natural language processing"),
    "aaai": ("aaai", "association for the advancement of artificial intelligence"),
    "ijcai": ("ijcai", "international joint conference on artificial intelligence"),
    "kdd": ("kdd", "knowledge discovery and data mining"),
    "sigir": ("sigir", "information retrieval"),
}


def _venue_aliases(venue: str | None) -> tuple[str, ...]:
    raw = (venue or "").strip().lower()
    if not raw:
        return ()
    key = re.sub(r"[^a-z0-9]", "", raw)
    aliases = _VENUE_ALIASES.get(key) or _VENUE_ALIASES.get(raw)
    return aliases or (raw,)


def _contains_venue_alias(text: str, venue: str | None) -> bool:
    low = (text or "").lower()
    if not low:
        return False
    compact = re.sub(r"[^a-z0-9]", "", low)
    for alias in _venue_aliases(venue):
        a = alias.lower()
        if len(a) < 2:
            continue
        if a in low:
            return True
        ac = re.sub(r"[^a-z0-9]", "", a)
        if ac and ac in compact:
            return True
    return False


def has_strong_main_conference_venue_signal(paper: LitPaper, target_venue: str | None) -> bool:
    """Check whether source or venue proves target-conference membership."""
    if not (target_venue or "").strip():
        return True
    source = (getattr(paper, "source", None) or "").strip().lower()
    if source in {"tavily_proceedings", "official_discovered", "tavily", "proceedings"}:
        return True
    journal = (getattr(paper, "journal", None) or getattr(paper, "venue", None) or "").strip()
    return _contains_venue_alias(journal, target_venue)


def is_journal_not_target_proceedings(paper: LitPaper, target_venue: str | None) -> bool:
    venue = (target_venue or "").strip()
    if not venue:
        return False
    journal = (getattr(paper, "journal", None) or getattr(paper, "venue", None) or "").strip()
    if not journal or not _JOURNAL_LIKE_VENUE_RE.search(journal):
        return False
    vkey = re.sub(r"[^a-z0-9]", "", venue.lower())
    jkey = re.sub(r"[^a-z0-9]", "", journal.lower())
    return bool(vkey) and vkey not in jkey


def is_stale_best_of_special(title: str, pinned_year: int | None) -> bool:
    if pinned_year is None or not re.search(r"(?i)\b(best of|special section)\b", title or ""):
        return False
    for m in re.finditer(r"(?:19|20)\d{2}", title or ""):
        try:
            y = int(m.group())
        except ValueError:
            continue
        if y != int(pinned_year):
            return True
    return False


def is_obvious_workshop_track(paper: LitPaper, target_venue: str | None = None) -> bool:
    """Fast pre-filter for obvious workshop/satellite papers."""
    title = (getattr(paper, "title", None) or "").strip()
    journal = (getattr(paper, "journal", None) or getattr(paper, "venue", None) or "").strip()
    blob = f"{title} {journal}".lower()
    if not blob.strip():
        return False
    if re.search(
        r"(?i)\b(workshops?|symposium|symposia|tutorial|"
        r"demo\s+track|satellite)\b",
        blob,
    ):
        return True
    if target_venue:
        can_t = re.escape((target_venue or "").strip())
        if re.search(rf"(?i)\b{can_t}\s+20\d{{2}}\s+workshop\b", title):
            return True
    return False


def should_exclude_main_conference_paper(
    paper: LitPaper,
    target_venue: str | None = None,
    *,
    pinned_year: int | None = None,
    require_venue_signal: bool = False,
) -> bool:
    title = (getattr(paper, "title", None) or "").strip()
    if is_obvious_workshop_track(paper, target_venue):
        return True
    if is_journal_not_target_proceedings(paper, target_venue):
        return True
    if is_stale_best_of_special(title, pinned_year):
        return True
    if require_venue_signal and not has_strong_main_conference_venue_signal(paper, target_venue):
        return True
    return False
