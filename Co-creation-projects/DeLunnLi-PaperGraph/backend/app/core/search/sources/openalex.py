"""OpenAlex source adapter for PaperSearcher."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...author import Author
from ...paper import Paper
from .source_common import author_names_for_api, pick_best_name_match
from ..normalize import (
    _arxiv_pdf_url_from_id,
    _openalex_human_source_url,
    _openalex_resolve_pdf_url,
    _venue_canonical_key,
    arxiv_id_from_doi,
    extract_pinned_topic_terms,
    plain_query_for_text_apis,
    sanitize_search_keyword_list,
)

logger = logging.getLogger(__name__)


def _openalex_inverted_index_to_text(inv: dict[str, Any | None]) -> str | None:
    """Restore OpenAlex inverted-index abstracts."""
    if not inv:
        return None
    try:
        slot: dict[int, str] = {}
        for word, positions in inv.items():
            for pos in positions:
                slot[int(pos)] = str(word)
        if not slot:
            return None
        return " ".join(slot[i] for i in sorted(slot)).strip() or None
    except (ValueError, TypeError, AttributeError):
        return None


def _score_openalex_venue_item(v_query: str, it: Dict[str, Any]) -> int:
    """Score an OpenAlex venue hit against the query."""
    vq = (v_query or "").strip().lower()
    dn = str(it.get("display_name") or "").lower()
    ab = str(it.get("abbreviated_title") or "").lower()
    score = 3 if (can := _venue_canonical_key(v_query)) and len(str(can)) >= 3 and str(can) in f"{dn} {ab}" else 0
    return score + 2 if len(vq) >= 4 and vq in dn else score


def _pick_openalex_venue_id_from_items(v2: str, items: List[Dict[str, Any]]) -> Optional[str]:
    """Pick the best venue ID from OpenAlex hits."""
    if not items:
        return None
    best_id, best_sc = None, -1
    for it in items:
        try:
            if not (vid := str(it.get("id") or "").strip()):
                continue
            if (sc := _score_openalex_venue_item(v2, it)) > best_sc:
                best_sc, best_id = sc, vid
        except Exception:
            continue
    if best_id is not None and best_sc > 0:
        return best_id
    target = (_venue_canonical_key(v2) or v2.split()[0]).lower().strip()
    chosen = None
    for it in items:
        try:
            if not (vid := str(it.get("id") or "").strip()):
                continue
            dn = str(it.get("display_name") or "").lower()
            ab = str(it.get("abbreviated_title") or "").lower()
            if target and (target in dn or target in ab):
                return vid
            if not chosen:
                chosen = vid
        except Exception:
            continue
    return chosen


def _title_matches_venue_signals(
    title: str,
    venue_canonical: str,
    venue_raw: str,
    abstract: Optional[str],
    notes: str,
) -> bool:
    """Fallback venue check across title, abstract, and notes."""
    v = venue_raw.lower().strip()
    if not v:
        return True
    can = (venue_canonical or "").lower().strip()
    blob = f"{title} {abstract or ''} {notes}".lower()
    if can and len(can) >= 2 and can in blob:
        return True
    if len(v) >= 4 and v in blob:
        return True
    return False


def _is_openalex_listing_title(title: str) -> bool:
    """Reject proceedings/listing records, not individual papers."""
    t = (title or "").strip().lower()
    if not t or len(t) < 15:
        return True
    if re.search(r"(?i)^(\d{4}\s+)?(ieee/cvf\s+)?conference on computer vision", t):
        return True
    if re.search(r"(?i)^computer vision and pattern recognition\b", t) and (
        "proceedings" in t or len(t) < 90
    ):
        return True
    if re.search(r"(?i)^proceedings of\b", t):
        return True
    return False


def _extract_openalex_papers(searcher, results: list, max_results: int, **kwargs) -> List[Paper]:
    """Convert OpenAlex works into Paper objects."""
    papers: List[Paper] = []
    for w in results:
        try:
            title = (w.get("title") or "").strip() or "Unknown"
            if _is_openalex_listing_title(title):
                continue
            authors = [
                Author(name=(au.get("display_name") or "").strip())
                for a in (w.get("authorships") or [])[:80]
                if (au := (a or {}).get("author") or {}) and (au.get("display_name") or "").strip()
            ]
            if not authors:
                continue
            if str(w.get("type") or "").strip().lower() in ("proceedings", "book", "report"):
                continue
            doi = str(doi_raw).replace("https://doi.org/", "").strip() if (doi_raw := w.get("doi")) else None
            year = w.get("publication_year")
            abstract = _openalex_inverted_index_to_text(w.get("abstract_inverted_index"))
            pl = w.get("primary_location") or {}
            venue = ((pl.get("source") or {}).get("display_name") or "").strip() or None
            if not venue:
                hv = w.get("host_venue") or {}
                if isinstance(hv, dict):
                    venue = (hv.get("display_name") or "").strip() or None
            if not venue:
                for loc in (w.get("locations") or [])[:20]:
                    if isinstance(loc, dict) and (lsrc := loc.get("source", {}) if isinstance(loc.get("source"), dict) else {}):
                        if cand := (lsrc.get("display_name") or "").strip():
                            venue = cand
                            break
            pdf_url = _openalex_resolve_pdf_url(w)
            arxiv_id_oa = None
            ids_obj = w.get("ids") or {}
            if isinstance(ids_obj, dict):
                axu = ids_obj.get("arxiv")
                if isinstance(axu, str):
                    if "arxiv.org/abs/" in axu.lower():
                        arxiv_id_oa = axu.split("arxiv.org/abs/", 1)[-1].strip().rstrip("/")
                    elif "arxiv.org/pdf/" in axu.lower():
                        raw = axu.split("arxiv.org/pdf/", 1)[-1].strip().rstrip("/")
                        arxiv_id_oa = raw[:-4] if raw.lower().endswith(".pdf") else raw
            if not arxiv_id_oa:
                arxiv_id_oa = arxiv_id_from_doi(doi)
            if not pdf_url and arxiv_id_oa:
                pdf_url = _arxiv_pdf_url_from_id(arxiv_id_oa)
            source_url = _openalex_human_source_url(w, doi)
            citations = int(w.get("cited_by_count") or 0)
            concepts = [
                str(c["display_name"])
                for c in (w.get("concepts") or [])[:10]
                if isinstance(c, dict) and c.get("display_name")
            ]
            papers.append(
                searcher._make_paper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    doi=doi,
                    arxiv_id=arxiv_id_oa,
                    journal=venue or "OpenAlex",
                    year=year,
                    pdf_url=pdf_url,
                    source_url=source_url,
                    citations=citations,
                    keywords=concepts,
                    source="openalex",
                )
            )
            if len(papers) >= max_results:
                break
        except Exception:
            continue
    return papers


async def _search_openalex_works_by_author_async(
    searcher, author_names: list[str], max_results: int, **kwargs: Any
) -> list[Paper]:
    """Resolve author IDs, then fetch their works."""
    search_candidates = author_names_for_api(author_names)
    if not search_candidates:
        return []
    headers = searcher._openalex_headers()

    from ....services.retrieval.source_plan import openalex_publication_year_filter

    year_filt = openalex_publication_year_filter(kwargs.get("year_from"), kwargs.get("year_to"))

    best_aid, best_score = "", -1
    for cand in search_candidates[:4]:
        try:
            ar = await searcher._async_client.get(
                "https://api.openalex.org/authors",
                params=searcher._openalex_params({"search": cand, "per_page": 8}),
                headers=headers,
                timeout=22.0,
            )
            ar.raise_for_status()
            hits = [h for h in list((ar.json() or {}).get("results") or []) if isinstance(h, dict)]
            best_hit, score = pick_best_name_match(
                hits,
                cand,
                display_name=lambda h: str(h.get("display_name") or "").strip(),
                score_bonus=lambda h, s: s + min(3, int(h.get("works_count") or 0) // 200),
            )
            if best_hit and score > best_score:
                best_score, best_aid = score, str(best_hit.get("id") or "").strip()
        except Exception:
            continue
    if not best_aid:
        return []

    from ....settings import get_settings

    if best_score < float(getattr(get_settings(), "openalex_author_match_min_score", 2.0) or 2.0):
        return []
    short_id = best_aid.rsplit("/", 1)[-1]
    params = searcher._openalex_params({
        "filter": f"authorships.author.id:{short_id}",
        "sort": "publication_date:desc",
        "per_page": min(max(1, max_results), 200),
    })
    if year_filt:
        params["filter"] = f"{params['filter']},{year_filt}"
    try:
        wr = await searcher._async_client.get(
            "https://api.openalex.org/works",
            params=params,
            headers=headers,
            timeout=28.0,
        )
        wr.raise_for_status()
        results = list((wr.json() or {}).get("results") or [])
    except Exception:
        return []

    return _extract_openalex_papers(searcher, results, max_results)


async def _openalex_resolve_venue_id_async(
    searcher, venue_raw: str, headers: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Resolve a venue name to an OpenAlex venue ID."""
    v = (venue_raw or "").strip().lower()
    if not v:
        return None
    v2 = re.sub(r"\b(19|20)\d{2}\b", "", v).strip() or v
    try:
        r = await searcher._async_client.get(
            "https://api.openalex.org/venues",
            params=searcher._openalex_params({"search": v2, "per_page": 5}),
            h=headers or searcher._openalex_headers(),
            timeout=25.0,
        )
        r.raise_for_status()
        return _pick_openalex_venue_id_from_items(
            v2, list((r.json() or {}).get("results") or [])
        )
    except Exception:
        return None


