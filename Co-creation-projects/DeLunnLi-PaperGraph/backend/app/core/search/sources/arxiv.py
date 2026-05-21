from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import feedparser

from ...author import Author
from ...paper import Paper
from ..normalize import (
    _arxiv_pdf_url_from_id,
    sanitize_search_keyword_list,
    split_query_phrases,
)
from ..paper_searcher import _sanitize_author_list_for_query
from ....utils.common import text_has_cjk

logger = logging.getLogger(__name__)


def arxiv_category_clause(categories: list[str | None]) -> str | None:
    if not categories:
        return None
    cats = [str(c).strip() for c in categories if c and str(c).strip()]
    if not cats:
        return None
    if len(cats) == 1:
        return f"cat:{cats[0]}"
    return "+OR+".join(f"cat:{c}" for c in cats)


def arxiv_query_string_from_kwargs(query: str, kwargs: dict[str, Any]) -> str:
    lk = sanitize_search_keyword_list(kwargs.get("llm_keywords"))
    if not lk:
        return (query or "").strip()
    if len(lk) >= 2:
        q0 = (query or "").strip()
        return q0 if q0 else str(lk[0]).strip()
    one = str(lk[0]).strip()
    if len(one) > 480:
        one = one[:480].rsplit(" ", 1)[0].strip()
    return one or ((query or "").strip())


def _arxiv_comment_from_feed_entry(entry: Any) -> str:
    for key in ("arxiv_comment", "comment"):
        v = getattr(entry, key, None) or (
            entry.get(key) if hasattr(entry, "get") else None
        )
        if isinstance(v, str) and v.strip():
            return v.replace("\n", " ").strip()
    return ""


def _arxiv_submitted_date_clause(kwargs: Dict[str, Any]) -> Optional[str]:
    if not bool(kwargs.get("arxiv_use_submitted_date", False)):
        return None
    db = kwargs.get("days_back")
    if db is None:
        return None
    try:
        days = int(db)
    except (TypeError, ValueError):
        return None
    if days <= 0:
        return None
    end = datetime.now()
    start = end - timedelta(days=days)
    return (
        f"submittedDate:[{start.strftime('%Y%m%d')}0000"
        f"+TO+{end.strftime('%Y%m%d')}2359]"
    )


def _arxiv_entry_published_naive(entry: Any) -> Optional[datetime]:
    t = (
        (entry.get("published_parsed") or entry.get("updated_parsed"))
        if hasattr(entry, "get")
        else (
            getattr(entry, "published_parsed", None)
            or getattr(entry, "updated_parsed", None)
        )
    )
    if not t:
        return None
    try:
        return datetime(*t[:6])
    except (TypeError, ValueError):
        return None


def _arxiv_clause_for_phrase(searcher, phrase: str, style: str) -> str:
    p = (phrase or "").replace('"', " ").strip()
    if not p:
        return ""
    if style == "ti_abs":
        return f'all:"{p}"' if " " in p else f'(ti:"{p}"+OR+abs:"{p}")'
    return f'all:"{p}"' if " " in p else f"all:{quote_plus(p)}"


def _arxiv_query_part(
    searcher, query: str, style: str = "all", *, max_phrases: int = 14
) -> Optional[str]:
    q = (query or "").strip().replace('"', " ")
    if not q:
        return None
    st = style if style in ("all", "ti_abs") else "all"
    phrases = [
        p.replace('"', " ").strip()
        for p in split_query_phrases(q)
        if p.strip()
    ][: max(1, int(max_phrases))]
    clauses = [
        c
        for c in (_arxiv_clause_for_phrase(searcher, p, st) for p in phrases)
        if c
    ]
    if len(clauses) >= 2:
        return "(" + "+OR+".join(clauses) + ")"
    if len(clauses) == 1:
        return clauses[0]
    q0 = phrases[0] if phrases else q
    return _arxiv_clause_for_phrase(searcher, q0, st) or None


