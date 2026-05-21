
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.paper import Paper as LitPaper

from ..llm.agent_runtime import _exception_chain_predicate, run_agent_task
from ..llm.llm_service import get_llm
from ..search_intent import extract_json_object
from ...settings import get_settings
from .paper_filters import should_exclude_main_conference_paper
from .ranking_prompt import (
    RANKER_SYSTEM_PROMPT,
    RANKER_SYSTEM_PROMPT_RETRY,
    build_ranking_prompt,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LlmPaperRanker",
    "RankedPaper",
    "_papers_to_ranked_pool",
]


def _recall_max_candidates() -> int:
    try:
        return max(8, min(60, int(get_settings().papergraph_recall_max_candidates)))
    except Exception:
        return 24


def _pool_fallback_sort_key(rp: RankedPaper) -> tuple:
    return (
        float(getattr(rp, "fine_score", 0) or 0),
        int(getattr(rp.paper, "year", 0) or 0),
        int(getattr(rp.paper, "citations", 0) or 0),
    )


def _papers_to_ranked_pool(
    papers: list[LitPaper],
    *,
    cap: int,
    prefer_recency: bool,
) -> list[RankedPaper]:
    pool = [RankedPaper(paper=p) for p in papers[: max(1, cap)]]
    if prefer_recency:
        pool.sort(key=lambda x: int(getattr(x.paper, "year", 0) or 0), reverse=True)
    return pool


def _looks_like_llm_timeout(exc: BaseException) -> bool:
    def pred(x: BaseException) -> bool:
        if isinstance(x, TimeoutError):
            return True
        s = str(x).lower()
        return any(
            k in s
            for k in ("timeout", "timed out", "readtimeout", "apitimeout", "agent task timeout")
        )

    return _exception_chain_predicate(exc, pred)


def _is_connectionish_error(exc: BaseException) -> bool:
    etxt = str(exc).lower()
    return any(k in etxt for k in ("connection", "remoteprotocolerror", "server disconnected", "eof"))


@dataclass
class RankedPaper:
    paper: LitPaper
    fine_score: float = 0.0
    final_score: float = 0.0
    ranking_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _is_venue_match(paper: LitPaper, venue: str) -> bool:
    """Check if paper's journal/source matches the target venue."""
    from .paper_filters import has_strong_main_conference_venue_signal
    return has_strong_main_conference_venue_signal(paper, venue)


