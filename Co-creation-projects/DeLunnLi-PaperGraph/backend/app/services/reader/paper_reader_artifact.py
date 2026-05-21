from __future__ import annotations

import json
import os
import time
from typing import Any

from .paper_reader_structure import parse_pdf_merged_text_to_json

ARTIFACT_VERSION = 1
ARTIFACT_DIR = "reader_artifacts"


def reader_artifact_path(db_path: str, paper_id: int) -> str:
    data_root = os.path.dirname(os.path.abspath(db_path or "."))
    return os.path.join(data_root, ARTIFACT_DIR, f"paper_{int(paper_id)}.json")


def _pdf_stat(pdf_abspath: str | None) -> dict[str, int]:
    if not pdf_abspath or not os.path.isfile(pdf_abspath):
        return {}
    try:
        st = os.stat(pdf_abspath)
        return {"mtime": int(st.st_mtime), "size": int(st.st_size)}
    except Exception:
        return {}


def _paper_meta(paper: Any) -> dict[str, Any]:
    authors = [
        (getattr(a, "name", None) or "").strip()
        for a in (getattr(paper, "authors", None) or [])
        if (getattr(a, "name", None) or "").strip()
    ]
    return {
        "id": getattr(paper, "id", None),
        "title": (getattr(paper, "title", None) or "").strip(),
        "authors": authors,
        "year": getattr(paper, "year", None),
        "venue": (getattr(paper, "journal", None) or "").strip(),
        "doi": (getattr(paper, "doi", None) or "").strip(),
        "arxiv_id": (getattr(paper, "arxiv_id", None) or "").strip(),
        "abstract": (getattr(paper, "abstract", None) or "").strip(),
        "keywords": [str(x) for x in (getattr(paper, "keywords", None) or [])[:32] if str(x).strip()],
    }


def load_reader_artifact(db_path: str, paper_id: int, pdf_abspath: str | None = None) -> dict[str, Any] | None:
    path = reader_artifact_path(db_path, paper_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return None
    if int(obj.get("version") or 0) != ARTIFACT_VERSION:
        return None
    current = _pdf_stat(pdf_abspath)
    saved = obj.get("pdf") or {}
    if current and (int(saved.get("mtime") or 0) != current["mtime"] or int(saved.get("size") or 0) != current["size"]):
        return None
    return obj


def build_reader_artifact(
    db_path: str,
    paper_id: int,
    paper: Any,
    pdf_text: str,
    pdf_abspath: str | None = None,
) -> dict[str, Any] | None:
    text = (pdf_text or "").strip()
    if len(text) < 200:
        return None

    parsed = parse_pdf_merged_text_to_json(text, max_chapter_chars=9000, max_chapters=40, max_ref_entries=100)
    artifact = {
        "version": ARTIFACT_VERSION,
        "generated_at": int(time.time()),
        "paper": _paper_meta(paper),
        "pdf": _pdf_stat(pdf_abspath),
        "structure": parsed,
    }
    path = reader_artifact_path(db_path, paper_id)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        return None
    return artifact


def ensure_reader_artifact(
    db_path: str,
    paper_id: int,
    paper: Any,
    pdf_text: str,
    pdf_abspath: str | None = None,
) -> dict[str, Any] | None:
    cached = load_reader_artifact(db_path, paper_id, pdf_abspath)
    if cached:
        return cached
    return build_reader_artifact(db_path, paper_id, paper, pdf_text, pdf_abspath)


def format_reader_artifact_block(artifact: dict[str, Any] | None, *, max_chars: int = 9000) -> str:
    if not artifact:
        return ""
    paper = artifact.get("paper") or {}
    structure = artifact.get("structure") or {}
    chapters = structure.get("chapters") or []
    refs = (structure.get("references") or {}).get("entries") or []
    lines = [
        "【结构化阅读档案（由 PDF 自动解析生成；阅读助手优先依据此档案回答）】",
        f"标题：{paper.get('title') or '—'}",
        f"摘要：{paper.get('abstract') or '（无摘要）'}",
        "章节：",
    ]
    for i, ch in enumerate(chapters[:14], start=1):
        heading = (ch.get("heading") or f"Section {i}").strip()
        text = " ".join(str(ch.get("text") or "").split())
        snippet = text[:900]
        tail = "..." if len(text) > 900 else ""
        lines.append(f"{i}. {heading}\n{snippet}{tail}")
    if refs:
        lines.append("参考文献条目：")
        for i, ref in enumerate(refs[:30], start=1):
            lines.append(f"[{i}] {str(ref)[:420]}")
    block = "\n".join(lines).strip()
    return block[:max_chars]
