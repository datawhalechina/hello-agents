
from __future__ import annotations

import contextlib
import logging
import os
import re
from urllib.parse import urlparse

import requests

from .conference_landing_pdf import fetch_pdf_url_from_html_page
from .paper import Paper

_log = logging.getLogger(__name__)

def _is_pkp_ojs_article_download_url(url: str) -> bool:
    return bool(re.search(r"/article/download/\d+/\d+", (url or ""), re.I))

def _is_direct_pdf_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    ul = u.lower().split("?", 1)[0]
    return ul.endswith(".pdf") or _is_pkp_ojs_article_download_url(u)

def _derive_proceedings_pdf_url(source_url: str) -> str | None:
    """Derive PDF URL from known proceedings abstract page URL patterns."""
    u = (source_url or "").strip()
    if not u:
        return None
    # NeurIPS: hash/XXX-Abstract-Conference.html → file/XXX-Paper-Conference.pdf
    m = re.match(r"(.*)/hash/([a-f0-9]+)-Abstract(-\w+)?\.html$", u, re.I)
    if m:
        suffix = (m.group(3) or "-Conference")
        return f"{m.group(1)}/file/{m.group(2)}-Paper{suffix}.pdf"
    # CVF (CVPR/ICCV/ECCV): .../html/PaperName-paper.html → .../papers/PaperName-paper.pdf
    m = re.match(r"(.*)/html/(.+?)\.html$", u, re.I)
    if m and ("/content/" in u.lower()):
        return f"{m.group(1)}/papers/{m.group(2)}.pdf"
    # OpenReview: forum?id=X → pdf?id=X
    if "openreview.net/forum" in u:
        return re.sub(r"/forum\?id=", "/pdf?id=", u)
    # Generic: .html → .pdf
    if u.lower().endswith(".html"):
        return re.sub(r"\.html$", ".pdf", u, flags=re.I)
    return None


def _pdf_download_candidates(paper: Paper, email: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def _push(u: str | None) -> None:
        s = (u or "").strip()
        if s and s.lower().startswith(("http://", "https://")):
            low = s.lower()
            if low not in seen:
                seen.add(low)
                out.append(s)

    pu = (getattr(paper, "pdf_url", None) or "").strip()
    if pu and _is_direct_pdf_url(pu):
        _push(pu)

    su = (getattr(paper, "source_url", None) or "").strip()
    if su and _is_direct_pdf_url(su):
        _push(su)

    try:
        resolved = resolve_paper_pdf_url(paper, email=email)
        _push(resolved)
    except Exception as ex:
        _log.warning("resolve_paper_pdf_url 异常（已忽略）: %s", ex, exc_info=True)

    # Last resort: derive PDF URL from abstract page URL pattern
    if not out and su:
        derived = _derive_proceedings_pdf_url(su)
        _push(derived)

    return out

def _headers_for_pdf_get(url: str, paper: Paper, email: str) -> dict:
    mail = (email or "").strip()
    ref = (getattr(paper, "source_url", None) or "").strip()

    if not ref or not ref.lower().startswith("http"):
        try:
            pr = urlparse(url)
            if pr.scheme and pr.netloc:
                ref = f"{pr.scheme}://{pr.netloc}/"
        except ValueError:
            ref = ""

    ua = f"PaperGraph/0.3 (mailto:{mail})" if mail else "PaperGraph/0.3"
    h = {
        "User-Agent": ua,
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
    }
    if ref and ref.lower().startswith("http"):
        h["Referer"] = ref[:2048]
    return h

def _file_looks_like_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False

def _normalize_doi_url(doi: str) -> str | None:
    d = (doi or "").strip()
    if not d:
        return None
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I).strip().rstrip("/")
    return f"https://doi.org/{d}" if d else None

def _should_probe_html_for_pdf(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u.startswith(("http://", "https://")):
        return False
    if _is_pkp_ojs_article_download_url(u):
        return False
    return not re.search(r"openalex\.org/(?:w\d+|works/)", u)

def resolve_paper_pdf_url(paper: Paper, email: str = "") -> str | None:
    u = (getattr(paper, "pdf_url", None) or "").strip()
    su = (getattr(paper, "source_url", None) or "").strip()
    doi_u = _normalize_doi_url(getattr(paper, "doi", None) or "")

    if u and _is_direct_pdf_url(u):
        return u

    from app.core.search import _arxiv_canonical_from_paper, _arxiv_pdf_url_from_id

    ax = _arxiv_pdf_url_from_id(_arxiv_canonical_from_paper(paper))
    if ax:
        return ax

    # Recover arXiv PDF URL from DOI/source URL.
    if not ax:
        for field_val in (getattr(paper, "doi", None) or "", getattr(paper, "source_url", None) or ""):
            m = re.search(r"arxiv/([\d.]+)", str(field_val), re.I)
            if m:
                ax = f"https://arxiv.org/pdf/{m.group(1)}"
                return ax

    probe_candidates: list[str] = []
    seen: set[str] = set()
    for cand in (u, su, doi_u):
        if cand and _should_probe_html_for_pdf(cand):
            norm = cand.rstrip("/").lower()
            if norm not in seen:
                seen.add(norm)
                probe_candidates.append(cand)

    for cand_url in probe_candidates:
        try:
            got = fetch_pdf_url_from_html_page(cand_url, email=email)
            if got:
                return got
        except Exception:
            continue

    # OpenReview forum pages expose PDFs at /pdf?id=...
    if su and "openreview.net/forum" in su:
        return re.sub(r"/forum\?id=", "/pdf?id=", su)

    # Some DOI URLs redirect directly to open-access PDFs.
    if doi_u:
        try:
            mail = (email or "").strip()
            ua = f"PaperGraph/0.3 (mailto:{mail})" if mail else "PaperGraph/0.3"
            headers = {"User-Agent": ua, "Accept": "application/pdf"}
            with requests.get(doi_u, timeout=30, headers=headers, allow_redirects=True, stream=True) as r:
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
                    return doi_u
        except Exception:
            pass

    return None

def _cleanup_temp_file(tmp_path: str) -> None:
    with contextlib.suppress(OSError):
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)

def download_paper_pdf_to_path(paper: Paper, dest_abspath: str, email: str = "") -> bool:
    try:
        urls = _pdf_download_candidates(paper, email=email)
        if not urls:
            return False

        with contextlib.suppress(OSError):
            os.makedirs(os.path.dirname(dest_abspath) or ".", exist_ok=True)

        for url in urls:
            tmp = dest_abspath + ".part"
            try:
                headers = _headers_for_pdf_get(url, paper, email)
                with requests.get(url, timeout=90, stream=True, headers=headers, allow_redirects=True) as r:
                    if r.status_code != 200:
                        continue

                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)

                if os.path.getsize(tmp) < 256 or not _file_looks_like_pdf(tmp):
                    _cleanup_temp_file(tmp)
                    continue

                os.replace(tmp, dest_abspath)
                return True

            except (OSError, requests.RequestException):
                _cleanup_temp_file(tmp)
                continue

        return False

    except Exception as ex:
        _log.warning("download_paper_pdf_to_path 异常: %s", ex, exc_info=True)
        _cleanup_temp_file(dest_abspath + ".part")
        return False