async def search_openalex(
    searcher, query: str, max_results: int = 10, **kwargs
) -> List[Paper]:
    """Search OpenAlex using pipeline constraints."""
    await searcher._ensure_async_client()
    await searcher._rate_limit_async("openalex")

    per_page = min(max(1, max_results), 200)
    venue_raw = (kwargs.get("venue") or "").strip() or None
    venue_s = (venue_raw or "").strip()
    vpj = searcher._resolve_vpj(venue_raw, kwargs)

    from ....services.retrieval.source_plan import openalex_publication_year_filter

    yf_int = int(kwargs.get("year_from")) if kwargs.get("year_from") is not None else None
    yt_int = int(kwargs.get("year_to")) if kwargs.get("year_to") is not None else None
    year_filt = openalex_publication_year_filter(yf_int, yt_int)
    pinned_venue_single_year = bool(
        venue_s and yf_int and yt_int and yf_int == yt_int and 1900 <= yf_int <= 2100
    )

    base_q = (plain_query_for_text_apis(query, kwargs) or "").strip()
    if pinned_venue_single_year:
        pin_q = f"{venue_s} {yf_int}".strip()
        topic_raw = kwargs.get("pinned_topic_terms") or []
        topic_str = (
            (
                " ".join(str(x).strip() for x in topic_raw if str(x).strip())[:120]
                if topic_raw
                else extract_pinned_topic_terms(
                    query=query,
                    merged_kw=sanitize_search_keyword_list(kwargs.get("llm_keywords")),
                    venue=venue_s,
                    year=yf_int,
                )
            )
        )
        if topic_str and topic_str.lower() not in (base_q or "").lower():
            base_q = f"{topic_str} {base_q or pin_q}".strip()[:180]
        if not base_q or len(base_q) < 4:
            base_q = f"{topic_str} {pin_q}".strip()[:180] if topic_str else pin_q
        elif venue_s.lower() not in base_q.lower():
            can_key = (_venue_canonical_key(venue_s) or "").lower()
            if not can_key or can_key not in base_q.lower():
                base_q = f"{topic_str} {pin_q}".strip()[:180] if topic_str else pin_q
            elif str(yf_int) not in base_q:
                base_q = f"{base_q} {yf_int}".strip()[:180]
    qtext = (base_q if base_q else venue_s or "").strip()
    if pinned_venue_single_year and (not qtext or qtext == "*"):
        qtext = f"{venue_s} {yf_int}".strip()

    try:
        qtext_clean = re.sub(
            r"\s+", " ",
            re.sub(r"[^\w\s\-\./]+", " ", qtext, flags=re.UNICODE),
        ).strip()[:180]
    except Exception:
        qtext_clean = (qtext or "").strip()[:180]

    star_q = qtext in ("*", "")
    main_track_oa = bool(venue_s and vpj and kwargs.get("main_conference_proceedings_only"))

    if pinned_venue_single_year and main_track_oa and venue_s and yf_int:
        headers = searcher._openalex_headers()
        vid = await _openalex_resolve_venue_id_async(searcher, venue_s, headers=headers)
        if vid:
            try:
                browse_mult = 5 if kwargs.get("venue_browse") else 3
                browse_n = min(max(per_page, max_results * browse_mult), 200)
                if kwargs.get("venue_browse"):
                    browse_n = max(browse_n, 80)
                oa_params = searcher._openalex_params({
                    "filter": f"publication_year:{yf_int},host_venue.id:{vid}",
                    "per_page": browse_n,
                    "sort": "cited_by_count:desc",
                })
                resp = await searcher._async_http_get_with_retry(
                    "https://api.openalex.org/works",
                    params=oa_params,
                    headers=headers,
                    timeout=float(kwargs.get("openalex_timeout_sec") or 45.0),
                    max_attempts=2,
                )
                browse_results = list((resp.json() or {}).get("results") or [])
                browse_papers = _extract_openalex_papers(
                    searcher, browse_results, max(browse_n, max_results)
                )
                from ....services.retrieval.paper_filters import is_obvious_workshop_track

                browse_papers = [
                    p
                    for p in browse_papers
                    if not is_obvious_workshop_track(p, venue_s)
                ]
                if browse_papers:
                    searcher._bump_stat("openalex_requests")
                    return browse_papers[:max_results]
            except Exception:
                logger.warning(
                    "[OpenAlex] host_venue browse failed venue=%s year=%s",
                    venue_s,
                    yf_int,
                    exc_info=True,
                )

    if star_q and (pinned_venue_single_year or main_track_oa):
        star_q = False
        qtext = (
            f"{venue_s} {yf_int}".strip()
            if pinned_venue_single_year and yf_int
            else (venue_s or qtext)
        )
        try:
            qtext_clean = re.sub(
                r"\s+", " ",
                re.sub(r"[^\w\s\-\./]+", " ", qtext, flags=re.UNICODE),
            ).strip()[:180]
        except Exception:
            qtext_clean = (qtext or "").strip()[:180]

    if star_q:
        if yf_int is None and year_filt is None:
            yf_int = datetime.now().year - 1
            year_filt = f"publication_year:>={yf_int}"
        filt = year_filt or f"publication_year:>={yf_int}"
        ocid = (kwargs.get("openalex_concept_id") or "").strip()
        if ocid and filt:
            filt = f"{filt},concept.id:{ocid if ocid.startswith('http') else f'https://openalex.org/{ocid}'}"
        params: Dict[str, Any] = searcher._openalex_params({
            "per_page": per_page,
            "sort": "publication_date:desc",
        })
        if filt:
            params["filter"] = filt
    else:
        params = searcher._openalex_params({
            "search": qtext_clean or qtext,
            "per_page": per_page,
        })
        if year_filt:
            params["filter"] = year_filt

    headers = searcher._openalex_headers()
    oa_retry_without_host_venue = (
        kwargs.get("venue_fallback_if_empty", True)
        or kwargs.get("openalex_relax_host_venue_on_empty", True)
    )

    async def _do_request(with_venue_filter: bool) -> List[Dict[str, Any]]:
        local_params = dict(params)
        if with_venue_filter and venue_raw and vpj:
            vid = await _openalex_resolve_venue_id_async(searcher, venue_raw, headers=headers)
            if vid:
                prev = (local_params.get("filter") or "").strip()
                local_params["filter"] = f"{prev},host_venue.id:{vid}" if prev else f"host_venue.id:{vid}"
        resp = await searcher._async_client.get(
            url="https://api.openalex.org/works",
            params=local_params,
            headers=headers,
            timeout=45.0,
        )
        if resp.status_code == 400 and (local_params.get("search") or local_params.get("filter")):
            lp2 = dict(local_params)
            lp2["search"] = qtext_clean or str(lp2.get("search") or "")
            lp2.pop("filter", None)
            if year_filt:
                lp2["filter"] = year_filt
            resp = await searcher._async_client.get(
                url="https://api.openalex.org/works",
                params=lp2,
                headers=headers,
                timeout=45.0,
            )
        resp.raise_for_status()
        return list((resp.json() or {}).get("results") or [])

    results = await _do_request(with_venue_filter=bool(venue_raw and vpj))
    if venue_raw and vpj and not results and oa_retry_without_host_venue:
        results = await _do_request(with_venue_filter=False)

    if star_q and not results and (kwargs.get("openalex_concept_id") or "").strip() and "concept.id:" in str(params.get("filter", "")):
        yf_b = yf_int if yf_int is not None else datetime.now().year - 1
        params["filter"] = f"publication_year:>={yf_b}"
        results = await _do_request(with_venue_filter=bool(venue_raw and vpj))
        if venue_raw and vpj and not results and oa_retry_without_host_venue:
            results = await _do_request(with_venue_filter=False)

    papers = _extract_openalex_papers(searcher, results, max_results)

    if main_track_oa and venue_raw and papers:
        matched = [p for p in papers if searcher._paper_matches_venue(p, venue_raw)]
        if not matched:
            can = _venue_canonical_key(venue_raw)
            matched = [
                p for p in papers
                if _title_matches_venue_signals(
                    getattr(p, "title", "") or "",
                    can,
                    venue_raw,
                    getattr(p, "abstract", None),
                    getattr(p, "notes", None) or "",
                )
            ]
        papers = matched

    searcher._bump_stat("openalex_requests")
    return papers
