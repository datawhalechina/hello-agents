
from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class SearchIntent:
    query: str = ""
    raw_user_message: str = ""
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    venues: list[str] = field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    sort: str = "relevance"
    max_results: int = 10
    target_titles: list[str] = field(default_factory=list)
    target_authors: list[str] = field(default_factory=list)
    arxiv_categories: list[str] = field(default_factory=list)
    arxiv_id_list: list[str] = field(default_factory=list)

    use_llm_rank: bool = True
    rerank_recall_max: int = 24
    ranking_rationale: str = ""

    is_short_acronym: bool = False
    wants_classic: bool = False
    wants_recent: bool = False

    use_tavily: bool | None = None

    confidence_level: str = "medium"
    search_strategy: str = "hybrid"
    sources: list[str] = field(default_factory=list)
    ranking_strategy: str = "hybrid"

    main_conference_proceedings_only: bool = False


__all__ = [
    "SearchIntent",
]