def _arxiv_build_search_query(
    searcher, query: str, venue: Optional[str], **kwargs
) -> str:
    style = kwargs.get("arxiv_query_style", "ti_abs").lower()
    if style not in ("all", "ti_abs"):
        style = "all"
    v = (str(venue).strip().replace('"', " ")) if venue else ""
    parts: List[str] = []
    cat_c = arxiv_category_clause(kwargs.get("arxiv_categories"))
    if cat_c:
        parts.append(cat_c)
    raw_authors = kwargs.get("authors") or kwargs.get("author") or []
    if isinstance(raw_authors, str):
        raw_authors = [raw_authors]
    if isinstance(raw_authors, list):
        raw_authors = _sanitize_author_list_for_query(query, raw_authors)
        aus = [
            str(x).strip().replace('"', " ")
            for x in raw_authors
            if str(x).strip()
        ][:3]
    else:
        aus = []
    if aus:
        author_clauses: List[str] = []
        for a in aus:
            a0 = a.strip()
            if not a0:
                continue
            author_clauses.extend([f'au:"{a0}"'])
        author_clauses = list(dict.fromkeys([c for c in author_clauses if c]))[:6]
        if author_clauses:
            inner = "+OR+".join(author_clauses)
            parts.append(
                f"({inner})" if len(author_clauses) > 1 else author_clauses[0]
            )
    max_or = int(kwargs.get("arxiv_max_or_clauses", 14) or 14)
    q_part = _arxiv_query_part(searcher, query, style, max_phrases=max(1, max_or))
    if q_part:
        parts.append(q_part)
    if v:
        if " " in v:
            parts.append(f'all:"{v}"')
        elif style == "ti_abs":
            vc = _arxiv_clause_for_phrase(searcher, v, "ti_abs")
            if vc:
                parts.append(vc)
        else:
            parts.append(f"all:{quote_plus(v)}")
    if not parts:
        return "cat:cs"
    elif len(parts) == 1:
        expr = parts[0]
    else:
        expr = "+AND+".join(parts)
    date_clause = _arxiv_submitted_date_clause(kwargs)
    return f"{expr}+AND+{date_clause}" if date_clause else expr


def _filter_arxiv_entries_by_days_back(
    searcher, entries: List[Any], days_back: int
) -> List[Any]:
    cutoff = datetime.now() - timedelta(days=days_back)
    return [
        e
        for e in entries
        if (pub := _arxiv_entry_published_naive(e)) is None or pub >= cutoff
    ]


def _arxiv_paper_dedupe_key(searcher, p: Paper) -> str:
    aid = (p.arxiv_id or "").strip()
    if aid:
        return re.sub(r"v\d+$", "", aid, flags=re.I).lower()
    return hashlib.md5(
        (p.title or "").strip().lower().encode("utf-8", errors="ignore")
    ).hexdigest()[:20]


