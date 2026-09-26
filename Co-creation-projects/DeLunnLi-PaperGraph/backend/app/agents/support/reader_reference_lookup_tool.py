"""参考文献工具 —— 解析论文引用列表并尝试在本库/外部检索被引文献."""

from __future__ import annotations

import logging
import re
from typing import Any
from collections.abc import Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from ...services.llm.context_budget import clip_utf8, TOOL_ITEM_BYTES

logger = logging.getLogger(__name__)

READER_RECOMMEND_MAX_RESULTS = 80
READER_RELATED_FROM_BIBLIOGRAPHY = "bibliography"
READER_RELATED_FROM_EXTERNAL_QUERY = "external_query"
READER_RELATED_FROM_REF_BLOCK = "ref_block"
READER_RELATED_FROM_PRE_SEARCH = "pre_search"

def _norm_doi(d: str | None) -> str:
    if not d:
        return ""
    s = str(d).strip().lower()
    if "doi.org/" in s:
        s = s.split("doi.org/", 1)[-1]
    s = s.replace("https://", "").replace("http://", "")
    s = re.sub(r"^doi:\s*", "", s)
    return s.strip().rstrip(".,;)")

def _norm_arxiv(a: str | None) -> str:
    if not a:
        return ""
    s = str(a).strip().lower()
    s = re.sub(r"^arxiv:\s*", "", s)
    m = re.search(r"(?:arxiv\.org/(?:abs|pdf)/)([\w.]+)", s)
    if m:
        s = m.group(1)
    s = s.replace(".pdf", "")
    if re.match(r"^\d{4}\.\d{4,5}", s):
        vi = s.rfind("v")
        if vi > 8 and vi < len(s) - 1 and s[vi + 1 :].isdigit():
            s = s[:vi]
    return s.strip()

def strip_reader_reco_boilerplate(um: str) -> str:
    import re as _re
    s = (um or "").strip()
    for pat in (r"推荐.*?论文", r"找.*?(相关|类似|参考)", r"search.*?(related|similar)", r"find.*?papers"):
        s = _re.sub(pat, "", s, flags=_re.IGNORECASE).strip()
    return s

def parse_reader_recommendation_intent(um: str) -> tuple[bool, int]:
    s = (um or "").strip().lower()
    want = any(k in s for k in ("推荐", "相关论文", "类似", "related", "similar", "recommend", "找.*论文"))

    import re as _re
    m = _re.search(r"(\d+)\s*[篇个本]", s)
    n = int(m.group(1)) if m else (5 if want else 0)
    return want, max(1, min(n, 20))

def user_message_may_need_reference_lookup(um: str) -> bool:
    s = (um or "").strip().lower()
    return any(k in s for k in ("参考", "引用", "reference", "bibliography", "related", "相关", "类似"))

def reader_user_allows_external_paper_lookup(um: str) -> bool:
    s = (um or "").strip().lower()
    if any(k in s for k in ("仅参考文献", "仅限参考文献", "只要参考文献", "只推荐参考文献", "只从参考文献", "只要引用", "不要库外", "不需要外部", "only reference", "just bibliography")):
        return False
    return True

def rerank_reader_pairs_by_anchor_refs_first(snap: dict, pairs: list, k: int = 5) -> list:
    title = str(snap.get("title") or "").strip().lower()
    if not title or not pairs:
        return pairs[:k]
    title_tokens = set(re.split(r"\W+", title)) - {""}
    if not title_tokens:
        return pairs[:k]
    def _score(pair):
        p, src = pair
        pt = str(getattr(p, "title", "") or "").strip().lower()
        pt_tokens = set(re.split(r"\W+", pt)) - {""}
        overlap = len(title_tokens & pt_tokens)
        bib_bonus = 2 if src in ("bibliography", "ref_block") else 0
        return (bib_bonus, overlap)
    return sorted(pairs, key=_score, reverse=True)[:k]

