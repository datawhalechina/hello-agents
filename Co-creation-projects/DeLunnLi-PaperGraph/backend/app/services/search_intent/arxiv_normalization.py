
from __future__ import annotations

from ...utils.common import dedupe_strings_preserve_order

_ALLOWED_ARXIV_CAT_REST = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")

def _valid_arxiv_category_token(s: str) -> bool:
    t = (s or "").strip()
    if len(t) > 56 or len(t) < 2:
        return False
    if ".." in t or t.startswith(".") or t.endswith("."):
        return False
    first = t[0]
    if not ("A" <= first <= "Z" or "a" <= first <= "z"):
        return False
    return all(c in _ALLOWED_ARXIV_CAT_REST for c in t[1:])

def sanitize_arxiv_categories(raw: list[str | None]) -> list[str]:
    stripped = [str(x).strip() for x in raw or []]
    return dedupe_strings_preserve_order([t for t in stripped if _valid_arxiv_category_token(t)], max_n=12)

def extract_arxiv_id_from_org_url(t: str) -> str | None:
    low = t.lower()
    key = "arxiv.org"
    idx = low.find(key)
    if idx < 0:
        return None
    after = t[idx + len(key) :]
    la = after.lower()
    for pref in ("/abs/", "/pdf/"):
        p = la.find(pref)
        if p < 0:
            continue
        seg = after[p + len(pref) :]
        seg = seg.split("?", 1)[0].split("#", 1)[0].strip().rstrip("/")
        return seg if seg else None
    return None

def strip_trailing_arxiv_version(u: str) -> str:
    s = u.strip().lower()
    idx = s.rfind("v")
    if idx > 0 and idx < len(s) - 1 and s[idx + 1 :].isdigit():
        return s[:idx]
    return s

def parse_new_style_arxiv_id(t: str) -> str | None:
    u = strip_trailing_arxiv_version(t)
    if len(u) < 10 or "." not in u:
        return None
    dot = u.find(".")
    if dot != 4:
        return None
    ym, tail = u[:4], u[5:]
    if not ym.isdigit() or not tail.isdigit() or not (4 <= len(tail) <= 5):
        return None
    return u

def parse_legacy_arxiv_id(t: str) -> str | None:
    u = strip_trailing_arxiv_version(t)
    slash = u.find("/")
    if slash <= 0:
        return None
    prefix, digits = u[:slash], u[slash + 1 :]
    if len(digits) != 7 or not digits.isdigit():
        return None
    if not prefix or not all(ch.islower() or ch in ".-" for ch in prefix):
        return None
    return u

def sanitize_arxiv_id_list(raw: list[str | None]) -> list[str]:
    out: list[str] = []
    for x in raw or []:
        t = str(x).strip().replace(" ", "")
        if not t:
            continue
        extracted = extract_arxiv_id_from_org_url(t)
        if extracted is not None:
            t = extracted
        t = t.replace("arXiv:", "").strip()
        nid = parse_new_style_arxiv_id(t)
        if nid is not None:
            out.append(nid)
            continue
        lid = parse_legacy_arxiv_id(t)
        if lid is not None:
            out.append(lid)
    return dedupe_strings_preserve_order(out, max_n=8)
