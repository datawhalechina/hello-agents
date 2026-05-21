from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, List

from ...author import Author
from ...paper import Paper
from ....utils.common import text_has_cjk
from ..normalize import (
    _QUERY_DELIM,
    _RE_ARXIV_VERSION_SUFFIX,
    sanitize_search_keyword_list,
    topic_terms_excluding_venue_year,
)
from .source_common import json_api_headers, normalize_query_authors, pick_best_name_match

logger = logging.getLogger(__name__)

# DBLP adds numeric suffixes to disambiguate same-name authors.
_DBLP_AUTHOR_SUFFIX_RE = re.compile(r"\s+\d{4}$")


def _dblp_parse_ee_urls(ee: Any) -> tuple[str | None, str | None, str | None, str | None]:
    urls: list[str] = []
    if isinstance(ee, list):
        for u in ee:
            if isinstance(u, str) and u.strip():
                urls.append(u.strip())
    elif isinstance(ee, str) and ee.strip():
        urls.append(ee.strip())

    doi: str | None = None
    aid: str | None = None
    pdf_url: str | None = None
    landing: str | None = None

    for u in urls:
        lu = u.lower()
        base = u.split("?", 1)[0].strip()

        if doi is None and "doi.org/" in lu:
            doi = u.split("doi.org/", 1)[-1].split("?", 1)[0].strip().rstrip("/")
            # arXiv DOI, e.g. 10.48550/arXiv.2601.22158.
            if aid is None:
                m = re.search(r"arxiv/([\d.]+)", lu)
                if m:
                    aid = _RE_ARXIV_VERSION_SUFFIX.sub("", m.group(1))
        if aid is None and "arxiv.org/abs/" in lu:
            raw = u.split("arxiv.org/abs/", 1)[-1].strip().rstrip("/")
            aid = _RE_ARXIV_VERSION_SUFFIX.sub("", raw)

        bl = base.lower()
        if pdf_url is None and (bl.endswith(".pdf") or "arxiv.org/pdf/" in bl):
            pdf_url = base
        elif landing is None and bl.startswith("http") and not bl.endswith(".pdf") and "arxiv.org/pdf/" not in bl:
            landing = base

    first = urls[0] if urls else None
    source_url = landing or first
    return source_url, doi, aid, pdf_url


def raw_query_for_dblp(query: str, kwargs: dict[str, Any]) -> str:
    if bool(kwargs.get("dblp_use_llm_keywords")):
        lk = sanitize_search_keyword_list(kwargs.get("llm_keywords"))
        if lk:
            if len(lk) >= 2:
                q0 = (query or "").strip()
                return q0 if q0 else str(lk[0]).replace('"', " ").strip()
            return str(lk[0]).replace('"', " ").strip()
    q = (query or "").strip()
    if not q:
        return ""

    parts = [p.strip() for p in _QUERY_DELIM.split(q) if p and p.strip()]
    if not parts:
        return q.replace('"', " ").strip()
    return " ".join([p.replace('"', " ").strip() for p in parts]).strip()


def _dblp_venue_search_queries(venue_only: str, year_from: Any) -> list[str]:
    raw = (venue_only or "").strip()
    if not raw:
        return []
    vlow = raw.lower()
    yfi = int(year_from) if year_from is not None and str(year_from).isdigit() else None
    seen, out = set(), []

    if yfi:
        q = f"{raw} {yfi}"
        if q not in seen:
            seen.add(q)
            out.append(q)

    if yfi:
        q = f"conf/{vlow}/{yfi}"
        if q not in seen:
            seen.add(q)
            out.append(q)
    q = f"conf/{vlow}"
    if q not in seen:
        seen.add(q)
        out.append(q)

    if raw not in seen:
        seen.add(raw)
        out.append(raw)
    return out


