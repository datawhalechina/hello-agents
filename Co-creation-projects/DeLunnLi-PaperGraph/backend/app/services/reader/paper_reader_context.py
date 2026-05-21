
from __future__ import annotations

import os
import re
import sqlite3
import time
from typing import Any

def extract_pdf_text_full(abspath: str | None) -> str:
    if not abspath or not os.path.isfile(abspath):
        return ""
    best = ""

    # Priority 1: pymupdf4llm Markdown — preserves tables, headings, structure
    try:
        import pymupdf4llm
        best = (pymupdf4llm.to_markdown(abspath) or "").strip()
    except Exception:
        pass

    # Priority 2: fitz plain text — only as fallback if Markdown is too short
    try:
        import fitz
        doc = fitz.open(abspath)
        pages: list[str] = []
        for page in doc:
            t = page.get_text("text")
            if t:
                pages.append(t.strip())
        doc.close()
        fitz_text = "\n\n".join(pages).strip()

        # Prefer Markdown even if shorter (preserves tables), but fall back if
        # Markdown is clearly broken (< 30% of fitz length and < 500 chars)
        if not best or (len(best) < 500 and len(fitz_text) > len(best) * 3):
            best = fitz_text
    except Exception:
        pass

    if len(best) < 200:
        try:
            import fitz
            doc = fitz.open(abspath)
            blocks: list[str] = []
            for page in doc:
                for block in page.get_text("blocks") or []:
                    if len(block) >= 5 and block[4].strip():
                        blocks.append(str(block[4]).strip())
            doc.close()
            block_text = "\n".join(blocks).strip()
            if len(block_text) > len(best):
                best = block_text
        except Exception:
            pass
    return best


def extract_pdf_tables_markdown(abspath: str | None) -> str:
    """Extract tables from PDF as Markdown. Uses fitz's built-in table detection first,
    then falls back to pymupdf4llm."""
    if not abspath or not os.path.isfile(abspath):
        return ""
    tables: list[str] = []

    # Method 1: fitz page.find_tables() — best for structured tables
    try:
        import fitz
        doc = fitz.open(abspath)
        for page in doc:
            try:
                tabs = page.find_tables()
            except Exception:
                tabs = None
            if tabs:
                for tab in tabs:
                    try:
                        md = tab.to_markdown()
                        if md and "|" in str(md) and len(str(md)) > 20:
                            tables.append(str(md).strip())
                    except Exception:
                        pass
        doc.close()
    except Exception:
        pass

    if not tables:
        # Method 2: pymupdf4llm Markdown — parses full doc
        try:
            import pymupdf4llm
            md = (pymupdf4llm.to_markdown(abspath) or "").strip()
            for m in re.finditer(r"(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+)", md):
                tables.append(m.group(1).strip())
        except Exception:
            pass

    if not tables:
        # Method 3: fitz text blocks — last resort
        try:
            import fitz
            doc = fitz.open(abspath)
            for page in doc:
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    lines = block.get("lines", [])
                    if len(lines) < 2:
                        continue
                    spans_by_line = [[s["text"] for s in ln["spans"]] for ln in lines]
                    # Tabular data typically has 3+ aligned columns
                    ncols = min(len(spans) for spans in spans_by_line)
                    if ncols < 3:
                        continue
                    # Build markdown table by columns
                    cols = [[] for _ in range(ncols)]
                    for spans in spans_by_line:
                        for j in range(ncols):
                            cols[j].append(spans[j].strip())
                    md_rows = [" | ".join(cols[i]) for i in range(ncols)]
                    # Reformat: each original row → one markdown row
                    nrows = len(cols[0])
                    result = [" | ".join(str(cols[c][r]) for c in range(ncols)) for r in range(nrows)]
                    result.insert(1, " | ".join("---" for _ in range(ncols)))
                    tables.append("\n".join(result))
            doc.close()
        except Exception:
            pass

    return "\n\n".join(tables) if tables else ""

def preprocess_pdf_text_for_reference_blob(blob: str) -> str:
    try:
        import ftfy
        return ftfy.fix_text(blob or "")
    except ImportError:
        return (blob or "").replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")