async def _search_arxiv_by_keyword_list_async(
    searcher, query: str, max_results: int, keywords: List[str], **kwargs: Any
) -> List[Paper]:
    n = max(1, len(keywords))
    per = max(8, min(60, (max_results + n - 1) // n + 8))
    merged, seen = [], set()
    for kw in keywords[:16]:
        kwt = str(kw).strip()
        if not kwt:
            continue
        for p in await search_arxiv(
            searcher, query, per, **{**kwargs, "llm_keywords": [kwt]}
        ):
            dk = _arxiv_paper_dedupe_key(searcher, p)
            if dk in seen:
                continue
            seen.add(dk)
            merged.append(p)
        if len(merged) >= max_results:
            break
    return merged[:max_results]


async def _search_arxiv_by_author_list(
    searcher, author_names: list[str], max_results: int, **kwargs
) -> list[Paper]:
    if not author_names:
        return []
    merged, seen = [], set()
    for name in author_names[:3]:
        nm = name.strip()
        if not nm or text_has_cjk(nm):
            continue
        akw = dict(kwargs)
        akw["authors"] = [nm]
        akw["llm_keywords"] = []
        for p in await search_arxiv(searcher, "", max(5, max_results), **akw):
            dk = _arxiv_paper_dedupe_key(searcher, p)
            if dk in seen:
                continue
            seen.add(dk)
            merged.append(p)
        if len(merged) >= max_results:
            break
    return merged[:max_results]


async def search_arxiv(
    searcher, query: str, max_results: int = 10, **kwargs
) -> List[Paper]:
    await searcher._ensure_async_client()
    await searcher._rate_limit_async("arxiv")

    id_list0 = str(kwargs.get("arxiv_id_list") or "").strip()
    lk0 = sanitize_search_keyword_list(kwargs.get("llm_keywords"))
    venue_bound = bool((kwargs.get("venue") or "").strip())
    if not id_list0 and len(lk0) >= 2 and not venue_bound:
        return await _search_arxiv_by_keyword_list_async(
            searcher, query, max_results, lk0, **kwargs
        )

    base_url = "https://export.arxiv.org/api/query"
    venue = (kwargs.get("venue") or "").strip() or None
    vpj = searcher._resolve_vpj(venue, kwargs)
    include_venue_in_arxiv_query = bool(
        venue and (not vpj) and bool(kwargs.get("strict_venue_match"))
    )
    id_list = str(kwargs.get("arxiv_id_list") or "").strip()
    if id_list:
        params = {
            "id_list": id_list,
            "start": 0,
            "max_results": min(max_results, 30000),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    else:
        q_arxiv = arxiv_query_string_from_kwargs(query, kwargs)
        arxiv_kw = {k: v for k, v in kwargs.items() if k != "venue"}
        search_expr = _arxiv_build_search_query(
            searcher,
            q_arxiv,
            venue if include_venue_in_arxiv_query else None,
            **arxiv_kw,
        )
        sort_by = (
            "relevance"
            if (kwargs.get("sort") or "date").lower().strip() == "relevance"
            else "submittedDate"
        )
        params = {
            "search_query": search_expr,
            "start": 0,
            "max_results": min(max_results, 30000),
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

    headers = {"User-Agent": searcher._user_agent()}
    req_timeout = float(kwargs.get("http_timeout_sec", 30.0))
    max_attempts = max(1, min(10, int(kwargs.get("http_max_attempts", 4))))
    resp = await searcher._async_http_get_with_retry(
        base_url,
        params=params,
        headers=headers,
        timeout=req_timeout,
        max_attempts=max_attempts,
    )
    feed = feedparser.parse(resp.content or b"")
    entries = list(getattr(feed, "entries", []) or [])

    if not entries and not id_list:
        from ....settings import get_settings

        if bool(getattr(get_settings(), "arxiv_or_retry_on_empty", True)):
            or_expr = search_expr.replace("+AND+", "+OR+")
            if or_expr != search_expr:
                await searcher._rate_limit_async("arxiv")
                or_params = dict(params)
                or_params["search_query"] = or_expr
                resp2 = await searcher._async_http_get_with_retry(
                    base_url,
                    params=or_params,
                    headers=headers,
                    timeout=req_timeout,
                    max_attempts=min(max_attempts, 2),
                )
                entries = list(
                    getattr(feedparser.parse(resp2.content or b""), "entries", [])
                    or []
                )

    db_days = kwargs.get("days_back")
    if db_days:
        try:
            if int(db_days) > 0:
                entries = _filter_arxiv_entries_by_days_back(
                    searcher, entries, int(db_days)
                )
        except (TypeError, ValueError):
            pass

    papers: List[Paper] = []
    for entry in entries:
        try:
            arxiv_id = entry.get("id", "").split("/")[-1].replace("abs/", "")
            title = entry.get("title", "Unknown").replace("\n", " ")
            authors = [
                Author(name=a.get("name", ""))
                for a in (entry.get("authors", []) or [])
                if a.get("name")
            ]
            abstract = (entry.get("summary", "") or "").replace("\n", " ")
            tags = entry.get("tags", [])
            keywords = [tag.get("term", "") for tag in tags if tag.get("term")]
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            year = published[0] if published else None
            links = entry.get("links", [])
            pdf_url = abs_url = None
            for link in links:
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                elif link.get("type") == "text/html":
                    abs_url = link.get("href")
            if not pdf_url and arxiv_id:
                pdf_url = _arxiv_pdf_url_from_id(
                    re.sub(r"v\d+$", "", arxiv_id.strip(), flags=re.I)
                )
            primary_category = tags[0].get("term", "") if tags else ""
            papers.append(
                searcher._make_paper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    arxiv_id=arxiv_id,
                    journal=f"arXiv:{primary_category}" if primary_category else "arXiv",
                    year=year,
                    pdf_url=pdf_url,
                    source_url=abs_url or f"https://arxiv.org/abs/{arxiv_id}",
                    keywords=keywords,
                    source="arxiv",
                    notes=_arxiv_comment_from_feed_entry(entry) or None,
                )
            )
        except Exception:
            continue

    searcher._bump_stat("arxiv_requests")
    return papers
