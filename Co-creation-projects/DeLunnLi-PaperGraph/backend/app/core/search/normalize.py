from __future__ import annotations

import functools
import re
from typing import Any

_QUERY_DELIM = re.compile(r"[,;\uFF0C\uFF1B\n]+")
_RE_JATS_MARKUP = re.compile(r"<[^>]+>")
_RE_MULTIPLE_SPACES = re.compile(r"\s+")
_RE_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.?([\d.]+\d)", re.I)
_RE_ARXIV_URL_IN_DOI = re.compile(r"arxiv\.org/(?:abs|pdf)/([\w./]+)", re.I)
_RE_ARXIV_VERSION_SUFFIX = re.compile(r"v\d+$", re.I)
_RE_TITLE_ENTITY = re.compile(r"&amp;|&lt;|&gt;|&quot;|&#\d+;")
_RE_TITLE_NON_ALNUM = re.compile(r"[^a-z0-9\u4e00-\u9fff]+", re.I)


@functools.lru_cache(maxsize=128)
def _venue_canonical_key(venue: str) -> str:
    v = (venue or "").strip().lower()
    v = re.sub(r"[^a-z0-9]", "", v)
    return v if len(v) >= 2 else ""


def _score_name_match(display_name: str, query_name: str) -> int:
    dl, ql = display_name.strip().lower(), query_name.strip().lower()
    if not dl or not ql: return 0
    parts = [x for x in ql.replace(",", " ").split() if x]
    score = 0
    if dl == ql: score += 10
    if ql in dl or dl in ql: score += 6
    if parts and all(p in dl for p in parts if len(p) >= 2): score += 4
    return score


def split_query_phrases(query: str) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    if not _QUERY_DELIM.search(q):
        return [(q or "").strip()]
    parts: list[str] = []
    for p in _QUERY_DELIM.split(q):
        t = p.strip()
        if t:
            parts.append((t or "").strip())
    return parts if parts else [(q or "").strip()]


def sanitize_search_keyword_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        if x is None:
            continue
        s = str(x).strip()
        if s and s not in out:
            out.append(s)
        if len(out) >= 24:
            break
    return out


def _normalize_title_for_dedupe(title: str | None) -> str:
    if not title:
        return ""
    t = str(title).lower()
    t = _RE_TITLE_ENTITY.sub(" ", t)
    t = _RE_JATS_MARKUP.sub(" ", t)
    t = _RE_TITLE_NON_ALNUM.sub(" ", t)
    return _RE_MULTIPLE_SPACES.sub(" ", t).strip()


def arxiv_id_from_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = str(doi).strip().lower()
    if d.startswith("https://doi.org/"):
        d = d[len("https://doi.org/"):].strip()
    if not d:
        return None
    m = _RE_ARXIV_DOI.search(d)
    if m:
        return _RE_ARXIV_VERSION_SUFFIX.sub("", m.group(1)).lower()
    m2 = _RE_ARXIV_URL_IN_DOI.search(d)
    if m2:
        raw = m2.group(1).split("/")[-1]
        return _RE_ARXIV_VERSION_SUFFIX.sub("", raw).lower()
    return None


def _arxiv_pdf_url_from_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    raw = str(arxiv_id).strip()
    if not raw:
        return None
    low = raw.lower()
    if "arxiv.org/pdf/" in low:
        u = raw if raw.lower().startswith("http") else "https://" + raw.lstrip("/")
        return u.split("?", 1)[0].rstrip("/")
    if "arxiv.org/abs/" in low:
        tail = raw.split("arxiv.org/abs/", 1)[-1].strip().rstrip("/")
    else:
        tail = re.sub(r"^arxiv:", "", raw, flags=re.I).strip()
        tail = tail.split("/")[-1]
    tail = tail.strip().rstrip("/")
    if not tail or not re.search(r"\d", tail):
        return None
    return f"https://arxiv.org/pdf/{tail}.pdf"


def _arxiv_canonical_from_paper(paper: Any) -> str | None:
    aid = (paper.arxiv_id or "").strip()
    if aid.lower().startswith("arxiv:"):
        aid = aid[6:]
    aid = aid.strip().rstrip("/")
    aid = _RE_ARXIV_VERSION_SUFFIX.sub("", aid)
    if aid and re.search(r"\d", aid):
        return aid.lower()
    return arxiv_id_from_doi(paper.doi)