def prioritize_reader_related_pairs_refs_first(pairs: list) -> list:
    def _priority(pair):
        _, src = pair
        if src in ("bibliography", "ref_block", "pre_search"):
            return 0
        return 1
    return sorted(pairs, key=_priority)

def paper_matches_reader_snap(snap: dict[str, Any], p: Any) -> bool:
    if not snap:
        return False
    pid = snap.get("paper_id")
    if pid and getattr(p, "id", None) is not None:
        try:
            if int(getattr(p, "id", 0) or 0) == int(pid):
                return True
        except (TypeError, ValueError):
            pass
    st_doi = _norm_doi(str(snap.get("doi") or ""))
    pt_doi = _norm_doi(str(getattr(p, "doi", None) or ""))
    if st_doi and pt_doi and st_doi == pt_doi:
        return True
    sa = _norm_arxiv(str(snap.get("arxiv_id") or ""))
    pa = _norm_arxiv(str(getattr(p, "arxiv_id", None) or ""))
    if sa and pa and sa == pa:
        return True
    st = str(snap.get("title") or "").strip().lower()
    pt = str(getattr(p, "title", "") or "").strip().lower()
    _noise = re.compile(r"[\s\-_:,\.\(\)\[\]]+")
    stn = _noise.sub(" ", st).strip()
    ptn = _noise.sub(" ", pt).strip()
    if len(stn) >= 14 and len(ptn) >= 14:
        if stn == ptn or (stn in ptn or ptn in stn):
            return True
        from difflib import SequenceMatcher

        if SequenceMatcher(None, stn, ptn).ratio() >= 0.75:
            return True
    return False

