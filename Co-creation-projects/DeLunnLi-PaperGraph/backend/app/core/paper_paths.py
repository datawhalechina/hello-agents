
import hashlib
import re

LIBRARY_PDF_ROOT_DIR = "文献库"

_UNCATEGORIZED_ALIASES = frozenset(
    {
        "无分类",
        "无分類",
        "无类目",
        "未归类",
        "不分類",
        "uncategorized",
        "uncategorised",
        "none",
        "n/a",
        "na",
        "null",
        "-",
        "—",
    }
)

def _segment_is_uncategorized_alias(seg: str) -> bool:
    t = (seg or "").strip()
    if not t:
        return True
    if t in _UNCATEGORIZED_ALIASES:
        return True
    tl = t.lower()
    return tl in _UNCATEGORIZED_ALIASES or tl in ("no category", "no cat", "not categorized")

def normalize_library_category_display(display: str | None) -> str:
    raw0 = (display or "").strip()
    if not raw0 or _segment_is_uncategorized_alias(raw0):
        return "未分类"
    parts = [p.strip() for p in raw0.split("/") if p.strip()]
    cleaned: list[str] = []
    for p in parts[:4]:
        s = "".join(ch for ch in p if ch not in '/\\:*?"<>|')
        s = s.strip()
        if len(s) > 32:
            s = s[:32]
        if _segment_is_uncategorized_alias(s):
            s = "未分类"
        if s:
            cleaned.append(s)
    if not cleaned:
        return "未分类"
    return "/".join(cleaned)

def _sanitize_filename(title: str | None, max_len: int = 80) -> str:
    if not title:
        return "untitled"

    safe_chars = []
    for ch in title.strip():
        if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
            safe_chars.append(ch)
        elif ch in (" ", "-", "_", "."):
            safe_chars.append("_")
        else:
            safe_chars.append("_")

    result = "".join(safe_chars)

    result = re.sub(r"_+", "_", result).strip("_")

    if len(result) > max_len:
        result = result[:max_len].rsplit("_", 1)[0]

    return result or "untitled"

def category_slug_for_pdf_dir(display: str | None) -> str:
    seg = (display or "").strip()
    if _segment_is_uncategorized_alias(seg):
        seg = "未分类"
    t = seg or "未分类"
    raw = []
    for ch in t:
        if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
            raw.append(ch)
        elif ch in (" ", "-", "_", "."):
            raw.append("_")
        else:
            raw.append("_")
    s = "".join(raw)
    s = re.sub(r"_+", "_", s).strip("_")[:48]
    if len(s) >= 2:
        return s
    h = hashlib.sha256(t.encode("utf-8")).hexdigest()[:12]
    return f"cat_{h}"

def library_pdf_relative_path(
    category_display: str | None, paper_id: int, title: str | None = None
) -> str:
    t = (category_display or "").strip() or "未分类"
    parts = [p.strip() for p in t.split("/") if p.strip()]
    if not parts:
        parts = ["未分类"]
    segs = [category_slug_for_pdf_dir(p) for p in parts]

    title_part = _sanitize_filename(title)
    short_id = hashlib.sha256(str(paper_id).encode()).hexdigest()[:6]
    filename = f"{title_part}_{short_id}.pdf"

    return "/".join([LIBRARY_PDF_ROOT_DIR] + segs + [filename])