def soft_unwrap_reference_section_newlines(blob: str) -> str:
    s = preprocess_pdf_text_for_reference_blob(blob or "")

    s = re.sub(r",\s*\n(?!\n)", ", ", s)

    s = re.sub(r"(?<=[,.])\s*\n(?!\s*\n)\s*(?=[A-Za-z0-9(\u4e00-\u9fff])", " ", s)
    s = re.sub(r"\n{4,}", "\n\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def normalize_saved_reference_entry(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"([A-Za-z]{2,})-\s*\r?\n\s*([A-Za-z]{2,})", r"\1\2", s)
    s = re.sub(r"([A-Za-z]{2,})-\s{1,3}([A-Za-z]{2,})", r"\1\2", s)
    s = re.sub(r"[\s\u00a0\u2000-\u200b\u202f\u2060\ufeff]+", " ", s).strip()
    return s

_REF_SECTION = re.compile(
    r"(?:^|\n)\s*(?:"
    r"References|REFERENCES|Bibliography|BIBLIOGRAPHY|"
    r"参考文献|引用文献|參考文獻"
    r")\s*\n",
    re.MULTILINE,
)

def extract_references_section_raw_from_pdf_text(pdf_text: str) -> str:
    t = (pdf_text or "").strip()
    if len(t) < 120:
        return ""
    m = _REF_SECTION.search(t)
    body = t[m.end():].strip() if m else t[-min(len(t), 48000):]
    body = soft_unwrap_reference_section_newlines(body)
    return (body or "").strip()

_REF_FALLBACK_ENTRY_HEAD = re.compile(
    r"^(?:\[\d{1,3}\]\s*)?(?:[A-Z][a-zA-Z'\u2019\-]{1,42},\s+[A-Z.\-]|\d{1,3}\.\s+[A-Za-z0-9])"
)
_REF_FALLBACK_DOI_LINE = re.compile(r"^doi:\s*10\.\d", re.I)

def reference_strings_for_resolve_fallback(section_raw: str, *, max_strings: int = 80) -> list[str]:
    if not (section_raw or "").strip():
        return []
    text = soft_unwrap_reference_section_newlines(section_raw)
    lines = [ln.strip() for ln in text.split("\n") if (ln or "").strip()]
    out: list[str] = []
    buf = ""
    for ln in lines:
        if re.match(r"^(figure|fig\.|table|tab\.|appendix|section)\b", ln, re.I):
            if buf:
                s = re.sub(r"\s+", " ", buf.strip())
                if len(s) >= 28:
                    out.append(normalize_saved_reference_entry(s)[:520])
                buf = ""
            continue
        starts = bool(_REF_FALLBACK_ENTRY_HEAD.match(ln) or _REF_FALLBACK_DOI_LINE.match(ln))
        if starts and buf:
            s = re.sub(r"\s+", " ", buf.strip())
            if len(s) >= 28:
                out.append(normalize_saved_reference_entry(s)[:520])
                if len(out) >= max_strings:
                    break
            buf = ln
        elif starts and not buf:
            buf = ln
        else:
            buf = (buf + " " + ln).strip() if buf else ln
    if buf and len(out) < max_strings:
        s = re.sub(r"\s+", " ", buf.strip())
        if len(s) >= 28:
            out.append(normalize_saved_reference_entry(s)[:520])
    return out[:max_strings]

def _ensure_cache_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_pdf_excerpt_cache (
          paper_id INTEGER PRIMARY KEY,
          pdf_abspath TEXT,
          pdf_mtime INTEGER,
          pdf_size INTEGER,
          excerpt TEXT,
          updated_at INTEGER
        )
        """
    )

    cur.execute("PRAGMA table_info(paper_pdf_excerpt_cache)")
    cols = [r[1] for r in cur.fetchall()]
    if "hit_count" not in cols:
        cur.execute("ALTER TABLE paper_pdf_excerpt_cache ADD COLUMN hit_count INTEGER DEFAULT 0")
    if "miss_count" not in cols:
        cur.execute("ALTER TABLE paper_pdf_excerpt_cache ADD COLUMN miss_count INTEGER DEFAULT 0")
    if "last_hit_at" not in cols:
        cur.execute("ALTER TABLE paper_pdf_excerpt_cache ADD COLUMN last_hit_at INTEGER")
    if "last_miss_at" not in cols:
        cur.execute("ALTER TABLE paper_pdf_excerpt_cache ADD COLUMN last_miss_at INTEGER")
    conn.commit()

def _pdf_stat(abspath: str) -> tuple[int, int | None]:
    try:
        st = os.stat(abspath)
        return int(st.st_mtime), int(st.st_size)
    except Exception:
        return None

def _cache_get(db_path: str, paper_id: int, pdf_abspath: str, max_age_days: int = 30) -> str | None:
    if not db_path or not pdf_abspath:
        return None
    st = _pdf_stat(pdf_abspath)
    if not st:
        return None
    mtime, size = st
    now = int(time.time())
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        _ensure_cache_table(conn)
        cur.execute(
            "SELECT pdf_mtime,pdf_size,excerpt,updated_at FROM paper_pdf_excerpt_cache WHERE paper_id=?",
            (int(paper_id),),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT OR IGNORE INTO paper_pdf_excerpt_cache(paper_id,pdf_abspath,pdf_mtime,pdf_size,excerpt,updated_at,miss_count,last_miss_at) VALUES(?,?,?,?,?,?,?,?)",
                (int(paper_id), pdf_abspath, mtime, size, "", 0, 1, now),
            )
            conn.commit()
            return None
        ok = int(row[0] or 0) == mtime and int(row[1] or 0) == size
        ex = (row[2] or "").strip()
        updated_at = int(row[3] or 0)
        expired = bool(updated_at and max_age_days > 0 and (now - updated_at) > max_age_days * 86400)
        if ok and ex and (not expired):
            cur.execute(
                "UPDATE paper_pdf_excerpt_cache SET hit_count=hit_count+1,last_hit_at=? WHERE paper_id=?",
                (now, int(paper_id)),
            )
            conn.commit()
            return ex

        cur.execute(
            "UPDATE paper_pdf_excerpt_cache SET miss_count=miss_count+1,last_miss_at=? WHERE paper_id=?",
            (now, int(paper_id)),
        )
        conn.commit()
        return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

def _cache_set(db_path: str, paper_id: int, pdf_abspath: str, excerpt: str) -> None:
    if not db_path or not pdf_abspath:
        return
    st = _pdf_stat(pdf_abspath)
    if not st:
        return
    mtime, size = st
    now = int(time.time())
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        _ensure_cache_table(conn)
        cur.execute(
            """
            INSERT INTO paper_pdf_excerpt_cache(paper_id,pdf_abspath,pdf_mtime,pdf_size,excerpt,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(paper_id) DO UPDATE SET
              pdf_abspath=excluded.pdf_abspath,
              pdf_mtime=excluded.pdf_mtime,
              pdf_size=excluded.pdf_size,
              excerpt=excluded.excerpt,
              updated_at=excluded.updated_at
            """,
            (int(paper_id), pdf_abspath, mtime, size, excerpt or "", now),
        )
        conn.commit()
    except Exception:
        return
    finally:
        if conn:
            conn.close()

def extract_pdf_text_full_cached(db_path: str, paper_id: int, abspath: str | None, ) -> tuple[str, bool]:
    if not abspath or not os.path.isfile(abspath):
        return "", False
    ex = _cache_get(db_path, int(paper_id), abspath, max_age_days=45)
    if ex is not None:
        return ex, True
    return "", False

def _cache_delete(db_path: str, paper_id: int) -> None:
    if not db_path:
        return
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM paper_pdf_excerpt_cache WHERE paper_id=?", (int(paper_id),))
        conn.commit()
        conn.close()
    except Exception:
        pass

def compute_and_cache_excerpt(db_path: str, paper_id: int, pdf_abspath: str) -> None:
    ex = extract_pdf_text_full(pdf_abspath)
    if ex.strip():
        _cache_set(db_path, int(paper_id), pdf_abspath, ex)
    else:

        _cache_delete(db_path, int(paper_id))

def _ensure_reader_pdf_available(db: Any, paper: Any) -> str | None:
    """阅读页兜底：库内无 PDF 但有 arXiv/pdf_url 时，现取现存一份供上下文解析。"""
    pid = getattr(paper, "id", None)
    if pid is None:
        return None
    try:
        existing = db.get_library_pdf_abspath(int(pid))
        if existing:
            return existing
    except Exception:
        return None

    if not any((getattr(paper, "arxiv_id", None), getattr(paper, "pdf_url", None), getattr(paper, "source_url", None))):
        return None

    try:
        from ...core.paper_paths import LIBRARY_PDF_ROOT_DIR, library_pdf_relative_path
        from ...core.pdf_download import download_paper_pdf_to_path, resolve_paper_pdf_url
        from ...settings import get_settings

        relpath = library_pdf_relative_path(getattr(paper, "category", None), int(pid), getattr(paper, "title", None))
        data_root = os.path.dirname(os.path.abspath(getattr(db, "db_path", "")))
        dest = os.path.join(data_root, relpath)
        os.makedirs(os.path.join(data_root, LIBRARY_PDF_ROOT_DIR), exist_ok=True)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        mail = (getattr(get_settings(), "ncbi_email", "") or "").strip()
        if os.path.isfile(dest) and os.path.getsize(dest) >= 256:
            db.set_local_pdf_path(int(pid), relpath)
            return dest
        if resolve_paper_pdf_url(paper, email=mail) and download_paper_pdf_to_path(paper, dest, email=mail):
            db.set_local_pdf_path(int(pid), relpath)
            return dest
    except Exception:
        return None
    return None

def build_reader_snap(paper: Any, *, pdf_text_for_references: str = "") -> dict[str, Any]:
    refs_raw = getattr(paper, "references", None) or []
    refs: list[str] = []
    for r in refs_raw[:220]:
        s = normalize_saved_reference_entry(str(r))
        if len(s) >= 6:
            refs.append(s)
    refs_source = "db"
    references_section_raw = ""
    if not refs and (pdf_text_for_references or "").strip():
        references_section_raw = extract_references_section_raw_from_pdf_text(pdf_text_for_references)
        refs_source = "pdf_section" if references_section_raw else "none"
    elif not refs:
        refs_source = "none"
    pid = getattr(paper, "id", None)
    out: dict[str, Any] = {
        "paper_id": int(pid) if pid is not None and int(pid) > 0 else None,
        "title": (getattr(paper, "title", None) or "").strip(),
        "doi": (getattr(paper, "doi", None) or "").strip(),
        "arxiv_id": (getattr(paper, "arxiv_id", None) or "").strip(),
        "abstract": (getattr(paper, "abstract", None) or "").strip(),
        "keywords": [str(x) for x in (getattr(paper, "keywords", None) or [])[:32] if str(x).strip()],
        "references": refs,
        "references_source": refs_source,
        "references_section_raw": references_section_raw,
    }
    ptf = (pdf_text_for_references or "").strip()
    if len(ptf) >= 200:
        out["_pdf_merged_for_structure"] = ptf
    return out

def format_paper_reader_block(
    paper: Any,
    pdf_excerpt: str,
    *,
    references_section_raw: str = "",
    reader_artifact_block: str = "",
) -> str:
    authors = ", ".join((a.name or "").strip() for a in (paper.authors or []) if (a.name or "").strip())
    lines = [
        f"标题：{paper.title}",
        f"作者：{authors or '—'}",
        f"年份：{paper.year if paper.year is not None else '—'}",
        f"来源/期刊：{(paper.journal or '').strip() or '—'}",
        f"DOI：{(paper.doi or '').strip() or '—'}",
        f"领域分类：{getattr(paper, 'category', None) or '—'}",
        f"摘要：\n{(paper.abstract or '').strip() or '（无摘要）'}",
    ]
    kw = getattr(paper, "keywords", None) or []
    if kw:
        lines.append(f"关键词：{', '.join(str(x) for x in kw[:32])}")
    refs = getattr(paper, "references", None) or []
    if refs:
        lines.append("【参考文献条目（库内保存的 references 列表；阅读助手仅从下列字符串解析并检索，不自由主题泛搜）】")
        for i, r in enumerate(refs[:120], start=1):
            s = normalize_saved_reference_entry(str(r))
            if not s:
                continue
            lines.append(f"  [{i}] {s[:420]}")
    elif (references_section_raw or "").strip():
        raw = (references_section_raw or "").strip()
        lines.append(
            "【参考文献区 PDF 原文摘录（未程序切条；可先调 reader_pdf_structure 得 JSON 与 entries，"
            "再对用户相关请求用 reader_paper_lookup 且 from_pdf_references_section=true）】"
        )
        lines.append(raw)
    else:
        lines.append(
            "【参考文献】库表未保存结构化 references，且当前未能从 PDF 摘录中定位到参考文献标题后的文本。"
            "可换带参考文献的数据源重新保存，或由用户粘贴英文题名 / DOI。"
        )
    if (reader_artifact_block or "").strip():
        lines.append((reader_artifact_block or "").strip())
    ex = (pdf_excerpt or "").strip()
    if ex:
        lines.append(
            "【PDF 正文（结构化 Markdown；## 标记为自动识别的章节标题；精确内容以 PDF 视图为准）】\n"
            + ex
        )
    return "\n".join(lines)

def build_reader_context_for_paper(db: Any, paper_id: int) -> tuple[Any | None, str, str]:
    p = db.get_paper_by_id(int(paper_id))
    if not p:
        return None, "", ""
    pdf_path = _ensure_reader_pdf_available(db, p)
    excerpt, is_cached = extract_pdf_text_full_cached(getattr(db, "db_path", ""), int(paper_id), pdf_path)
    if pdf_path and not excerpt:
        excerpt = extract_pdf_text_full(pdf_path)
        if excerpt.strip():
            _cache_set(getattr(db, "db_path", ""), int(paper_id), pdf_path, excerpt)
    merged_for_refs = excerpt.strip()
    refs_raw = ""
    if not (getattr(p, "references", None) or []):
        refs_raw = extract_references_section_raw_from_pdf_text(merged_for_refs) if merged_for_refs else ""
    # DBLP 论文无摘要→Tavily 搜摘要+正文摘录（作为 PDF 替代）
    if not (p.abstract or "").strip() and not excerpt.strip() and p.title:
        try:
            from ...settings import get_settings as _gs
            _ak = getattr(_gs(), "tavily_api_key", "").strip()
            if _ak:
                import httpx
                _resp = httpx.post("https://api.tavily.com/search", json={
                    "api_key": _ak, "query": f"{p.title} paper",
                    "max_results": 5, "include_answer": True, "search_depth": "advanced"}, timeout=20.0)
                _resp.raise_for_status()
                _parts = []
                for _it in (_resp.json().get("results") or []):
                    _c = _it.get("content", "")
                    if _c and len(_c) > 80: _parts.append(_c)
                _full = "\n\n".join(_parts)[:4000]
                if _full:
                    p.abstract = _full[:2000]
                    excerpt = _full  # 替代 PDF 正文
                    db.update_paper(p.id, abstract=p.abstract)
        except Exception: pass
    reader_artifact_block = ""
    if merged_for_refs:
        try:
            from .paper_reader_artifact import ensure_reader_artifact, format_reader_artifact_block

            artifact = ensure_reader_artifact(
                getattr(db, "db_path", ""),
                int(paper_id),
                p,
                merged_for_refs,
                pdf_path,
            )
            reader_artifact_block = format_reader_artifact_block(artifact)
        except Exception:
            reader_artifact_block = ""
    block = format_paper_reader_block(
        p,
        excerpt,
        references_section_raw=refs_raw,
        reader_artifact_block=reader_artifact_block,
    )
    pdf_parsing = False  # 后台异步解析，不阻塞用户
    return p, block, merged_for_refs, pdf_parsing
