
from __future__ import annotations

import re

from ...core.paper_paths import normalize_library_category_display
from ...utils import parse_llm_json, tokenize_for_keywords, truncate_text

def clip_text(text: str | None, n: int) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    t = t[:n]
    while t:
        try:
            t.encode('utf-8')
            break
        except UnicodeEncodeError:
            t = t[:-1]
    return t

def dedupe_tags(tags: list[str], max_tags: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        s = str(t).strip()
        k = s.lower()
        if s and k not in seen:
            out.append(s)
            seen.add(k)
        if len(out) >= max_tags:
            break
    return out

def clean_library_tag(tag: str) -> str | None:
    s = str(tag).strip()[:24]
    if not s:
        return None
    if any(c in s for c in '|\\:*?"<>/'):
        return None
    return s

def sanitize_major_name(raw: str) -> str | None:
    t = str(raw or "").strip()
    if not t or len(t) > 16:
        return None
    t = "".join(ch for ch in t if ch not in '/\\:*?"<>|')
    t = t.strip()
    if len(t) < 2:
        return None
    return t[:10]

def nearest_major_in(raw: str, whitelist: tuple[str, ...]) -> str:
    s = (raw or "").strip()
    if "/" not in s:
        s = normalize_library_category_display(s)
    if s in whitelist:
        return s
    for m in whitelist:
        if m and (m in s or s in m):
            return m
    if "未分类" in whitelist:
        return "未分类"
    return whitelist[0] if whitelist else "未分类"

def parse_taxonomy_majors(raw: str) -> list[str | None]:
    d = parse_llm_json(raw)
    if not isinstance(d, dict):
        return None
    arr = d.get("majors")
    if not isinstance(arr, list):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for x in arr:
        c = sanitize_major_name(str(x))
        if not c:
            continue
        k = c.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    if "未分类" not in out:
        out.append("未分类")
    if len(out) < 4:
        return None
    return out[:28]

def top_similar_categories(seed: str, categories: list[str], k: int = 18) -> list[str]:
    cats = [str(x).strip() for x in categories if str(x).strip()]
    if len(cats) <= k:
        return cats
    tokens = tokenize_for_keywords(seed)
    if not tokens:
        return cats[:k]
    scored: list[tuple[float, str]] = []
    for c in cats:
        ct = tokenize_for_keywords(c)
        inter = len(tokens & ct)
        if inter == 0:
            continue
        union = len(tokens | ct) or 1
        scored.append((inter / union, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [c for _, c in scored[:k]]
    if len(picked) < max(8, k // 2):
        for c in cats:
            if c not in picked:
                picked.append(c)
            if len(picked) >= k:
                break
    return picked[:k]

def prioritize_reader_context(block: str, max_chars: int) -> str:
    b = (block or "").strip()
    if len(b) <= max_chars:
        return b

    def grab(label_pat: str, cap: int) -> str:
        m = re.search(label_pat, b, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        seg = (m.group(1) if m.groups() else m.group(0)).strip()
        return truncate_text(seg, cap, suffix="…")

    abstract = grab(
        r"(?:摘要|Abstract)\s*[:：]?\s*([\s\S]{20,}?)(?=\n\s*(?:相关工作|Related\s*work|关键词|Key\s*words|PDF|【)|\Z)",
        1400,
    )
    related = grab(
        r"(?:相关工作|Related\s*work)\s*[:：]?\s*([\s\S]{20,}?)(?=\n\s*(?:关键词|Key\s*words|参考文献|PDF|【)|\Z)",
        1200,
    )
    artifact = grab(
        r"(【结构化阅读档案[\s\S]{80,}?)(?=\n【PDF 正文|\Z)",
        min(2600, max(1400, max_chars - 900)),
    )
    ref_blob = grab(
        r"【参考文献区 PDF 原文摘录[^\n]*\n([\s\S]{10,}?)(?=\n【结构化阅读档案|\n【PDF 正文|\Z)",
        min(10000, max(2400, max_chars - 1200)),
    )
    budget = max_chars - len(abstract) - len(related) - len(artifact) - len(ref_blob) - 30
    if budget < 400:
        budget = 400
    head = truncate_text(b, budget, suffix="…")
    parts = [p for p in (abstract, related, artifact, ref_blob, head) if p]
    merged = "\n\n---\n\n".join(parts)
    return truncate_text(merged, max_chars, suffix="…")

def clip_reader_history(hist: str, max_chars: int) -> str:
    h = (hist or "").strip()
    if len(h) <= max_chars:
        return h
    lines = h.splitlines()
    out: list[str] = []
    size = 0
    for line in reversed(lines):
        if size + len(line) + 1 > max_chars:
            break
        out.append(line)
        size += len(line) + 1
    return "\n".join(reversed(out)) if out else truncate_text(h, max_chars, suffix="…")
