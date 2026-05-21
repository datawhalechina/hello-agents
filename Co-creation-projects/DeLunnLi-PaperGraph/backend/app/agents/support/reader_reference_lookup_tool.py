
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from collections.abc import Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from ...agents.search_agent import SearchIntent

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
    if any(k in s for k in ("仅参考文献", "只要引用", "only reference", "just bibliography")):
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
                "接受一条参考文献文本（或用户提示），调用 search_papers() 检索并返回可点击的论文结果。"
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
                    "可选。用户感兴趣的引用方向或文本片段，直接用作文本检索查询。"
                ),
                required=False,
                default="",
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        snap = {}
        try:
            snap = self._get_snap() or {}
        except Exception as exc:
            logger.debug("reader_reference_lookup_get_snap_failed", exc_info=exc)
            return ToolResponse.error("SNAP_FAILED", f"reader_reference_lookup: cannot read snap. {exc}")

        refs = [str(x).strip() for x in (snap.get("references") or []) if str(x).strip()]
        raw = (snap.get("references_section_raw") or "").strip()
        if not refs:
            if raw:
                return ToolResponse.success(
                    text=(
                        "reader_reference_lookup: current paper has no parsed references list; "
                        "the PDF references section text is available. "
                        "Extract English titles, DOIs, or arXiv IDs from it and call reader_paper_lookup."
                    ),
                )
            return ToolResponse.success(
                text=(
                    "reader_reference_lookup: no references available (empty list, no PDF section text)."
                ),
            )

        try:
            mr = int(parameters.get("max_results") or 5)
        except (TypeError, ValueError):
            mr = 5
        mr = max(1, min(READER_RECOMMEND_MAX_RESULTS, mr))

        focus = str(parameters.get("reference_focus") or "").strip()
        um = ""
        try:
            um = (self._get_user_message() or "").strip()
        except Exception as exc:
            logger.debug("reader_reference_lookup_get_user_message_failed", exc_info=exc)

        query = (focus or um or (refs[0] if refs else "")).strip()[:300]
        if not query or len(query) < 4:
            return ToolResponse.success(
                text="reader_reference_lookup: no usable query text. Provide a title, DOI, or arXiv ID.",
            )

        try:
            from ...api.dependencies import get_searcher
            from ...services.papers.papers_converters import litpaper_to_api_paper
            from ...services.retrieval.search_pipeline import run_search_pipeline_async
            from ...services.retrieval.search_plan import ResolvedSearchPlan
        except Exception as exc:
            logger.warning("reader_reference_lookup_import_failed", exc_info=exc)
            return ToolResponse.error("IMPORT_FAILED", f"import failed: {exc}")

        searcher = get_searcher()
        intent = SearchIntent(
            query=query,
            sources=["arxiv", "openalex"],
            max_results=mr,
            sort="relevance",
        )
        plan = ResolvedSearchPlan.from_search_intent(intent)

        try:
            pip = asyncio.run(
                run_search_pipeline_async(
                    searcher=searcher,
                    plan=plan,
                    max_results=mr,
                )
            )
        except Exception as exc:
            logger.debug("reader_reference_lookup_search_failed", exc_info=exc)
            return ToolResponse.error("SEARCH_FAILED", f"search failed: {exc}")

        collected = [litpaper_to_api_paper(rp.paper) for rp in (pip.ranked or [])[:mr]]
        if not collected:
            return ToolResponse.success(
                text=(
                    f"reader_reference_lookup: no results for query [{query[:80]}]. "
                    "Try a more specific English title, DOI, or arXiv ID."
                ),
            )

        try:
            self._on_papers_found(collected, READER_RELATED_FROM_BIBLIOGRAPHY)
        except Exception as exc:
            logger.debug("reader_reference_lookup_callback_failed", exc_info=exc)

        lines = [
            f"reader_reference_lookup: {len(collected)} papers found from references:"
        ]
        for i, ap in enumerate(collected, start=1):
            t = str(getattr(ap, "title", "") or "").strip() or "(no title)"
            y = getattr(ap, "year", None) or "-"
            lines.append(f"{i}. {t} | year={y}")
        lines.append("Refer to items by number or short title above.")
        return ToolResponse.success(text="\n".join(lines))

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

def resolve_references_via_openalex(
    snap: dict[str, Any], *, max_results: int = 5
) -> list[Any]:
    refs = snap.get("references") or []
    if not refs:
        return []
    from app.api.dependencies import get_searcher
    from app.services.papers.papers_converters import litpaper_to_api_paper
    from app.utils.async_sync import run_coroutine_sync
    searcher = get_searcher()
    results: list[Any] = []
    seen: set[str] = set()
    for ref in refs[:max_results * 3]:
        q = str(ref or "").strip()[:200]
        if not q or q.lower() in seen:
            continue
        seen.add(q.lower())
        try:
            papers = run_coroutine_sync(
                searcher.search_async(q, sources=["openalex", "arxiv"], max_results=2, http_timeout_sec=5),
                op_name="resolve_refs",
            )
            for p in (papers or []):
                api_p = litpaper_to_api_paper(p)
                t = str(getattr(api_p, "title", "") or "").strip().lower()
                if t and t not in seen:
                    seen.add(t)
                    results.append(api_p)
        except Exception:
            continue
        if len(results) >= max_results:
            break
    return results[:max_results]