async def search_dblp(searcher, query, max_results=10, **kwargs):
    await searcher._ensure_async_client()
    await searcher._rate_limit_async("dblp")

    author_names = normalize_query_authors(query, kwargs.get("authors") or kwargs.get("author") or [])
    papers_by_author = None
    for author_name in author_names:
        if text_has_cjk(author_name):
            continue
        papers_by_author = await _search_dblp_by_author_pid(
            searcher, author_name, max_results, kwargs
        )
        if papers_by_author:
            break
    if papers_by_author:
        searcher._bump_stat("dblp_requests")
        return papers_by_author
    if author_names and not papers_by_author:
        from ....settings import get_settings

        if not bool(getattr(get_settings(), "dblp_author_name_fallback_search", True)):
            return []

    base_q = (raw_query_for_dblp(query, kwargs) or "").strip()
    venue_only = (kwargs.get("venue") or "").strip()
    vpj = searcher._resolve_vpj(venue_only, kwargs)
    strict_no_fallback = bool(
        vpj and venue_only and not kwargs.get("venue_fallback_if_empty", True)
    )
    dblp_queries: list[str] = []
    if venue_only:
        dblp_queries = _dblp_venue_search_queries(venue_only, kwargs.get("year_from"))
        yf_dblp = (
            int(kwargs.get("year_from"))
            if kwargs.get("year_from") is not None
               and str(kwargs.get("year_from")).isdigit()
            else None
        )
        if base_q:
            topic = topic_terms_excluding_venue_year(
                base_q, venue=venue_only, year=yf_dblp
            )
            topic_prefix = []
            if topic:
                topic_prefix.append(f"{topic} {venue_only}".strip())
                if yf_dblp is not None:
                    topic_prefix.insert(
                        0, f"{topic} {venue_only} {yf_dblp}".strip()
                    )
            elif base_q.lower() != venue_only.lower():
                topic_prefix.append(f"{base_q} {venue_only}".strip())
            seen_q = set(dblp_queries)
            dblp_queries = [q for q in topic_prefix if q not in seen_q] + dblp_queries
        tt_prefix = []
        raw_tt = kwargs.get("target_titles")
        if isinstance(raw_tt, list) and raw_tt:
            t0 = str(raw_tt[0] or "").replace('"', " ").strip()
            if len(t0) >= 8:
                tt_prefix.append(t0[:220])
        if tt_prefix:
            dblp_queries = (
                [q for q in tt_prefix if q not in set(dblp_queries)] + dblp_queries
            )
        qtext = dblp_queries[0] if dblp_queries else venue_only
    elif base_q:
        qtext = base_q
    else:
        return []

    n_cap = 1200 if strict_no_fallback else 500
    if venue_only:
        yf_db, yt_db = kwargs.get("year_from"), kwargs.get("year_to")
        pinned_db = (
            (
                yf_db is not None
                and yt_db is not None
                and int(yf_db) == int(yt_db)
                and 1900 <= int(yf_db) <= 2100
            )
            if yf_db is not None and yt_db is not None
            else False
        )
        has_topic = bool(
            base_q
            and topic_terms_excluding_venue_year(
                base_q,
                venue=venue_only,
                year=int(yf_db) if pinned_db else None,
            )
        )
        if has_topic:
            n_cap = 500 if strict_no_fallback else 300
            n = min(max(max_results, 40), n_cap)
        elif not base_q:
            venue_browse = bool(kwargs.get("venue_browse"))
            n_cap = 80 if (pinned_db and venue_browse) else (36 if pinned_db else 100)
            n = min(max(40 if (pinned_db and venue_browse) else (20 if pinned_db else 30), max_results * 2), n_cap)
        else:
            n = min(max(1, max_results), n_cap)
    else:
        n = min(max(1, max_results), n_cap)

    try:
        max_attempts = max(
            1,
            min(
                3,
                int(
                    kwargs.get("http_max_attempts")
                    or os.getenv("PAPERGRAPH_DBLP_MAX_ATTEMPTS")
                    or 2
                ),
            ),
        )
    except Exception:
        max_attempts = 2
    query_chain = dblp_queries if venue_only else [qtext]
    dblp_req_to = max(
        10.0,
        min(
            90.0,
            float(
                kwargs.get("dblp_timeout_sec")
                or kwargs.get("http_timeout_sec")
                or 35.0
            ),
        ),
    )
    headers = json_api_headers(searcher)
    data, raw_hits = {}, None
    for qi, cand_q in enumerate(query_chain):
        qtext = cand_q
        try:
            r = await searcher._async_http_get_with_retry(
                "https://dblp.org/search/publ/api",
                params={
                    "q": qtext.strip(),
                    "format": "json",
                    "h": n,
                    "c": "0",
                },
                headers=headers,
                timeout=dblp_req_to,
                max_attempts=max_attempts,
            )
            data = r.json() or {}
            raw_hits = ((data.get("result") or {}).get("hits") or {}).get("hit")
            if raw_hits:
                break
        except Exception:
            if qi + 1 >= len(query_chain):
                logger.warning("[DBLP] async giving up q=%r", qtext)
                searcher._bump_stat("dblp_requests")
                return []
            continue
    if not raw_hits:
        searcher._bump_stat("dblp_requests")
        return []

    raw_list = [raw_hits] if isinstance(raw_hits, dict) else list(raw_hits)
    y_min = (
        int(kwargs.get("year_from"))
        if kwargs.get("year_from") is not None
        else None
    )
    y_max = (
        int(kwargs.get("year_to"))
        if kwargs.get("year_to") is not None
        else None
    )
    papers: List[Paper] = []
    pinned_db = y_min is not None and y_max is not None and y_min == y_max

    for hit in raw_list:
        try:
            info = (hit or {}).get("info") or {}
            if str(info.get("type") or "").strip().lower() == "editorship":
                continue
            key = str(info.get("key") or "").strip()
            if key.startswith("conf/"):
                parts = key.split("/")
                if len(parts) >= 3 and re.fullmatch(
                    r"(?:19|20)\d{2}w?", parts[-1].strip().lower()
                ):
                    continue
            title = (info.get("title") or "").strip() or "Unknown"
            if not title:
                continue
            if bool(kwargs.get("main_conference_proceedings_only")):
                from ....services.retrieval.paper_filters import is_stale_best_of_special
                # Hard-reject obvious satellite tracks before LLM ranking.
                tl = title.lower()
                if re.search(r"\b(workshops?|symposium|symposia|tutorial|demo\s+track|satellite|challenge|ntire|pbvs|competition|contest)\b", tl):
                    continue
                y_pin = (
                    int(kwargs.get("year_from"))
                    if kwargs.get("year_from") is not None
                    and kwargs.get("year_to") is not None
                    and int(kwargs.get("year_from")) == int(kwargs.get("year_to"))
                    else None
                )
                if is_stale_best_of_special(title, y_pin):
                    continue
            year = (
                int(ys)
                if (ys := str(info.get("year") or "").strip()).isdigit()
                else None
            )
            if y_min is not None and year is not None and year < y_min:
                continue
            if y_max is not None and year is not None and year > y_max:
                continue

            raw_a = (info.get("authors") or {}).get("author", [])
            if isinstance(raw_a, dict):
                raw_a = [raw_a]
            authors = [
                Author(
                    name=_DBLP_AUTHOR_SUFFIX_RE.sub("", (
                        (a.get("text") or "").strip()
                        if isinstance(a, dict)
                        else str(a).strip()
                    ))
                )
                for a in raw_a
                if (
                    a.get("text") if isinstance(a, dict) else str(a)
                ).strip()
            ]

            ee = info.get("ee")
            source_url, doi_guess, arxiv_guess, pdf_ee = _dblp_parse_ee_urls(ee)
            if not source_url:
                source_url = (info.get("url") or "").strip() or None
            venue = (
                str(info.get("venue")[0]).strip().upper()
                if isinstance(info.get("venue"), list) and info.get("venue")
                else (str(info.get("venue") or "").strip().upper() or None)
            )
            if key.startswith("conf/"):
                parts = key.split("/")
                if len(parts) >= 2:
                    venue = parts[1].strip().upper()

            papers.append(
                searcher._make_paper(
                    title=title,
                    authors=authors,
                    doi=doi_guess,
                    arxiv_id=arxiv_guess,
                    journal=venue or "DBLP",
                    year=year,
                    pdf_url=pdf_ee,
                    source_url=source_url,
                    source="dblp",
                )
            )
        except Exception:
            continue

    searcher._bump_stat("dblp_requests")

    # New-year DBLP metadata can lag; retry year-1 unless the year is pinned.
    if not papers and y_min is not None and y_min >= datetime.now().year - 1:
        skip_fallback = bool(kwargs.get("wants_recent")) or (
            pinned_db and bool(kwargs.get("main_conference_proceedings_only"))
        )
        if not skip_fallback and y_min >= datetime.now().year:
            logger.info(
                "[DBLP] year=%s no results, retry year=%s", y_min, y_min - 1
            )
            return await search_dblp(
                searcher,
                query,
                max_results,
                **{
                    **kwargs,
                    "year_from": y_min - 1,
                    "year_to": (
                        y_min - 1
                        if y_max == y_min
                        else (y_max - 1 if y_max else None)
                    ),
                },
            )

    return papers


