from __future__ import annotations

import asyncio, hashlib, logging, os, re, time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx, requests

from ..paper import Paper
from ...utils.async_sync import run_coroutine_sync
from ...utils.author_query_match import (
    normalize_author_names, author_phrase_matches_canonical_line,
    is_author_centric_search, pick_primary_english_author_for_query,
)
from .normalize import (
    _normalize_title_for_dedupe,
    _arxiv_canonical_from_paper,
    plain_query_for_text_apis,
)

logger = logging.getLogger(__name__)


def abbreviate_journal(journal: str | None) -> str | None:
    if not journal:
        return None
    j = str(journal).strip()

    m = re.search(r"\(([A-Z][A-Za-z]{1,12})\)", j)
    if m:
        return m.group(1).upper()

    caps = [w for w in re.findall(r"\b[A-Z]{3,8}\b", j)
            if w not in ("IEEE", "ACM", "SIG", "CVF", "THE", "FOR", "AND", "WITH", "ON", "IN")]
    if caps:
        return caps[0]
    return j

def _venue_appears_in_text(venue: str, text: str) -> bool:
    v =(venue or "").strip().lower()
    return len(v) >= 2 and v in (text or "").lower()


def _merge_paper_link_fields(dst: Paper, src: Paper) -> None:
    sp, dp = (src.pdf_url or "").strip(), (dst.pdf_url or "").strip()
    s_pdf = bool(sp) and sp.lower().split("?", 1)[0].endswith(".pdf")
    d_pdf = bool(dp) and dp.lower().split("?", 1)[0].endswith(".pdf")
    if s_pdf and not d_pdf or not dp and sp:
        dst.pdf_url = sp

    ss, ds = (src.source_url or "").strip(), (dst.source_url or "").strip()
    if not ds and ss:
        dst.source_url = ss

    sd, dd = (src.doi or "").strip(), (dst.doi or "").strip()
    if not dd and sd:
        dst.doi = sd
    sa, da = (src.arxiv_id or "").strip(), (dst.arxiv_id or "").strip()
    if not da and sa:
        dst.arxiv_id = sa



class RateLimiter:
    def __init__(self, *, fixed_delays: dict[str, float]) -> None:
        self._fixed = dict(fixed_delays)
        self._last: dict[str, float] = {}

    def _delay_for(self, source: str) -> float:
        return float(self._fixed.get(source, 0.0))

    async def wait_async(self, source: str) -> None:
        delay = self._delay_for(source)
        if delay <= 0:
            self._last[source] = time.time()
            return
        now = time.time()
        elapsed = now - self._last.get(source, 0.0)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last[source] = time.time()

_DEFAULT_PAPER_SEARCHER_DOWNLOAD_DIR = str(Path(__file__).resolve().parents[3] / "downloads" / "papers")

def _sanitize_author_list_for_query(query: str, raw_authors: Any) -> List[str]:
    if raw_authors is None: return []
    if isinstance(raw_authors, str): seq = [raw_authors]
    elif isinstance(raw_authors, list): seq = [str(x) for x in raw_authors]
    else: return []
    return [str(a).strip() for a in seq if str(a).strip()]



def _has_any_author(p: Paper, want_raw: list) -> bool:
    try:
        names = [str(getattr(a, "name", "") or "").strip() for a in (p.authors or [])
                 if str(getattr(a, "name", "") or "").strip()]
    except Exception: return False
    return bool(names) and any(any(author_phrase_matches_canonical_line(nm, ph) for nm in names) for ph in want_raw)


from .sources.arxiv import (
    search_arxiv as _search_arxiv_src,
    _search_arxiv_by_author_list,
)
from .sources.dblp import (
    search_dblp as _search_dblp_src,
)
from .sources.openalex import (
    search_openalex as _search_openalex_src,
    _search_openalex_works_by_author_async,
)


