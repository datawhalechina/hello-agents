
from __future__ import annotations

import re
from typing import Any

from .paper_reader_context import (
    extract_references_section_raw_from_pdf_text,
    reference_strings_for_resolve_fallback,
)

_REF_HEADER = re.compile(
    r"(?is)(?:^|\n)[\s#]*(?:references|reference\s+list|bibliography|cited\s+references|引用文献|参考文献)\s*[:：]?\s*(?:\n+|$)",
)

_CHAPTER_LINE = re.compile(
    r"(?m)^(?:\s|#)*(?:(?P<num>\d+(?:\.\d+){0,2})\.?\s+)?(?P<h>"
    r"Abstract|ABSTRACT|Introduction|INTRODUCTION|Related\s+Work|RELATED\s+WORK|"
    r"Background|BACKGROUND|Preliminar(?:y|ies)|Problem\s+Formulation|"
    r"Methodology|Method|Methods|Model|Models|Approach|Architecture|Framework|"
    r"Experiment(?:s)?|EXPERIMENTS|Implementation|Evaluation|Results?|RESULTS|Analysis|ANALYSIS|"
    r"Discussion|DISCUSSION|Ablation|Ablations|Comparison|Comparisons|"
    r"Conclusion|CONCLUSIONS?|Limitations?|LIMITATIONS|Future\s+Work|Broader\s+Impact|"
    r"Appendix|APPENDIX|Supplementary|Acknowledg(?:e)?ments?|ACKNOWLEDG|"
    r"摘要|引言|简介|预备|问题表述|相关工作|背景|方法|模型|架构|框架|"
    r"实验|实现|评估|结果|分析|讨论|消融|对比|结论|局限|未来工作|附录|补充|致谢"
    r")(?:\s*[.:：#])?\s*$",
    re.I,
)

def _slug_heading(h: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", (h or "").strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:48] or "sec")

def _split_chapters(
    text: str,
    *,
    max_chapter_chars: int,
    max_chapters: int,
) -> list[dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    matches = list(_CHAPTER_LINE.finditer(t))
    if not matches:
        return [
            {
                "id": "document",
                "heading": "(未识别到标准章节标题)",
                "text": t[:max_chapter_chars],
                "truncated": len(t) > max_chapter_chars,
            }
        ]

    out: list[dict[str, Any]] = []
    p0 = matches[0].start()
    if p0 > 40:
        pre = t[:p0].strip()
        if len(pre) >= 24:
            out.append(
                {
                    "id": "preamble",
                    "heading": "(文首)",
                    "text": pre[:max_chapter_chars],
                    "truncated": len(pre) > max_chapter_chars,
                }
            )

    for i, m in enumerate(matches):
        if len(out) >= max_chapters:
            break
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
        heading = (m.group("h") or "section").strip()
        body = t[start:end].strip()
        if not body:
            continue
        slug = _slug_heading(heading)
        out.append(
            {
                "id": f"{slug}_{i}",
                "heading": heading,
                "text": body[:max_chapter_chars],
                "truncated": len(body) > max_chapter_chars,
            }
        )
    return out

def parse_pdf_merged_text_to_json(
    merged_text: str,
    *,
    max_chapter_chars: int = 12000,
    max_chapters: int = 24,
    max_ref_entries: int = 80,
) -> dict[str, Any]:
    t = (merged_text or "").strip()
    if not t:
        return {
            "version": 1,
            "chapters": [],
            "references": {"raw": "", "entries": [], "entry_count": 0},
        }

    m = _REF_HEADER.search(t)
    head_for_chapters = t[: m.start()].strip() if m else t

    ref_raw = extract_references_section_raw_from_pdf_text(t)
    entries = reference_strings_for_resolve_fallback(ref_raw, max_strings=max_ref_entries) if ref_raw else []

    chapters = _split_chapters(
        head_for_chapters,
        max_chapter_chars=max_chapter_chars,
        max_chapters=max_chapters,
    )

    return {
        "version": 1,
        "chapters": chapters,
        "references": {
            "raw": (ref_raw or "")[:28000],
            "raw_truncated": len(ref_raw or "") > 28000,
            "entry_count": len(entries),
            "entries": entries,
        },
    }