class ReaderReferenceLookupTool(Tool):

    def __init__(
        self,
        get_snap: Callable[[], dict[str, Any]],
        on_papers_found: Callable[[list[Any], str], None],
        get_user_message: Callable[[], str],
    ) -> None:
        super().__init__(
            name="reader_reference_lookup",
            description=(
                "从当前文献的参考文献中提取搜索查询，检索相关论文。"
                "用户提示仅用于选择已有引用；结果须与引用的题名、DOI 或 arXiv 标识一致。"
            ),
        )
        self._get_snap = get_snap
        self._on_papers_found = on_papers_found
        self._get_user_message = get_user_message

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="max_results",
                type="integer",
                description="最多返回几条（1～80，默认 5）",
                required=False,
                default=5,
            ),
            ToolParameter(
                name="reference_focus",
                type="string",
                description=(
                    "可选。用于对当前参考文献排序的引用方向或文本片段。"
                ),
                required=False,
                default="",
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        try:
            snap = self._get_snap() or {}
            hint = clip_utf8(parameters.get("reference_focus") or self._get_user_message(), 600)
            try:
                mr = max(1, min(READER_RECOMMEND_MAX_RESULTS, int(parameters.get("max_results") or 5)))
            except (TypeError, ValueError):
                mr = 5
            collected = resolve_references_via_openalex(snap, max_results=mr, user_hint=hint)
        except Exception:
            logger.debug("reader_reference_lookup_failed", exc_info=True)
            return ToolResponse.error("SEARCH_FAILED", "参考文献检索暂不可用，请稍后重试。")
        if not collected:
            return ToolResponse.success(text="未找到与当前参考文献的题名、DOI 或 arXiv 标识一致的结果。可指定一条完整引用后重试。")
        self._on_papers_found(collected, READER_RELATED_FROM_BIBLIOGRAPHY)
        lines = [f"已核对 {len(collected)} 条参考文献；下方卡片可查看完整条目："]
        for i, paper in enumerate(collected, 1):
            lines.append(f"{i}. {clip_utf8(getattr(paper, 'title', ''), 240)} | year={getattr(paper, 'year', None) or '-'}")
        return ToolResponse.success(text=clip_utf8("\n".join(lines), TOOL_ITEM_BYTES))

def score_reference_line_against_hint(ln: str, hint: str) -> float:
    import re as _re
    h = (hint or "").lower()
    l = (ln or "").lower()
    if not h or not l:
        return 0.0
    h_tokens = set(_re.split(r"\W+", h)) - {""}
    l_tokens = set(_re.split(r"\W+", l)) - {""}
    if not h_tokens or not l_tokens:
        return 0.0
    return len(h_tokens & l_tokens) / max(len(h_tokens), len(l_tokens))

def reader_reference_lines(snap: dict[str, Any]) -> list[str]:
    refs = snap.get("references") or snap.get("references_from_structure") or []
    if not refs:
        from ...services.reader.paper_reader_context import reference_strings_for_resolve_fallback
        refs = reference_strings_for_resolve_fallback(str(snap.get("references_section_raw") or ""))
    return [str(ref).strip()[:4000] for ref in refs[:220] if str(ref).strip()]


def paper_matches_reference(paper: Any, reference: str) -> bool:
    """Bibliography provenance requires an identifier or complete title anchor.

    Topic overlap and search-engine ranking are not evidence of citation. In
    particular, a conflicting identifier defeats an otherwise similar title.
    """
    doi_refs = {_norm_doi(x) for x in re.findall(r"10\.\d{4,9}/[^\s<>\"|]+", reference, re.I)}
    doi = _norm_doi(getattr(paper, "doi", None))
    if doi and doi_refs:
        return doi in doi_refs
    ax_refs = {_norm_arxiv(x) for x in re.findall(r"(?<!\d)\d{4}\.\d{4,5}(?:v\d+)?", reference, re.I)}
    ax = _norm_arxiv(getattr(paper, "arxiv_id", None))
    if ax and ax_refs:
        return ax in ax_refs
    # Remove punctuation/line wraps, preserving whole-word order. Do not accept
    # a subset of generic words, or a search hit merely matching the topic.
    normalize = lambda value: " ".join(re.findall(r"[^\W_]+", str(value or "").casefold()))
    title = normalize(getattr(paper, "title", None))
    ref = normalize(reference)
    substantial = len(title) >= 16 and (len(title.split()) >= 3 or len(re.findall(r"[\u4e00-\u9fff]", title)) >= 8)
    return bool(substantial and f" {title} " in f" {ref} ")


def resolve_references_via_openalex(
    snap: dict[str, Any], *, max_results: int = 5, user_hint: str = ""
) -> list[Any]:
    refs = reader_reference_lines(snap)
    if not refs:
        return []
    max_results = max(1, min(READER_RECOMMEND_MAX_RESULTS, int(max_results)))
    if user_hint:
        refs.sort(key=lambda ref: score_reference_line_against_hint(ref, user_hint[:900]), reverse=True)
    from app.api.dependencies import get_searcher
    from app.services.papers.papers_converters import litpaper_to_api_paper
    from app.utils.async_sync import run_coroutine_sync
    searcher = get_searcher()
    results: list[Any] = []
    queries: set[str] = set()
    seen: set[str] = set()
    for ref in refs[:min(max_results * 3, 24)]:
        q = ref[:520]
        if not q or q.casefold() in queries:
            continue
        queries.add(q.casefold())
        try:
            papers = run_coroutine_sync(
                searcher.search_async(q, sources=["openalex", "arxiv"], max_results=2, http_timeout_sec=5),
                op_name="resolve_refs",
            )
            for paper in papers or []:
                candidate = litpaper_to_api_paper(paper)
                title = str(getattr(candidate, "title", "") or "").strip().casefold()
                if title and title not in seen and paper_matches_reference(candidate, ref):
                    seen.add(title)
                    results.append(candidate)
        except Exception:
            logger.debug("reader_reference_resolve_failed", exc_info=True)
        if len(results) >= max_results:
            break
    return results[:max_results]