class PaperSearcher:
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None,
                 download_dir: str = _DEFAULT_PAPER_SEARCHER_DOWNLOAD_DIR, *, httpx_trust_env: bool = True):
        _email = (email or os.getenv("OPENALEX_MAILTO") or os.getenv("NCBI_EMAIL") or "").strip()
        if _email.lower() == "user@example.com": _email = ""
        self.email, self.api_key, self.download_dir = _email, api_key, download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self._rate = RateLimiter(fixed_delays={"arxiv": 0.1, "openalex": 0.15, "dblp": 0.35})
        self._session = requests.Session()
        self._async_client: Optional[httpx.AsyncClient] = None
        self._async_client_loop: Optional[asyncio.AbstractEventLoop] = None
        self.stats = {"arxiv_requests": 0, "dblp_requests": 0, "openalex_requests": 0,
                      "total_results": 0, "downloaded_pdfs": 0}

    def _bump_stat(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    async def _ensure_async_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self._async_client is not None and self._async_client_loop is loop:
            return self._async_client
        if self._async_client is not None:
            try: await self._async_client.aclose()
            except Exception: pass
        self._async_client = httpx.AsyncClient(
            trust_env=False, limits=httpx.Limits(max_keepalive_connections=20, max_connections=80),
            timeout=httpx.Timeout(60.0))
        self._async_client_loop = loop
        return self._async_client

    async def aclose(self) -> None:
        try:
            if self._async_client is not None: await self._async_client.aclose()
        except Exception: pass
        self._async_client = self._async_client_loop = None

    def _user_agent(self) -> str:
        try:
            from ...settings import get_settings
            v = str(getattr(get_settings(), "app_version", "0.1") or "0.1")
        except Exception:
            v = "0.1"
        return f"PaperGraph/{v} (mailto:{self.email})"

    def _openalex_headers(self) -> Dict[str, str]:
        return {"User-Agent": self._user_agent()}

    def _openalex_params(self, base: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(base or {})
        if self.email: out["mailto"] = self.email
        return out

    def _make_paper(self, *, title, authors=None, abstract=None, doi=None, arxiv_id=None,
                    journal=None, year=None, pdf_url=None, source_url=None, citations=0,
                    source="unknown", **extra) -> Paper:
        return Paper(title=title, authors=authors or [], abstract=abstract, doi=doi,
                     arxiv_id=arxiv_id, journal=journal or source, year=year, pdf_url=pdf_url,
                     source_url=source_url, citations=citations, source=source, **extra)

    @staticmethod
    def _resolve_vpj(venue: Optional[str], kwargs: Dict[str, Any]) -> bool:
        vpj = kwargs.get("venue_proceedings_journal")
        return vpj if vpj is not None else bool(venue)

    @staticmethod
    def _paper_matches_venue(paper: Paper, venue: str) -> bool:
        v = venue.lower().strip()
        if not v: return True
        blob = f"{paper.journal or ''} {paper.title or ''}".lower()
        return v in blob

    @staticmethod
    def _paper_matches_venue_proceedings(paper: Paper, venue: str) -> bool:
        raw = (venue or "").strip()
        if not raw: return True
        j = (paper.journal or "").lower()
        t = (paper.title or "").lower()
        return _venue_appears_in_text(raw, j) or _venue_appears_in_text(raw, t)


    async def _rate_limit_async(self, source: str) -> None:
        await self._rate.wait_async(source)

    async def _async_http_get_with_retry(self, url, params, headers, timeout, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                resp = await self._async_client.get(url, params=params, headers=headers, timeout=timeout)
                if resp.status_code == 429:
                    if attempt < max_attempts - 1 and "arxiv" in str(url):
                        await asyncio.sleep(8 + attempt * 8); continue
                    raise RuntimeError(f"HTTP 429: {url}")
                if resp.status_code in (500, 502, 503, 504) and attempt < max_attempts - 1:
                    await asyncio.sleep(4 + attempt * 4); continue
                resp.raise_for_status()
                return resp
            except Exception:
                if attempt < max_attempts - 1: await asyncio.sleep(4 + attempt * 4); continue
                raise

    def _post_process_results(self, all_results: List[Paper], query: str, *, max_results: int,
                              **kwargs: Any) -> List[Paper]:

        raw_authors = kwargs.get("authors") or kwargs.get("author") or []
        if isinstance(raw_authors, str): raw_authors = [raw_authors]
        raw_authors = _sanitize_author_list_for_query(query, raw_authors)
        want_raw = normalize_author_names([str(a).strip() for a in raw_authors if str(a).strip()])
        unique_results = [p for p in all_results if _has_any_author(p, want_raw)] if want_raw else list(all_results)

        unique_results = self._smart_deduplicate(unique_results)
        unique_results = PaperSearcher._collapse_identical_norm_title_prefer_older(unique_results)

        venue_kw = (kwargs.get("venue") or "").strip() or None
        year_from, year_to = kwargs.get("year_from"), kwargs.get("year_to")

        if venue_kw and unique_results:
            matched = [p for p in unique_results if self._paper_matches_venue_proceedings(p, venue_kw)]
            if matched and len(matched) >= max(1, len(unique_results) * 0.15):
                non_matched = [p for p in unique_results if p not in matched]
                unique_results = matched + non_matched

        if year_from is not None:
            unique_results = [p for p in unique_results if (p.year or 0) >= int(year_from)]
        if year_to is not None:
            unique_results = [p for p in unique_results if (p.year or 9999) <= int(year_to)]

        sort_mode = (kwargs.get("sort") or "relevance").lower().strip()
        if sort_mode == "date":
            unique_results.sort(key=lambda p: (p.year or -1, p.citations or 0), reverse=True)
        else:
            unique_results.sort(key=lambda p: (p.citations or 0, p.year or -1), reverse=True)
        return unique_results[:max_results]

    def search(self, query: str, sources: Optional[List[str]] = None, max_results: int = 10, **kwargs) -> List[Paper]:
        return run_coroutine_sync(self.search_async(query, sources=sources, max_results=max_results, **kwargs),
                                  op_name="search")

    async def search_async(self, query: str, sources: Optional[List[str]] = None, max_results: int = 10,
                           **kwargs) -> List[Paper]:
        if "max_results" in kwargs:
            try: max_results = int(kwargs.pop("max_results"))
            except (TypeError, ValueError): kwargs.pop("max_results", None)
        if "sources" in kwargs: sources = kwargs.pop("sources")
        if sources is None: sources = ["arxiv", "dblp", "openalex"]
        sources = [str(s).strip().lower() for s in sources if str(s).strip()] or ["arxiv", "dblp", "openalex"]
        # Tavily 网页结果不作为普通 paper 源；会议官网兜底由显式 proceedings 路径处理
        sources = [s for s in sources if s != "tavily"] or ["arxiv", "dblp", "openalex"]

        raw_authors_kw = kwargs.get("authors") or kwargs.get("author") or []
        if isinstance(raw_authors_kw, str): raw_authors_kw = [raw_authors_kw]
        expanded_authors = normalize_author_names([str(x).strip() for x in (raw_authors_kw or []) if str(x).strip()])
        if expanded_authors: kwargs = {**kwargs, "authors": expanded_authors}
        author_centric = is_author_centric_search(query, expanded_authors)
        _query_before_author = query
        if author_centric:
            eng_q = pick_primary_english_author_for_query(expanded_authors)
            if eng_q: _query_before_author, query = query, eng_q

        cap_factor = max(0.5, min(2.0, float(kwargs.get("per_source_cap_factor") or 1.0)))
        per_src_n = max(5, int(max_results * 2 * cap_factor))
        venue_bound = bool((kwargs.get("venue") or "").strip())
        yf_p = kwargs.get("year_from")
        yt_p = kwargs.get("year_to")
        pinned_year = (
            yf_p is not None
            and yt_p is not None
            and int(yf_p) == int(yt_p)
        )
        if venue_bound and not (plain_query_for_text_apis(query, kwargs) or "").strip():
            if kwargs.get("venue_browse"):
                per_src_n = max(per_src_n, 56)
            else:
                per_src_n = max(per_src_n, 32) if pinned_year else min(per_src_n, 56)

        if kwargs.get("days_back"):
            days = kwargs["days_back"]
            kwargs["date_from"] = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")


        await self._ensure_async_client()
        _src_timeouts = {
            "dblp": float(kwargs.get("dblp_timeout_sec") or 32.0),
            "openalex": float(kwargs.get("openalex_timeout_sec") or kwargs.get("http_timeout_sec") or 45.0),
            "arxiv": float(kwargs.get("arxiv_timeout_sec") or kwargs.get("http_timeout_sec") or 30.0),
        }

        async def _fetch_src(src: str) -> List[Paper]:
            if src == "arxiv":
                if author_centric and expanded_authors:
                    by_author_ax = await _search_arxiv_by_author_list(self, expanded_authors, per_src_n, **kwargs)
                    if by_author_ax: return by_author_ax
                    return await _search_arxiv_src(self, _query_before_author, per_src_n, **kwargs)
                return await _search_arxiv_src(self, query, per_src_n, **kwargs)
            elif src == "openalex":
                if author_centric and expanded_authors:
                    by_author = await _search_openalex_works_by_author_async(self, expanded_authors, per_src_n, **kwargs)
                    if by_author: return by_author
                    return await _search_openalex_src(self, _query_before_author, per_src_n, **kwargs)
                return await _search_openalex_src(self, query, per_src_n, **kwargs)
            elif src == "dblp":
                return await _search_dblp_src(self, query, per_src_n, **kwargs)
            else:
                return []

        async def _run_one(src: str) -> List[Paper]:
            wall = max(5.0, min(60.0, float(_src_timeouts.get(src, 25.0))))
            try: return await asyncio.wait_for(_fetch_src(src), timeout=wall)
            except asyncio.TimeoutError:
                logger.warning("搜索 %s 超时（%.0fs）", src, wall); return []
            except Exception as e:
                logger.warning("搜索 %s 时出错: %s", src, str(e)); return []

        results_by_src = await asyncio.gather(*[_run_one(s) for s in sources])
        all_results: List[Paper] = []
        for src, res in zip(sources, results_by_src):
            all_results.extend(res)
            logger.info("从 %s 获取 %s 篇文献", src, len(res))

        final_results = self._post_process_results(all_results, query, max_results=max_results, **kwargs)
        self._bump_stat("total_results", len(final_results))
        return final_results

    def search_arxiv(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        return run_coroutine_sync(self.search_arxiv_async(query, max_results, **kwargs), op_name="search_arxiv")

    async def search_arxiv_async(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        return await _search_arxiv_src(self, query, max_results, **kwargs)

    async def search_dblp_async(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        return await _search_dblp_src(self, query, max_results, **kwargs)

    def search_openalex(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        return run_coroutine_sync(self.search_openalex_async(query, max_results, **kwargs), op_name="search_openalex")


    async def search_openalex_async(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        return await _search_openalex_src(self, query, max_results, **kwargs)

    @staticmethod
    def _collapse_identical_norm_title_prefer_older(results: List[Paper]) -> List[Paper]:
        if not results: return results
        def _yy(p: Paper) -> int:
            try: yi = int(p.year) if p.year is not None else 9999
            except (TypeError, ValueError): return 9999
            return yi if 1900 <= yi <= 2100 else 9999
        groups: dict[str, list[Paper]] = {}
        for p in results:
            nt = _normalize_title_for_dedupe(p.title)
            if len(nt) >= 22: groups.setdefault(nt, []).append(p)
        drop_ids = {id(pp) for grp in groups.values() if len(grp) > 1
                   for pp in grp if pp is not min(grp, key=_yy)}
        return [p for p in results if id(p) not in drop_ids] if drop_ids else results

    @staticmethod
    def _paper_dedupe_key(paper: Paper) -> str:
        if ax := _arxiv_canonical_from_paper(paper): return f"arxiv:{ax}"
        if doi := (paper.doi or "").strip().lower(): return f"doi:{doi}"
        nt = _normalize_title_for_dedupe(paper.title)
        return f"empty:{id(paper)}" if not nt else "title:" + hashlib.md5(nt.encode("utf-8")).hexdigest()

    @staticmethod
    def _dedupe_quality_tuple(p: Paper) -> tuple:
        abst = (p.abstract or "").strip()
        return (1 if abst else 0, len(abst), int(p.citations or 0), int(p.year or 0))

    def _smart_deduplicate(self, papers: List[Paper]) -> List[Paper]:
        best: Dict[str, Paper] = {}
        for paper in papers:
            k = self._paper_dedupe_key(paper)
            if k not in best: best[k] = paper; continue
            if self._dedupe_quality_tuple(paper) > self._dedupe_quality_tuple(best[k]):
                _merge_paper_link_fields(paper, best[k]); best[k] = paper
            else: _merge_paper_link_fields(best[k], paper)
        return list(best.values())

    def download_pdf(self, paper: Paper) -> Optional[str]:
        if not paper.pdf_url: return None
        try:
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in paper.title[:50])
            filename = f"{paper.arxiv_id or 'paper'}_{safe_title}.pdf"
            file_path = os.path.join(self.download_dir, filename)
            if os.path.exists(file_path): return file_path
            response = self._session.get(paper.pdf_url, timeout=60, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
                self._bump_stat("downloaded_pdfs")
                return file_path
        except Exception: pass
        return None
