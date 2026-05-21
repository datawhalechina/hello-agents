"""Pipeline 运行时配置 — 集中读取 settings，减少 pipeline 噪音。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .plan_helpers import effective_max_results, is_pinned_single_year
from .search_plan import ResolvedSearchPlan


@dataclass(frozen=True)
class SearchRuntimeConfig:
    max_results: int
    recall_max: int
    recall_cap: int
    recall_wall: float
    rank_wall: float
    arxiv_fallback_wall: float
    proc_min: int
    proc_enabled: bool
    http_timeout_sec: float
    http_max_attempts: int
    openalex_timeout_sec: float
    dblp_timeout_sec: float | None = None

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        plan: ResolvedSearchPlan,
        max_results: int | None = None,
    ) -> "SearchRuntimeConfig":
        mr = max(int(max_results or getattr(plan, "max_results", None) or 10), 5)
        mr = effective_max_results(plan, mr)

        recall_max = int(plan.recall_max_candidates or 24)
        try:
            recall_cap_setting = int(settings.papergraph_recall_max_candidates)
        except (TypeError, ValueError):
            recall_cap_setting = 24
        recall_cap = max(mr + 4, min(60, recall_cap_setting, recall_max))

        recall_wall = max(
            10.0, min(180.0, float(getattr(settings, "papergraph_search_recall_wall_sec", 42.0)))
        )
        venue = (plan.venues[0] if plan.venues else None) or None
        if is_pinned_single_year(plan) and venue:
            recall_wall = max(recall_wall, 75.0)

        rank_wall = max(
            10.0, min(120.0, float(getattr(settings, "papergraph_fine_rank_pipeline_wall_sec", 25.0)))
        )
        arxiv_fb_wall = max(
            3.0,
            min(90.0, float(getattr(settings, "papergraph_search_arxiv_fallback_wall_sec", 15.0))),
        )

        try:
            proc_min = int(getattr(settings, "papergraph_proceedings_supplement_min_candidates", 8) or 8)
        except (TypeError, ValueError):
            proc_min = 8
        proc_enabled = bool(getattr(settings, "papergraph_proceedings_supplement_enabled", True))

        http_timeout = max(
            2.0, min(60.0, float(getattr(settings, "papergraph_search_recall_http_timeout_sec", 12.0)))
        )
        try:
            http_max_attempts = int(settings.papergraph_search_http_max_attempts)
        except (TypeError, ValueError):
            http_max_attempts = 2
        http_max_attempts = max(1, min(3, http_max_attempts))

        openalex_timeout = 18.0
        dblp_timeout: float | None = None
        if is_pinned_single_year(plan) and venue:
            dblp_timeout = 55.0
            openalex_timeout = 45.0

        return cls(
            max_results=mr,
            recall_max=recall_max,
            recall_cap=recall_cap,
            recall_wall=recall_wall,
            rank_wall=rank_wall,
            arxiv_fallback_wall=arxiv_fb_wall,
            proc_min=proc_min,
            proc_enabled=proc_enabled,
            http_timeout_sec=http_timeout,
            http_max_attempts=http_max_attempts,
            openalex_timeout_sec=openalex_timeout,
            dblp_timeout_sec=dblp_timeout,
        )

    def execution_kwargs(self) -> dict[str, Any]:
        """HTTP/超时等执行参数，不混入用户约束。"""
        out: dict[str, Any] = {
            "http_timeout_sec": self.http_timeout_sec,
            "http_max_attempts": self.http_max_attempts,
            "openalex_timeout_sec": self.openalex_timeout_sec,
        }
        if self.dblp_timeout_sec is not None:
            out["dblp_timeout_sec"] = self.dblp_timeout_sec
        return out