def _openalex_collect_landing_urls(w: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if not raw or not isinstance(raw, str):
            return
        s = raw.strip().split("?", 1)[0]
        if not s.lower().startswith("http"):
            return
        sl = s.lower()
        if bool(re.search(r"https?://(api\.)?openalex\.org/works?/", sl)) or bool(
            re.search(r"https?://(www\.)?openalex\.org/w\d+", sl)
        ):
            return
        if sl in seen:
            return
        seen.add(sl)
        out.append(s)

    for key in ("best_oa_location", "primary_location"):
        loc = w.get(key) or {}
        if isinstance(loc, dict):
            add(loc.get("landing_page_url"))
    for loc in w.get("locations") or []:
        if isinstance(loc, dict):
            add(loc.get("landing_page_url"))
    oa = w.get("open_access") or {}
    if isinstance(oa, dict):
        add(oa.get("oa_url"))
    return out


def _openalex_human_source_url(w: dict[str, Any], doi: str | None) -> str | None:
    land = _openalex_collect_landing_urls(w)
    for s in land:
        if not s.lower().endswith(".pdf"):
            return s
    for s in land:
        if s.lower().endswith(".pdf"):
            return s
    if doi:
        d = str(doi).strip().lstrip("https://doi.org/").lstrip("doi.org/")
        if d:
            return f"https://doi.org/{d}"
    wid = w.get("id")
    return str(wid).strip() if isinstance(wid, str) and wid.strip() else None


def _openalex_resolve_pdf_url(w: dict[str, Any]) -> str | None:
    if not isinstance(w, dict):
        return None
    for key in ("best_oa_location", "primary_location"):
        loc = w.get(key) or {}
        if isinstance(loc, dict):
            u = loc.get("pdf_url")
            if isinstance(u, str) and u.strip():
                return u.strip().split("?", 1)[0]
    for loc in w.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        u = loc.get("pdf_url")
        if isinstance(u, str) and u.strip():
            return u.strip().split("?", 1)[0]
    oa = w.get("open_access") or {}
    if isinstance(oa, dict):
        u = oa.get("oa_url")
        if isinstance(u, str) and u.strip():
            ul = u.strip().lower()
            if ul.endswith(".pdf") or "arxiv.org/pdf" in ul:
                return u.strip().split("?", 1)[0]

    for s in _openalex_collect_landing_urls(w):
        ul = s.lower()
        if ul.endswith(".pdf") or "arxiv.org/pdf" in ul:
            return s
    return None


def normalized_query_for_text_apis(query: str) -> str:
    parts = split_query_phrases(query)
    return " ".join(parts).strip()


def plain_query_for_text_apis(query: str, kwargs: dict[str, Any]) -> str:
    lk = sanitize_search_keyword_list(kwargs.get("llm_keywords"))
    if not lk:
        return normalized_query_for_text_apis(query)
    if len(lk) >= 2:
        q0 = ((query or "").strip() or str(lk[0]).strip())
        venue_kw = (kwargs.get("venue") or "").strip()

        if venue_kw and len(q0) <= 16:
            tail: list[str] = []
            for x in lk[1:8]:
                t = str(x).strip()
                if not t or t.lower() == q0.lower():
                    continue
                tail.append(t)
                if len(tail) >= 4:
                    break
            if tail:
                merged = f"{q0} {' '.join(tail)}".strip()
                return merged[:200]
        return q0[:200] if q0 else str(lk[0]).strip()[:200]
    return (str(lk[0]).strip() or normalized_query_for_text_apis(query))[:200]


def topic_terms_excluding_venue_year(
    query: str,
    *,
    extra_terms: list[str] | None = None,
    venue: str | None = None,
    year: int | None = None,
) -> str:
    seen: set[str] = set()
    out: list[str] = []
    vlow = (venue or "").strip().lower()

    def _consume(text: str) -> None:
        for seg in _QUERY_DELIM.split(text or ""):
            for tok in re.split(r"\s+", seg.strip()):
                t = tok.strip()
                if not t or len(t) < 2:
                    continue
                if year is not None and re.fullmatch(r"(?:19|20)\d{2}", t):
                    continue
                tl = t.lower()
                if vlow and (tl == vlow or re.sub(r"[^a-z0-9]", "", tl) == re.sub(r"[^a-z0-9]", "", vlow)):
                    continue
                if tl in seen:
                    continue
                seen.add(tl)
                out.append(t)
                if len(out) >= 12:
                    return

    _consume(query or "")
    for x in extra_terms or []:
        if len(out) >= 12:
            break
        _consume(str(x))
    return " ".join(out).strip()


def sanitize_pinned_topic_keywords(raw: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in raw or []:
        s = str(x).strip()
        if not s or len(s) < 2 or len(s) > 80:
            continue
        if s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out[:10]


def extract_pinned_topic_terms(
    *,
    query: str,
    merged_kw: list[str] | None,
    venue: str,
    year: int | None,
) -> str:
    seen: set[str] = set()
    parts: list[str] = []

    def _push(text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        tl = t.lower()
        if tl in seen:
            return
        seen.add(tl)
        parts.append(t)

    t_query = topic_terms_excluding_venue_year(query or "", venue=venue, year=year)
    if t_query:
        _push(t_query)
    for kw in sanitize_pinned_topic_keywords(list(merged_kw or [])):
        tk = topic_terms_excluding_venue_year(kw, venue=venue, year=year)
        if tk:
            _push(tk)
    return " ".join(parts[:12]).strip()