class LlmPaperRanker:
    """召回去重后由 LLM 直接排序。"""

    def __init__(self, recall_max: int = 24, fine_top_k: int = 10, llm=None):
        self.recall_max = max(8, int(recall_max or 24))
        self.fine_top_k = fine_top_k
        self._llm = llm or get_llm()

    @staticmethod
    def _ranked_paper_dedupe_key(rp: RankedPaper) -> str:
        p = rp.paper
        aid = str(getattr(p, "arxiv_id", "") or "").strip()
        if aid:
            return f"arxiv:{aid}"
        doi = str(getattr(p, "doi", "") or "").strip().lower()
        if doi:
            return f"doi:{doi}"
        t = str(getattr(p, "title", "") or "").strip().lower()[:240]
        return f"t:{t}" if t else f"id:{id(p)}"

    def _parse_ranking_result(self, result: str, papers: list[RankedPaper]) -> list[RankedPaper]:
        if not papers:
            return []
        raw = (result or "").strip()
        if not raw:
            return []

        data: dict[str, Any | None] = None
        try:
            data = extract_json_object(raw)
            if data is None:
                m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
                if m:
                    data = extract_json_object(m.group(1))
            if data is None:
                start, end = raw.find("{"), raw.rfind("}")
                if start >= 0 and end > start:
                    chunk = re.sub(r",\s*([\]}])", r"\1", raw[start : end + 1])
                    data = json.loads(chunk)
                    if not isinstance(data, dict):
                        data = None
        except Exception as e:
            logger.warning("[LlmPaperRanker] 精排 JSON 解析失败: %s", e)
            return []

        if not isinstance(data, dict):
            return []
        rankings = data.get("rankings")
        if not isinstance(rankings, list):
            return []

        result_list: list[RankedPaper] = []
        seen_idx: set[int] = set()
        for r in rankings:
            if not isinstance(r, dict):
                continue
            try:
                idx = int(r.get("paper_index", r.get("index", 0))) - 1
            except (TypeError, ValueError):
                continue
            if idx in seen_idx or not (0 <= idx < len(papers)):
                continue
            seen_idx.add(idx)
            rp = papers[idx]
            try:
                rp.fine_score = float(r.get("fine_score", 0))
            except (TypeError, ValueError):
                rp.fine_score = 0.0
            rp.ranking_reason = str(r.get("reason", "") or "").strip()
            result_list.append(rp)
        return result_list

    def _supplement_ranked(
        self,
        ranked: list[RankedPaper],
        pool: list[RankedPaper],
        top_k: int,
        *,
        allow_supplement: bool = True,
    ) -> list[RankedPaper]:
        cap = min(int(top_k or 10), len(pool))
        if not allow_supplement or len(ranked) >= cap:
            return ranked[:cap]

        keys = {self._ranked_paper_dedupe_key(rp) for rp in ranked}
        out = list(ranked)
        for rp in sorted(pool, key=_pool_fallback_sort_key, reverse=True):
            if len(out) >= cap:
                break
            k = self._ranked_paper_dedupe_key(rp)
            if k in keys:
                continue
            keys.add(k)
            rp.fine_score = float(getattr(rp, "fine_score", 0.0) or 0.0)
            if not getattr(rp, "ranking_reason", ""):
                rp.ranking_reason = "（精排序列未覆盖该项，按召回顺序递补）"
            out.append(rp)
        return out[:cap]

    def _finalize_scores(self, ranked: list[RankedPaper]) -> None:
        for rp in ranked:
            rp.final_score = round(float(rp.fine_score or 0), 2)

    def _invoke_llm_rank(
        self,
        candidates: list[RankedPaper],
        prompt: str,
        *,
        task_name: str,
        agent_name: str,
        system_prompt: str,
        timeout_sec: float,
    ) -> str:
        return run_agent_task(
            task_name=task_name,
            agent_name=agent_name,
            llm=self._llm,
            system_prompt=system_prompt,
            user_prompt=prompt,
            timeout_sec=timeout_sec,
            retries=0,
            task_logger=logger,
        )

    def _rank_from_llm_output(
        self,
        result_text: str,
        candidates: list[RankedPaper],
        top_k: int,
    ) -> tuple[list[RankedPaper], str]:
        ranked = self._parse_ranking_result(result_text, candidates)
        if not ranked:
            ranked = sorted(candidates, key=_pool_fallback_sort_key, reverse=True)[:top_k]
            for rp in ranked:
                rp.fine_score = 0.0
                rp.ranking_reason = rp.ranking_reason or "（精排未返回有效条目，按召回顺序保留）"
            return self._supplement_ranked(ranked, candidates, top_k), "recall_fallback"
        return self._supplement_ranked(ranked, candidates, top_k), "llm_rank"

    def _fine_rank(
        self,
        papers: list[RankedPaper],
        query: str,
        top_k: int = 10,
        *,
        ranking_profile: str = "accuracy",
        target_venue: str | None = None,
        main_conference_proceedings_only: bool = False,
        intent_source_message: str | None = None,
        target_titles: list[str] | None = None,
        authors: list[str] | None = None,
        venues: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        method_acronym: str | None = None,
    ) -> tuple[list[RankedPaper], str]:
        if not papers:
            return [], "llm_rank"

        profile = str(ranking_profile or "accuracy").strip().lower()
        if profile not in ("accuracy", "novelty", "classic"):
            profile = "accuracy"

        try:
            cand_limit = int(str(get_settings().papergraph_fine_rank_candidates))
        except Exception:
            cand_limit = 12
        cand_limit = max(int(top_k or 10), min(40, max(10, cand_limit)))

        try:
            fine_timeout_sec = float(os.getenv("PAPERGRAPH_FINE_RANK_TIMEOUT_SEC", "30").strip() or 30)
        except Exception:
            fine_timeout_sec = 30.0
        fine_timeout_sec = max(10.0, min(120.0, fine_timeout_sec))

        candidates = list(papers or [])[:cand_limit]
        try:
            abs_max = int(os.getenv("PAPERGRAPH_FINE_RANK_ABSTRACT_CHARS", "").strip() or 200)
        except Exception:
            abs_max = 200

        rank_kwargs = dict(
            ranking_profile=profile,
            abstract_max_chars=abs_max,
            target_venue=target_venue,
            main_conference_proceedings_only=main_conference_proceedings_only,
            intent_source_message=intent_source_message,
            target_titles=target_titles,
            authors=authors,
            venues=venues,
            year_from=year_from,
            year_to=year_to,
            method_acronym=method_acronym,
        )

        try:
            prompt = build_ranking_prompt(candidates, query, top_k, **rank_kwargs)
            result_text = self._invoke_llm_rank(
                candidates,
                prompt,
                task_name="paper_ranker_fine_rank",
                agent_name="paper_ranker",
                system_prompt=RANKER_SYSTEM_PROMPT,
                timeout_sec=fine_timeout_sec,
            )
            ranked, fine_method = self._rank_from_llm_output(result_text, candidates, top_k)
            self._finalize_scores(ranked)
            return ranked[:top_k], fine_method

        except Exception as e:
            if _looks_like_llm_timeout(e) or _is_connectionish_error(e):
                try:
                    retry_limit = min(max(int(top_k or 10) * 2, 12), max(12, cand_limit))
                    retry_candidates = list(papers or [])[:retry_limit]
                    prompt2 = build_ranking_prompt(
                        retry_candidates,
                        query,
                        top_k,
                        ranking_profile=profile,
                        abstract_max_chars=min(280, max(160, abs_max // 2)),
                        target_venue=target_venue,
                        main_conference_proceedings_only=main_conference_proceedings_only,
                        intent_source_message=intent_source_message,
                    )
                    ranked2, method2 = self._rank_from_llm_output(
                        self._invoke_llm_rank(
                            retry_candidates,
                            prompt2,
                            task_name="paper_ranker_fine_rank_retry",
                            agent_name="paper_ranker_retry",
                            system_prompt=RANKER_SYSTEM_PROMPT_RETRY,
                            timeout_sec=min(120.0, fine_timeout_sec + 25.0),
                        ),
                        retry_candidates,
                        top_k,
                    )
                    if method2 == "llm_rank":
                        self._finalize_scores(ranked2)
                        return ranked2[:top_k], method2
                except Exception:
                    pass

            if _looks_like_llm_timeout(e):
                logger.warning(
                    "[LlmPaperRanker] 精排 LLM 超时（当前上限 %.0fs），已按召回顺序降级；可提高 "
                    "PAPERGRAPH_FINE_RANK_TIMEOUT_SEC，或减小 PAPERGRAPH_FINE_RANK_CANDIDATES / "
                    "PAPERGRAPH_FINE_RANK_ABSTRACT_CHARS。详情: %s",
                    fine_timeout_sec,
                    str(e)[:200],
                )
            else:
                logger.exception(
                    "[LlmPaperRanker] 精排失败: %s (llm_set=%s, LLM_API_KEY=%s, LLM_BASE_URL=%s, LLM_MODEL_ID=%s)",
                    e,
                    bool(self._llm),
                    ("已配置" if os.getenv("LLM_API_KEY") else "未配置"),
                    os.getenv("LLM_BASE_URL", "未配置"),
                    os.getenv("LLM_MODEL_ID", "未配置"),
                )
            etxt = str(e).lower()
            if any(k in etxt for k in ("proxy", "ssl", "eof", "connection")):
                logger.warning(
                    "[LlmPaperRanker] 提示：若为代理/SSL 握手失败，可在 backend/.env 设置 LLM_DISABLE_PROXY=1 后重启；"
                    "或临时取消 HTTPS_PROXY/ALL_PROXY；或确认 NO_PROXY 包含 LLM 域名（见 llm_service._maybe_disable_proxy_for_llm）。"
                )

            fallback = sorted(list(papers or []), key=_pool_fallback_sort_key, reverse=True)
            if main_conference_proceedings_only and target_venue:
                yf, yt = kwargs.get("year_from"), kwargs.get("year_to")
                pin_y = int(yf) if yf is not None and yf == yt else None
                fallback = [
                    rp
                    for rp in fallback
                    if not should_exclude_main_conference_paper(
                        rp.paper, target_venue, pinned_year=pin_y
                    )
                ]
            self._finalize_scores(fallback)
            return fallback[:top_k], "recall_fallback"

    def rank(
        self,
        papers: list[LitPaper],
        query: str,
        top_k: int | None = None,
        **kwargs: Any,
    ) -> tuple[list[RankedPaper], dict[str, Any]]:
        final_k = top_k or self.fine_top_k
        profile = str(kwargs.get("ranking_profile") or "accuracy").strip().lower()
        if profile not in ("accuracy", "novelty", "classic"):
            profile = "accuracy"
        target_venue = (kwargs.get("target_venue") or "").strip() or None
        main_conf = bool(kwargs.get("main_conference_proceedings_only"))
        if main_conf and target_venue:
            yf, yt = kwargs.get("year_from"), kwargs.get("year_to")
            pin_y = int(yf) if yf is not None and yf == yt else None
            papers = [
                p
                for p in papers
                if not should_exclude_main_conference_paper(p, target_venue, pinned_year=pin_y)
            ]
        sort_mode = str(kwargs.get("sort") or "").strip().lower()
        prefer_recency = bool(kwargs.get("prefer_recency") or sort_mode == "date" or target_venue)
        recall_cap = min(_recall_max_candidates(), max(self.recall_max, final_k + 4))

        # Pre-rank: when venue is specified, boost venue-matched papers ahead of others
        if target_venue:
            papers = sorted(
                papers,
                key=lambda p: (
                    0 if _is_venue_match(p, target_venue) else 1,
                    -(int(getattr(p, "year", 0) or 0)),
                    -(int(getattr(p, "citations", 0) or 0)),
                ),
            )

        candidate_pool = _papers_to_ranked_pool(papers, cap=recall_cap, prefer_recency=prefer_recency)
        if not candidate_pool:
            return [], {"error": "无候选论文"}

        try:
            fine_result, fine_method = self._fine_rank(
                papers=candidate_pool,
                query=query,
                top_k=final_k,
                ranking_profile=profile,
                target_venue=target_venue,
                main_conference_proceedings_only=main_conf,
                intent_source_message=kwargs.get("intent_source_message"),
                target_titles=list(kwargs.get("target_titles") or []),
                authors=list(kwargs.get("authors") or []),
                venues=list(kwargs.get("venues") or []),
                year_from=kwargs.get("year_from"),
                year_to=kwargs.get("year_to"),
                method_acronym=(kwargs.get("method_acronym") or "").strip() or None,
            )
            method = fine_method
        except Exception:
            fine_result = sorted(candidate_pool, key=_pool_fallback_sort_key, reverse=True)[:final_k]
            method = "recall_fallback"

        return fine_result, {
            "ranking_method": method,
            "ranking_profile": profile,
            "total_candidates": len(papers),
            "recall_pool": len(candidate_pool),
            "fine_output": len(fine_result),
        }
