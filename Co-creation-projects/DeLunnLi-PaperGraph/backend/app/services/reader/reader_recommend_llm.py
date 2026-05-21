
from __future__ import annotations

import logging
import re
from typing import Any

from ...agents.support.reader_reference_lookup_tool import (
    READER_RECOMMEND_MAX_RESULTS,
    prioritize_reader_related_pairs_refs_first,
)
from ...utils import parse_llm_json, truncate_text
from ..llm.llm_service import coerce_hello_agents_llm_output_to_str, get_llm, is_llm_configured
from .paper_reader_context import preprocess_pdf_text_for_reference_blob

logger = logging.getLogger(__name__)

READER_BIB_SOURCES = frozenset({"bibliography", "ref_block"})

def extract_title_queries_from_ref_blob_llm(
    section_raw: str,
    snap: dict[str, Any],
    *,
    max_queries: int = 12,
) -> list[str]:
    if not is_llm_configured() or not (section_raw or "").strip():
        return []
    blob = truncate_text((section_raw or "").strip(), 11000, suffix="...")
    title = str(snap.get("title") or "").strip()
    ab = truncate_text(str(snap.get("abstract") or "").strip(), 1200, suffix="...")
    kw = snap.get("keywords") or []
    kw_s = ", ".join(str(x) for x in kw[:20] if str(x).strip()) if isinstance(kw, (list, tuple)) else ""

    system = (
        "Extract English paper titles/phrases from the reference blob below for OpenAlex search. "
        "Output JSON: {\"queries\":[...]}, max "
        f"{max_queries} items, each 16-160 chars. "
        "Each must be a contiguous substring of the reference blob (join lines with spaces). "
        "Prefer long titles (>=22 chars); arXiv/DOI are OK as single items. "
        "Skip journal names, venue-only lines, vol/pages, generic topics."
    )
    user = (
        f"[Title] {title}\n[Abstract snippet] {ab}\n[Keywords] {kw_s}\n\n"
        f"[Reference blob]\n{blob}\n"
    )
    try:
        llm = get_llm()
        raw = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        text = coerce_hello_agents_llm_output_to_str(raw).strip()
    except Exception as exc:
        logger.debug("extract_title_queries_llm_invoke_failed", exc_info=exc)
        return []

    data = parse_llm_json(text)
    if not isinstance(data, dict):
        return []
    arr = data.get("queries") or data.get("title_queries") or []
    if not isinstance(arr, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for x in arr:
        q = re.sub(r"\s+", " ", str(x).strip())[:200]
        if len(q) < 16:
            continue

        _nq = re.sub(r"\s+", " ", preprocess_pdf_text_for_reference_blob(q or "").lower()).strip()
        _nr = re.sub(r"\s+", " ", preprocess_pdf_text_for_reference_blob(section_raw or "").lower()).strip()
        if len(_nq) < 12 or len(_nr) < 40:
            continue
        if not (_nq in _nr or (len(_nq[:48]) >= 14 and _nq[:48] in _nr)):
            _words = [w for w in re.findall(r"[a-z]{5,}", _nq) if len(w) >= 5][:8]
            if not _words or sum(1 for w in _words if w in _nr) < max(2, int(len(_words) * 0.5)):
                continue
        k = q.lower()[:240]
        if k in seen:
            continue
        seen.add(k)
        out.append(q[:520])
        if len(out) >= max_queries:
            break
    return out

def merge_ref_lines_with_llm_queries(
    section_raw: str,
    snap: dict[str, Any],
    base_lines: list[str],
    *,
    max_queries: int = 12,
) -> list[str]:
    llm_q = extract_title_queries_from_ref_blob_llm(section_raw, snap, max_queries=max_queries)
    merged: list[str] = []
    seen: set[str] = set()
    for src in (base_lines or []) + llm_q:
        t = re.sub(r"\s+", " ", str(src).strip())
        if len(t) < 22:
            continue
        k = t.lower()[:260]
        if k in seen:
            continue
        seen.add(k)
        merged.append(t[:520])
        if len(merged) >= 72:
            break
    return merged

def rerank_reader_recommend_pairs_by_llm(
    snap: dict[str, Any],
    pairs: list[tuple[Any, str]],
    *,
    user_message: str,
    history_lines: str = "",
    reco_max_hint: int = 2,
) -> list[tuple[Any, str]]:
    if not pairs:
        return pairs
    if not is_llm_configured():
        return prioritize_reader_related_pairs_refs_first(pairs)
    hint = max(1, min(int(reco_max_hint or 2), READER_RECOMMEND_MAX_RESULTS))

    head: list[tuple[Any, str]] = []
    bib: list[tuple[Any, str]] = []
    for p, s in pairs:
        if s in READER_BIB_SOURCES:
            bib.append((p, s))
        else:
            head.append((p, s))

    if len(bib) <= 1:
        return bib + head

    n = len(bib)
    title = str(snap.get("title") or "").strip()
    ab = truncate_text(str(snap.get("abstract") or "").strip(), 2000, suffix="...")
    kw = snap.get("keywords") or []
    kw_s = ", ".join(str(x) for x in kw[:24] if str(x).strip()) if isinstance(kw, (list, tuple)) else ""
    um = truncate_text((user_message or "").strip(), 600, suffix="...")
    hist = truncate_text((history_lines or "").strip(), 1400, suffix="...")

    lines: list[str] = []
    for i, (ap, _) in enumerate(bib):
        t = str(getattr(ap, "title", "") or "").strip() or "(no title)"
        y = getattr(ap, "year", None) or "-"
        j = str(getattr(ap, "journal", None) or getattr(ap, "venue", None) or "").strip() or "-"
        ax = str(getattr(ap, "arxiv_id", None) or "").strip() or "-"
        doi = str(getattr(ap, "doi", None) or "").strip() or "-"
        lines.append(f"{i}. {t} | year={y} | venue={j[:80]} | arxiv={ax} | doi={doi}")

    system = (
        "You are a relevance judge. Given the main paper, chat context, and user question, "
        "rank candidate papers (from its reference parsing) by relevance to the paper's method, task, data. "
        "Decide how many to keep (keep_n) -- don't pad to match the user's hint, "
        f"max = min(candidate_count, {READER_RECOMMEND_MAX_RESULTS}). "
        "Exclude unrelated domains, generic-topic surveys, shared buzzwords. "
        "Non-reference items are secondary. "
        "Output JSON:\n"
        "{\"keep_n\":int,\"order\":[int,...],"
        "\"items\":[{\"i\":0,\"score\":0.82,\"relation\":\"...\",\"why\":\"<=40 chars\"}]}\n"
        f"keep_n in 1..min(count,{READER_RECOMMEND_MAX_RESULTS}), matching conversation intent. "
        "order: full permutation of indices (0-based) by descending relevance, no dupes. "
        f"User hint (~{hint}) is non-binding -- explain in items[].why if different."
    )
    user = (
        f"[Title] {title}\n[Abstract] {ab}\n[Keywords] {kw_s}\n\n"
        f"[Chat context]\n{hist or '(none)'}\n\n"
        f"[User question] {um}\n\n"
        f"[Candidates] ({n} total)\n" + "\n".join(lines) + "\n"
    )
    order: list[int | None] = None
    keep_n: int | None = None
    try:
        llm = get_llm()
        raw = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        text = coerce_hello_agents_llm_output_to_str(raw).strip()
        data = parse_llm_json(text)
        if isinstance(data, dict):
            if isinstance(data.get("order"), list):
                parsed: list[int] = []
                for x in data["order"]:
                    try:
                        parsed.append(int(x))
                    except (TypeError, ValueError):
                        continue
                order = parsed
            for key in ("keep_n", "keep", "n_keep", "num_keep"):
                v = data.get(key)
                if v is None:
                    continue
                try:
                    keep_n = int(v)
                    break
                except (TypeError, ValueError):
                    continue
    except Exception as exc:
        logger.debug("rerank_reader_recommend_llm_invoke_failed", exc_info=exc)

    if not order or len(order) < max(2, (n + 1) // 2):
        try:
            from ...agents.support.reader_reference_lookup_tool import rerank_reader_pairs_by_anchor

            kn = max(1, min(hint, n, READER_RECOMMEND_MAX_RESULTS))
            return rerank_reader_pairs_by_anchor(snap, bib, k=kn) + head
        except Exception:
            return bib[: max(1, min(hint, n, READER_RECOMMEND_MAX_RESULTS))] + head

    seen_i: set[int] = set()
    reordered: list[tuple[Any, str]] = []
    for i in order:
        try:
            ii = int(i)
        except (TypeError, ValueError):
            continue
        if 0 <= ii < n and ii not in seen_i:
            reordered.append(bib[ii])
            seen_i.add(ii)
    for i in range(n):
        if i not in seen_i:
            reordered.append(bib[i])

    kn = hint
    if keep_n is not None:
        try:
            kn = int(keep_n)
        except (TypeError, ValueError):
            kn = hint
    kn = max(1, min(kn, n, READER_RECOMMEND_MAX_RESULTS))
    return reordered[:kn] + head
