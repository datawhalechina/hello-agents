"""Short method names / acronyms (DiAD, LoRA, Mamba) — avoid broad keyword expansion."""

from __future__ import annotations

import re
from typing import Any

_METHOD_ACRONYM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9\-]{1,15}$")


def is_method_acronym_token(text: str) -> bool:
    """如 DiAD、LoRA、Mamba（无空格、偏短、含大小写或全大写）。"""
    t = (text or "").strip()
    if not t or " " in t:
        return False
    if not _METHOD_ACRONYM_RE.match(t):
        return False
    if t.isupper() and len(t) >= 2:
        return True
    if re.search(r"[A-Z]", t) and re.search(r"[a-z]", t):
        return True
    if len(t) <= 8 and re.search(r"[A-Z]{2,}", t):
        return True
    return len(t) <= 6 and t[0].isupper()


def title_matches_method_acronym(title: str, acronym: str) -> bool:
    if not acronym:
        return False
    ac = acronym.strip()
    flags = 0 if (re.search(r"[a-z]", ac) and re.search(r"[A-Z]", ac)) else re.I
    return bool(re.search(rf"\b{re.escape(ac)}\b", title or "", flags))


def derive_full_title_from_named_method(paper: Any, acronym: str) -> str | None:
    """从「DiAD: A Diffusion-based ...」提取正式标题用于会场版检索。"""
    title = str(getattr(paper, "title", None) or "").strip()
    if not title or not acronym:
        return None
    m = re.match(rf"^{re.escape(acronym.strip())}\s*[:\\-]\s*(.+)$", title, re.I)
    if not m:
        return None
    full = m.group(1).strip()
    return full if len(full) >= 12 else None


def resolve_method_acronym(query: str, keywords: list[str] | None) -> str | None:
    q = (query or "").strip()
    if is_method_acronym_token(q):
        return q
    kws = [str(k).strip() for k in (keywords or []) if str(k).strip()]
    if len(kws) == 1 and is_method_acronym_token(kws[0]):
        return kws[0]
    return None


def paper_matches_method_query(
    paper: Any,
    acronym: str,
    *,
    canonical_titles: list[str] | None = None,
    pinned_arxiv_ids: list[str] | None = None,
    venue: str | None = None,
) -> bool:
    """方法缩写查询：标题含缩写、锚定标题模糊匹配、或 pinned arXiv。"""
    from ...core.search.paper_searcher import PaperSearcher

    title = str(getattr(paper, "title", None) or "")
    blob = f"{title} {getattr(paper, 'abstract', None) or ''}"
    acronym_hit = title_matches_method_acronym(blob, acronym)
    venue_hit = bool(
        venue and PaperSearcher._paper_matches_venue_proceedings(paper, venue)
    )
    title_l = title.lower()
    canonical_hit = False
    for ct in canonical_titles or []:
        ctl = (ct or "").strip().lower()
        if len(ctl) >= 12 and (ctl in title_l or title_l in ctl):
            canonical_hit = True
            break
    arxiv_id = str(getattr(paper, "arxiv_id", None) or getattr(paper, "arxivId", None) or "")
    url = str(getattr(paper, "url", None) or getattr(paper, "source_url", None) or "")
    hay = f"{arxiv_id} {url}".lower()
    pinned_hit = any(
        (aid or "").strip().lower() in hay for aid in (pinned_arxiv_ids or []) if (aid or "").strip()
    )
    named_method = bool(
        re.match(rf"^{re.escape(acronym.strip())}\s*[:\\-]", title.strip(), re.I)
    )

    if pinned_hit or canonical_hit:
        return True
    if venue:
        if venue_hit and acronym_hit:
            return True
        if named_method and acronym_hit:
            return True
        return False
    return acronym_hit
