
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import requests

_ABS_PDF_HTTP = re.compile(r"https?://[^'\"<>\s]+?\.pdf", re.I)

_HREF_PDF = re.compile(
    r'(?:href|src|data-href)\s*=\s*(["\'])([^"\']+?\.pdf)\1',
    re.I,
)

_META_CONTENT_PDF = re.compile(
    r'<meta[^>]+(?:property|name)\s*=\s*["\']?(?:pdf_url|citation_pdf_url|og:pdf_url)["\']?[^>]+content\s*=\s*["\']([^"\']+?\.pdf)["\']',
    re.I | re.S,
)
_META_CONTENT_PDF_ALT = re.compile(
    r'<meta[^>]+content\s*=\s*["\']([^"\']+?\.pdf)["\'][^>]+(?:property|name)\s*=\s*["\']?(?:pdf_url|citation_pdf_url|og:pdf_url)["\']?',
    re.I | re.S,
)
_GENERIC_CONTENT_PDF = re.compile(
    r'content\s*=\s*["\']([^"\']+?\.pdf)["\']',
    re.I,
)

_OJS_VIEW_OR_DL = re.compile(
    r'(?:href|data-href)\s*=\s*(["\'])([^"\']*?/article/(?:view|download)/\d+/\d+[^"\']*)\1',
    re.I,
)

def _is_relative_pdf_path(rel: str) -> bool:
    s = (rel or "").strip()
    if not s or s.startswith("//"):
        return False
    low = s.lower()
    return not low.startswith(("http://", "https://", "javascript:", "mailto:", "#"))

def _same_site_pdf_preference(base_url: str, candidates: list[str]) -> str | None:
    if not candidates:
        return None
    try:
        base_host = (urlparse(base_url).netloc or "").lower().removeprefix("www.")
    except ValueError:
        base_host = ""
    for c in candidates:
        try:
            h = (urlparse(c).netloc or "").lower().removeprefix("www.")
            if base_host and h == base_host:
                return c
        except ValueError:
            continue
    return candidates[0]

def fetch_pdf_url_from_html_page(
    url: str,
    email: str = "",
    timeout: int = 35,
    max_bytes: int = 800_000,
) -> str | None:
    u0 = (url or "").strip()
    if not u0.lower().startswith(("http://", "https://")):
        return None

    mail = (email or "").strip()
    ua = f"PaperGraph/0.3 (mailto:{mail})" if mail else "PaperGraph/0.3"
    headers = {"User-Agent": ua}

    try:
        with requests.get(u0, timeout=timeout, headers=headers, stream=True) as r:
            if r.status_code != 200:
                return None
            buf = bytearray()
            for chunk in r.iter_content(65536):
                if chunk:
                    buf.extend(chunk)
                    if len(buf) >= max_bytes:
                        break
        text = bytes(buf).decode("utf-8", errors="ignore")
    except (requests.RequestException, OSError, ValueError):
        return None

    found: list[str] = []
    seen: set[str] = set()

    def _add_url(raw_url: str) -> None:
        s = raw_url.strip().split("?", 1)[0]
        if not s.lower().endswith(".pdf"):
            return
        low = s.lower()
        if low not in seen:
            seen.add(low)
            found.append(s)

    try:
        for m in _ABS_PDF_HTTP.finditer(text):
            _add_url(m.group(0))

        for m in _HREF_PDF.finditer(text):
            path = m.group(2).strip()
            if path.startswith("//"):
                _add_url(urljoin(u0, path))
            elif path.lower().startswith(("http://", "https://")):
                _add_url(path)
            elif _is_relative_pdf_path(path):
                _add_url(urljoin(u0, path))

        # Meta content="..." PDF URLs (e.g., NeurIPS proceedings abstract pages)
        if not found:
            for pat in (_META_CONTENT_PDF, _META_CONTENT_PDF_ALT):
                for m in pat.finditer(text):
                    path = m.group(1).strip()
                    if path.lower().startswith(("http://", "https://")):
                        _add_url(path)
                    elif _is_relative_pdf_path(path):
                        _add_url(urljoin(u0, path))

        if not found:
            for m in _GENERIC_CONTENT_PDF.finditer(text):
                path = m.group(1).strip()
                if path.lower().startswith(("http://", "https://")):
                    _add_url(path)
                elif _is_relative_pdf_path(path):
                    _add_url(urljoin(u0, path))

        if not found:
            for m in _OJS_VIEW_OR_DL.finditer(text):
                path = m.group(2).strip()
                abs_u = urljoin(u0, path)
                if "/article/view/" in abs_u:
                    abs_u = abs_u.replace("/article/view/", "/article/download/", 1)
                low = abs_u.lower()
                if "citationstylelanguage" in low or low in seen:
                    continue
                seen.add(low)
                found.append(abs_u)
    except re.error:
        return None

    if not found:
        return None
    return _same_site_pdf_preference(u0, found)
