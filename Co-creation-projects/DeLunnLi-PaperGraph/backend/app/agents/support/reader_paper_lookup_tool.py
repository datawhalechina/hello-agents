
from __future__ import annotations

import logging
import re
from typing import Any
from collections.abc import Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from .reader_reference_lookup_tool import (
    READER_RECOMMEND_MAX_RESULTS, READER_RELATED_FROM_EXTERNAL_QUERY, READER_RELATED_FROM_REF_BLOCK,
    _norm_doi, _norm_arxiv,
    resolve_references_via_openalex, score_reference_line_against_hint,
)

logger = logging.getLogger(__name__)

def _normalize_ref_blob_for_match(blob: str) -> str:
    u = (blob or "").lower()
    u = re.sub(r"\s+", " ", u)
    for _ in range(20):
        u2 = re.sub(r"([a-z])-\s*([a-z])", r"\1\2", u)
        if u2 == u:
            break
        u = u2
    return u

def ground_score_paper_vs_reference_blob(ap: Any, ref_blob: str) -> float:
    raw = _normalize_ref_blob_for_match(ref_blob)
    if len(raw) < 50:
        return 1.0

    doi = _norm_doi(str(getattr(ap, "doi", None) or ""))
    if doi and len(doi) > 6 and doi in raw.replace("https://doi.org/", "").replace("http://dx.doi.org/", ""):
        return 1.0

    ax = _norm_arxiv(str(getattr(ap, "arxiv_id", None) or ""))
    if ax and len(ax) >= 8:
        compact = re.sub(r"[^\d.]", "", raw)
        if ax in raw or ax in compact:
            return 1.0

    title = str(getattr(ap, "title", "") or "").strip()
    if len(title) < 8:
        return 0.2
    tn = _normalize_ref_blob_for_match(title)
    if len(tn) >= 10 and tn in raw:
        return 1.0
    if len(tn) >= 22:
        head = tn[: min(88, len(tn))]
        if len(head) >= 18 and head in raw:
            return 0.95

    toks = [w for w in re.findall(r"[a-z0-9]{4,}", tn) if len(w) >= 4]
    if not toks:
        return 0.22
    hits = sum(1 for w in toks if w in raw)
    ratio = hits / max(1, len(toks))
    return min(1.0, 0.28 + 0.72 * ratio)