async def _search_dblp_by_author_pid(searcher, author_name, max_results, kwargs):
    if not author_name:
        return None
    try:
        headers = json_api_headers(searcher)
        ar = await searcher._async_client.get(
            "https://dblp.org/search/author/api",
            params={"q": author_name, "format": "json", "h": 5, "c": 0},
            headers=headers,
            timeout=25.0,
        )
        ar.raise_for_status()
        hits = (
            (((ar.json() or {}).get("result") or {}).get("hits") or {}).get("hit")
            or []
        )
        if isinstance(hits, dict):
            hits = [hits]

        def _dblp_author_name(h: Any) -> str:
            info = (h or {}).get("info") or {}
            return str(info.get("display_name") or info.get("author") or "").strip()

        def _dblp_author_bonus(h: Any, score: int) -> int:
            url = str(((h or {}).get("info") or {}).get("url") or "").strip()
            return score + (2 if "/pid/" in url else 0)

        best_hit, best_pid_score = pick_best_name_match(
            hits, author_name, display_name=_dblp_author_name, score_bonus=_dblp_author_bonus
        )
        pid_url = str(((best_hit or {}).get("info") or {}).get("url") or "").strip() if best_hit else ""
        if pid_url and "/pid/" in pid_url:
            from ....settings import get_settings

            min_score = float(
                getattr(get_settings(), "dblp_author_pid_min_score", 3.0) or 3.0
            )
            if best_pid_score < min_score:
                pid_url = ""
            else:
                pr = await searcher._async_client.get(
                    pid_url + ".xml",
                    headers={"User-Agent": headers["User-Agent"]},
                    timeout=25.0,
                )
                pr.raise_for_status()
                root = ET.fromstring(pr.text)
        else:
            root = None

        papers: List[Paper] = []
        if root is not None:
            for rnode in list(root.findall("./r")):
                if len(papers) >= max_results:
                    break
                try:
                    pub = next(
                        (child for child in rnode if child.tag), None
                    )
                    if pub is None:
                        continue
                    title = (
                        (pub.findtext("title") or "").strip() or "Unknown"
                    )
                    year = (
                        int(yt)
                        if (
                            yt := (pub.findtext("year") or "").strip()
                        ).isdigit()
                        else None
                    )
                    yf = kwargs.get("year_from")
                    if yf is not None and year is not None and year < int(yf):
                        continue
                    venue = (
                        pub.findtext("booktitle")
                        or pub.findtext("journal")
                        or ""
                    ).strip().upper() or None
                    authors = [
                        Author(name=_DBLP_AUTHOR_SUFFIX_RE.sub("", (a.text or "").strip()))
                        for a in pub.findall("author")
                        if (a.text or "").strip()
                    ]
                    ee = (pub.findtext("ee") or "").strip() or None
                    url_text = (
                        (pub.findtext("url") or "").strip() or None
                    )
                    papers.append(
                        searcher._make_paper(
                            title=title,
                            authors=authors,
                            journal=venue or "DBLP",
                            year=year,
                            source_url=ee or url_text,
                            source="dblp",
                        )
                    )
                except Exception:
                    continue
        return papers
    except Exception:
        return None