class ReaderPaperLookupTool(Tool):

    def __init__(
        self,
        on_papers_found: Callable[[list[Any], str], None],
        *,
        get_snap: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            name="reader_paper_lookup",
            description=(
                "两类用法：(1) 用户粘贴的库外英文题名/DOI/arXiv：from_pdf_references_section=false，"
                "按 query 在 OpenAlex 快速检索（1～80 条）。"
                "(2) 仅有「参考文献区 PDF 原文摘录」、无库表列表时：from_pdf_references_section=true；"
                "优先使用本轮 ``reader_pdf_structure`` 写入的粗分 ``entries`` 选条；若未调用该工具则退回摘录内粗分。"
                "再按 query 与题录行匹配排序，对最相关若干条做多源解析。"
                "若已有库表 references 且用户要求按列表解析，优先 reader_reference_lookup。"
            ),
        )
        self._on_papers_found = on_papers_found
        self._get_snap = get_snap

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "from_pdf=false：OpenAlex 检索串（题名片段、作者+年、DOI/arXiv）。"
                    "from_pdf=true：与用户问题相关的**提示串**（摘录中的英文题名片段、DOI、arXiv、或作者姓+年份），"
                    "用于在粗分后的参考文献行里排序选条；勿只用两三个泛词。"
                ),
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="最多返回几条（1～80，默认 3）",
                required=False,
                default=3,
            ),
            ToolParameter(
                name="from_pdf_references_section",
                type="boolean",
                description=(
                    "true：当前依赖「参考文献区 PDF 原文摘录」；服务端粗分条后按 query 与题录行匹配，再逐条多源解析。"
                    "false：库外粘贴题名等，直接 OpenAlex。"
                ),
                required=False,
                default=False,
            ),
        ]

    def _run_from_pdf_ref_blob(self, q: str, mr: int) -> ToolResponse:
        if not callable(self._get_snap):
            return ToolResponse.error(
                "NO_SNAPSHOT",
                "reader_paper_lookup：from_pdf 模式需要阅读上下文快照，当前不可用。",
            )
        try:
            snap = dict(self._get_snap() or {})
        except Exception as exc:
            logger.debug("reader_paper_lookup_snap_failed", exc_info=exc)
            return ToolResponse.error("SNAP_FAILED", f"reader_paper_lookup：读取快照失败：{exc}")

        ref_blob = str(snap.get("references_section_raw") or "").strip()
        rs_pre = snap.get("references_from_structure")
        has_struct_entries = isinstance(rs_pre, list) and bool(rs_pre)
        if len(ref_blob) < 80 and not has_struct_entries:
            return ToolResponse.success(
                text=(
                    "reader_paper_lookup：当前无足够长的「参考文献区 PDF 摘录」，且本轮尚未通过 reader_pdf_structure 得到 entries。"
                    "请先调用 reader_pdf_structure，或确认已打开带 PDF 的文献；也可改用库外题名（from_pdf_references_section=false）。"
                ),
            )

        try:
            from ...services.reader.paper_reader_context import reference_strings_for_resolve_fallback
        except Exception as exc:
            logger.warning("reader_paper_lookup_ref_fallback_import_failed", exc_info=exc)
            return ToolResponse.error("IMPORT_FAILED", f"reader_paper_lookup：摘录分条模块不可用。{exc}")

        lines: list[str] = []
        rs = snap.get("references_from_structure")
        if isinstance(rs, list) and rs:
            lines = [str(x).strip() for x in rs if str(x).strip()]
        if not lines:
            lines = reference_strings_for_resolve_fallback(ref_blob)
        if not lines:
            return ToolResponse.success(
                text=(
                    "reader_paper_lookup：无法得到参考文献粗分条目（可先调 reader_pdf_structure，"
                    "或提示用户给出 DOI / 标准英文题名走库外检索）。"
                ),
            )

        ref_for_ground = ref_blob
        if len(ref_for_ground) < 80 and lines:
            ref_for_ground = "\n".join(lines[:80])

        hint = q.strip()
        ranked = sorted(lines, key=lambda ln: -score_reference_line_against_hint(ln, hint))
        pool_n = max(mr * 6, 24)
        snap["references"] = ranked[:pool_n]

        try:
            api_papers = list(
                resolve_references_via_openalex(snap, max_results=mr) or []
            )
        except Exception as exc:
            logger.debug("reader_paper_lookup_resolve_failed", exc_info=exc)
            return ToolResponse.error("RESOLVE_FAILED", f"reader_paper_lookup：按摘录解析失败：{exc}")

        if not api_papers:
            return ToolResponse.success(
                text=(
                    "reader_paper_lookup：按 PDF 摘录分条解析后无通过锚定校验的命中。"
                    "请把 query 换成摘录中与目标文献更贴近的英文题名片段、DOI 或 arXiv。"
                ),
            )

        try:
            self._on_papers_found(api_papers, READER_RELATED_FROM_REF_BLOCK)
        except Exception as exc:
            logger.debug("reader_paper_lookup_callback_failed", exc_info=exc)

        out_lines = [
            f"reader_paper_lookup：已按 PDF 参考文献摘录匹配并解析 {len(api_papers)} 条（阅读页卡片与参考文献推荐同列）："
        ]
        for i, ap in enumerate(api_papers, start=1):
            t = str(getattr(ap, "title", "") or "").strip() or "（无标题）"
            y = getattr(ap, "year", None) or "—"
            ax = getattr(ap, "arxiv_id", None) or "—"
            doi = getattr(ap, "doi", None) or "—"
            out_lines.append(f"{i}. {t} | year={y} | arxiv={ax} | doi={doi}")
        return ToolResponse.success(text="\n".join(out_lines))

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        q = str(parameters.get("query") or parameters.get("input") or "").strip()
        q = re.sub(r"\s+", " ", q)[:160]
        if len(q) < 4:
            return ToolResponse.error("INVALID_PARAM", "reader_paper_lookup：query 过短（至少 4 个字符）。")

        try:
            mr = int(parameters.get("max_results") or 3)
        except (TypeError, ValueError):
            mr = 3
        mr = max(1, min(READER_RECOMMEND_MAX_RESULTS, mr))

        from_ref = parameters.get("from_pdf_references_section")
        if isinstance(from_ref, str):
            from_ref = from_ref.strip().lower() in ("1", "true", "yes", "on")
        else:
            from_ref = bool(from_ref)

        if from_ref:
            return self._run_from_pdf_ref_blob(q, mr)

        fetch_n = max(mr * 2, 6)

        try:
            from ...api.dependencies import get_searcher
            from ...services.papers.papers_converters import litpaper_to_api_paper
        except Exception as exc:
            logger.warning("reader_paper_lookup_import_failed", exc_info=exc)
            return ToolResponse.error("IMPORT_FAILED", f"reader_paper_lookup：检索模块不可用。{exc}")

        _REF_ARXIV = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|\barXiv:\s*)([\w.]+)", re.I)
        _REF_ARXIV_ID_LOOSE = re.compile(r"(?:^|[^\w])arxiv\s*:?\s*(\d{4}\.\d{4,5}(?:v\d+)?)\b", re.I)
        ax_match = _REF_ARXIV.search(q) or _REF_ARXIV_ID_LOOSE.search(q)
        ax_id = ""
        if ax_match:
            g1 = ax_match.group(1) if ax_match.lastindex else ""
            ax_id = (g1 or "").strip().replace(".pdf", "")
            if ax_id and ax_id[-1].isalpha():
                vi = ax_id.rfind("v")
                if vi > 8 and vi < len(ax_id) - 1 and ax_id[vi + 1:].isdigit():
                    ax_id = ax_id[:vi]

        searcher = get_searcher()
        merged: list[Any] = []
        seen_titles: set[str] = set()

        def _merge(batch: Any) -> None:
            for p in batch or []:
                t = (getattr(p, "title", None) or "").strip().lower()
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    merged.append(p)

        if ax_id and re.match(r"^\d{4}\.\d{4,5}", ax_id):
            try:
                _merge(searcher.search_arxiv(
                    "", max_results=4, arxiv_id_list=ax_id,
                    http_timeout_sec=10, http_max_attempts=1,
                ))
            except Exception as exc:
                logger.debug("reader_paper_lookup_arxiv_id_failed", exc_info=exc)

        clean_q = re.sub(r"\b(?:arxiv\.org/(?:abs|pdf)/|arxiv\s*:?\s*)\d{4}\.\d{4,5}(?:v\d+)?\b\.?", " ", q, flags=re.I)
        clean_q = re.sub(r"\s+", " ", clean_q).strip()
        search_queries: list[str] = []
        if clean_q and len(clean_q) >= 6:
            search_queries.append(clean_q[:160])
        search_queries.append(q[:160])
        uniq_q = list(dict.fromkeys(search_queries))

        year_filter: int | None = None
        year_match = re.search(r"\b(19|20)(\d{2})\b", q)
        if year_match:
            y = int(year_match.group(0))
            if 1990 <= y <= 2030:
                year_filter = y

        author_hint: str | None = None
        author_match = re.search(r"\(?([A-Z][a-z]{1,20})\s+(?:et\s+al\.?|and)", q)
        if author_match:
            author_hint = author_match.group(1).lower()

        for sq in uniq_q[:2]:
            if len(merged) >= fetch_n:
                break
            try:
                _merge(searcher.search_openalex(
                    sq, max_results=max(fetch_n - len(merged), 5),
                    venue_proceedings_journal=False,
                    year_from=year_filter,
                    year_to=year_filter,
                ))
            except Exception as exc:
                logger.debug("reader_paper_lookup_openalex_failed", exc_info=exc)

        def _auth_score(p: Any) -> float:
            s = 0.0
            if author_hint:
                auth_names = [str(getattr(a, "name", "") or "").lower() for a in (getattr(p, "authors", None) or [])]
                if any(author_hint in an for an in auth_names):
                    s += 2.0
            if year_filter and getattr(p, "year", None) == year_filter:
                s += 1.0
            return s

        merged.sort(key=_auth_score, reverse=True)

        api_papers: list[Any] = []
        for p in merged:
            try:
                api_papers.append(litpaper_to_api_paper(p))
            except Exception:
                continue
        api_papers = api_papers[:mr]

        if not api_papers:
            return ToolResponse.success(
                text=(
                    f"reader_paper_lookup：未命中条目（query={q[:80]}）。"
                    "可换更标准的英文题名或作者+年份重试。"
                ),
            )

        try:
            self._on_papers_found(api_papers, READER_RELATED_FROM_EXTERNAL_QUERY)
        except Exception as exc:
            logger.debug("reader_paper_lookup_callback_failed", exc_info=exc)

        lines = [f"reader_paper_lookup：命中 {len(api_papers)} 条（可在最终回答中对应引用）："]
        for i, ap in enumerate(api_papers, start=1):
            t = str(getattr(ap, "title", "") or "").strip() or "（无标题）"
            y = getattr(ap, "year", None) or "—"
            ax = getattr(ap, "arxiv_id", None) or "—"
            doi = getattr(ap, "doi", None) or "—"
            lines.append(f"{i}. {t} | year={y} | arxiv={ax} | doi={doi}")
        lines.append("以上条目为库外检索结果；用户若只要参考文献区内的论文，应使用 from_pdf_references_section=true。")
        return ToolResponse.success(text="\n".join(lines))
