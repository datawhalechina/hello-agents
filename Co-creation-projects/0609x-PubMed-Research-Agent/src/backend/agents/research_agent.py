"""
ResearchAgent

Orchestrates the full research workflow:
  User Query -> Query Rewrite -> PubMed Search -> RAG Hybrid Search
              -> Rerank -> Context Compress -> LLM Summary -> JSON Report

All optional components (rewriter, hybrid searcher, reranker, compressor,
cache, memory) gracefully degrade: if any is missing or raises, the agent
falls back to the previous working stage instead of failing the request.

Usage:
    from backend.tools.pubmed_tool import PubMedSearchTool
    from backend.services.literature_summary import LiteratureSummarizer
    from backend.agents.research_agent import ResearchAgent

    pubmed = PubMedSearchTool(email="...", verify_ssl=False)
    summarizer = LiteratureSummarizer.from_preset("deepseek-flash", api_key="...")
    agent = ResearchAgent(pubmed=pubmed, summarizer=summarizer)
    report = agent.research("SEC61G in Lung Cancer")
    print(report.to_json())
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from pydantic import BaseModel, Field

from backend.tools.pubmed_tool import PubMedSearchTool, PubMedSearchResult
from backend.services.literature_summary import (
    LiteratureSummarizer,
    LiteratureSummary,
    LiteratureSummaryError,
)
from backend.agents.query_rewrite import QueryRewriter
from backend.services.hybrid_search import HybridSearcher
from backend.services.reranker import LLMReranker
from backend.services.context_compressor import ContextCompressor
from backend.services.prompt_cache import PromptCache
from backend.services.memory import ConversationMemory
from backend.services.neo4j_store import Neo4jGraphStore
from backend.services.journal_metrics import JournalMetrics
from backend.services.literature_sorting import filter_articles, sort_articles

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Models
# ---------------------------------------------------------------------------

class ResearchReport(BaseModel):
    """Final structured report from a research query."""

    # Metadata
    query: str = Field(description="Original user research question")
    model_used: str = Field(description="LLM model used for summarization")
    language: str = Field(default="en", description="Output language")
    elapsed_seconds: float = Field(
        default=0.0,
        description="Total wall-clock time for the full workflow",
    )
    rewritten_query: str = Field(
        default="",
        description="Query string actually sent to PubMed (after rewrite, if any)",
    )

    search_mode: str = Field(
        default="advanced",
        description="Search mode: keyword (raw keywords) or advanced (LLM-rewritten query)",
    )
    sort_by: str = Field(
        default="relevance",
        description="Result ordering: relevance, date_desc, date_asc",
    )

    # Search results
    total_pubmed_hits: int = Field(
        default=0,
        description="Number of articles returned by PubMed",
    )
    articles: list[dict] = Field(
        default_factory=list,
        description="Fetched articles (pmid, title, abstract, doi, etc.)",
    )

    # Literature analysis
    research_background: str = Field(default="")
    current_hotspots: list[dict] = Field(default_factory=list)
    main_findings: list[str] = Field(default_factory=list)
    experimental_methods: list[dict] = Field(default_factory=list)
    future_directions: list[dict] = Field(default_factory=list)

    # Errors
    errors: list[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during the workflow",
    )
    status: str = Field(
        default="pending",
        description="Workflow status: pending|running|completed|partial|failed",
    )

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a pretty-printed JSON string."""
        import json
        return json.dumps(
            self.model_dump(),
            indent=indent,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# ResearchAgent
# ---------------------------------------------------------------------------

class ResearchAgent:
    """End-to-end research agent for PubMed literature analysis.

    Workflow (with all optional components enabled):
        0. Query Rewrite     - natural language -> PubMed syntax
        1. Hybrid Search     - keyword + semantic (Qdrant) -> RRF fusion
        2. Rerank            - LLM pointwise/listwise scoring
        3. Compress          - token reduction before LLM summary
        4. Summarize         - 5-dimension structured analysis
        5. Cache + Memory    - dedupe LLM calls, record session turns

    Parameters
    ----------
    pubmed : PubMedSearchTool
        Configured PubMed search tool instance.
    summarizer : LiteratureSummarizer
        Configured LLM summarizer instance.
    max_articles : int
        Default max articles to fetch per query (1-100).
    language : str
        Default output language ("en" or "zh").
    rewriter : QueryRewriter, optional
        Rewrites the user query into PubMed syntax. Missing -> raw query.
    hybrid_searcher : HybridSearcher, optional
        Merges keyword + semantic rankings. Missing -> keyword-only search.
    reranker : LLMReranker, optional
        Re-ranks retrieved articles. Missing -> keep retrieval order.
    compressor : ContextCompressor, optional
        Compresses abstracts before summarization. Missing -> raw abstracts.
    cache : PromptCache, optional
        Caches summarizer output by (language, model, PMID list).
    memory : ConversationMemory, optional
        Records (query, report) turns for multi-turn research sessions.
    """

    def __init__(
        self,
        pubmed: PubMedSearchTool,
        summarizer: LiteratureSummarizer,
        max_articles: int = 20,
        language: str = "en",
        rewriter: Optional[QueryRewriter] = None,
        hybrid_searcher: Optional[HybridSearcher] = None,
        reranker: Optional[LLMReranker] = None,
        compressor: Optional[ContextCompressor] = None,
        cache: Optional[PromptCache] = None,
        memory: Optional[ConversationMemory] = None,
        graph_store: Optional[Neo4jGraphStore] = None,
        journal_metrics: Optional[JournalMetrics] = None,
    ) -> None:
        self.pubmed = pubmed
        self.summarizer = summarizer
        self.max_articles = max_articles
        self.language = language
        self.rewriter = rewriter
        self.hybrid_searcher = hybrid_searcher
        self.reranker = reranker
        self.compressor = compressor
        self.cache = cache
        self.memory = memory
        self.graph_store = graph_store
        self._journal_metrics = journal_metrics

        enabled = []
        if self.rewriter:
            enabled.append("rewrite")
        if self.hybrid_searcher:
            enabled.append("hybrid")
        if self.reranker:
            enabled.append("rerank")
        if self.compressor:
            enabled.append("compress")
        if self.cache:
            enabled.append("cache")
        if self.memory:
            enabled.append("memory")
        if self.graph_store:
            enabled.append("graph")

        logger.info(
            "ResearchAgent initialized (max=%d, lang=%s, model=%s, enabled=%s)",
            max_articles,
            language,
            summarizer.model,
            ",".join(enabled) or "none",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def research(
        self,
        query: str,
        max_results: Optional[int] = None,
        language: Optional[str] = None,
        search_mode: str = "advanced",
        sort_by: str = "relevance",
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_impact_factor: Optional[float] = None,
    ) -> ResearchReport:
        """Execute the full research workflow.

        Parameters
        ----------
        query : str
            The research question (e.g. "SEC61G in Lung Cancer").
        max_results : int, optional
            Override the default max articles to fetch.
        language : str, optional
            Override the default output language.
        search_mode : str
            ``keyword`` searches PubMed with the (translated) keywords only;
            ``advanced`` additionally rewrites the query into optimized
            PubMed syntax (MeSH, boolean) before searching.
        sort_by : str
            Result ordering: ``relevance``, ``date_desc``, ``date_asc``.
        min_year / max_year : int, optional
            Inclusive publication-year window.
        min_impact_factor : float, optional
            Keep only articles from journals with a known impact factor
            at or above this value.

        Returns
        -------
        ResearchReport
            Structured JSON-serializable report.
        """
        start_time = time.perf_counter()
        max_n = max_results or self.max_articles
        lang = language or self.language
        mode = search_mode if search_mode in ("keyword", "advanced") else "advanced"
        sort_key = sort_by if sort_by in ("relevance", "date_desc", "date_asc") else "relevance"

        logger.info(
            "Research started: query=%r, max=%d, lang=%s, mode=%s, sort=%s",
            query, max_n, lang, mode, sort_key,
        )

        report = ResearchReport(
            query=query,
            model_used=self.summarizer.model,
            language=lang,
            status="running",
            search_mode=mode,
            sort_by=sort_key,
        )

        # --- Step 0: Query Prep (translate -> keyword / advanced rewrite) ---
        english_query = self._safe_translate(query, report)
        if mode == "keyword":
            search_query = english_query
            logger.info("Keyword mode: using raw keywords %r", search_query[:100])
        else:
            search_query = self._safe_rewrite(english_query, report)
        report.rewritten_query = search_query

        # --- Step 1: Search (hybrid in advanced mode, keyword-only in keyword mode) ---
        logger.info("[Step 1/4] Searching PubMed... query=%r", search_query[:100])
        search_result = self._safe_search(
            search_query,
            max_n,
            report,
            use_hybrid=(mode == "advanced"),
        )

        if not search_result or not search_result.articles:
            if report.status != "failed":
                report.status = "completed"
            report.elapsed_seconds = round(time.perf_counter() - start_time, 3)
            logger.warning(
                "No articles found for query=%r (%.2fs)",
                query,
                report.elapsed_seconds,
            )
            return report

        report.total_pubmed_hits = search_result.total_count

        # --- Step 1.5: Apply user filters (year / impact factor) ---
        kept, dropped = filter_articles(
            search_result.articles,
            min_year=min_year,
            max_year=max_year,
            min_impact_factor=min_impact_factor,
            journal_metrics=self._get_journal_metrics(),
        )
        if dropped:
            msg = f"筛选后保留 {len(kept)}/{len(search_result.articles)} 篇（排除 {dropped} 篇）"
            logger.info(msg)
            report.errors.append(msg)
        if not kept:
            report.status = "completed"
            report.elapsed_seconds = round(time.perf_counter() - start_time, 3)
            logger.warning("All articles filtered out for query=%r", query)
            return report

        report.articles = [art.to_dict() for art in kept]

        # --- Step 2: Knowledge graph (optional) ---
        self._safe_graph_store(report.articles, report)

        # --- Step 3: Rerank (optional) ---
        articles = self._safe_rerank(query, kept, report)

        # --- Step 3.5: Sort (date / relevance) ---
        articles = sort_articles(articles, sort_key)
        # Keep the displayed article order in sync with the chosen sort.
        report.articles = [art.to_dict() for art in articles]

        # --- Step 4: Compress (optional) ---
        article_dicts = [art.to_dict() for art in articles]
        article_dicts = self._safe_compress(article_dicts, query, report)

        # --- Step 4: LLM Summary (with cache) ---
        summary = self._safe_summarize(article_dicts, lang, report)

        if summary:
            self._merge_summary(report, summary)
            report.status = "completed"
        else:
            report.status = "partial"

        # --- Record memory turn ---
        if self.memory is not None:
            try:
                self.memory.add_turn(query, report.model_dump())
                logger.info("Memory: recorded turn for query=%r", query[:60])
            except Exception as exc:
                logger.warning("Memory add_turn failed: %s", exc)

        # --- Finalize ---
        report.elapsed_seconds = round(time.perf_counter() - start_time, 3)
        logger.info(
            "Research completed: status=%s, articles=%d, %.2fs",
            report.status,
            report.total_pubmed_hits,
            report.elapsed_seconds,
        )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------


    def _safe_graph_store(self, articles: list[dict], report: ResearchReport) -> None:
        """Index retrieved articles into the Neo4j graph; never fails the flow."""
        if self.graph_store is None:
            return
        try:
            self.graph_store.upsert_articles(articles)
            logger.info("Knowledge graph: indexed %d articles", len(articles))
        except Exception as exc:
            msg = f"Neo4j graph indexing failed (ignored): {exc}"
            logger.warning(msg)
            report.errors.append(msg)

    def _safe_translate(self, query: str, report: ResearchReport) -> str:
        """Translate a Chinese query into English; pass through otherwise."""
        if self.rewriter is None:
            return query
        try:
            translated = self.rewriter.translate_to_english(query)
            if isinstance(translated, str) and translated.strip():
                return translated
            return query
        except Exception as exc:
            msg = f"Query translation failed, using original query: {exc}"
            logger.warning(msg)
            report.errors.append(msg)
            return query

    def _get_journal_metrics(self) -> JournalMetrics:
        """Lazily build the journal impact-factor lookup table."""
        if self._journal_metrics is None:
            self._journal_metrics = JournalMetrics()
        return self._journal_metrics

    def _safe_rewrite(self, query: str, report: ResearchReport) -> str:

        """Rewrite query via LLM; fall back to the raw query on any failure."""
        if self.rewriter is None:
            return query
        try:
            result = self.rewriter.rewrite(query)
            rewritten = result.get("pubmed_query") or query
            if rewritten != query:
                logger.info("Query rewritten: %r -> %r", query[:60], rewritten[:100])
            return rewritten
        except Exception as exc:
            msg = f"Query rewrite failed, using original query: {exc}"
            logger.warning(msg)
            report.errors.append(msg)
            return query

    def _safe_search(
        self,
        query: str,
        max_n: int,
        report: ResearchReport,
        use_hybrid: bool = True,
    ) -> Optional[PubMedSearchResult]:
        """Run hybrid search if available; fall back to keyword-only."""
        if use_hybrid and self.hybrid_searcher is not None:
            try:
                logger.info("Hybrid search: keyword + semantic")
                return self.hybrid_searcher.search(
                    query,
                    top_k=max_n,
                    keyword_k=min(max_n * 2, 50),
                )
            except Exception as exc:
                msg = f"Hybrid search failed, falling back to keyword: {exc}"
                logger.warning(msg)
                report.errors.append(msg)

        try:
            return self.pubmed.search(query, max_results=max_n)
        except Exception as exc:
            msg = f"PubMed search failed: {exc}"
            logger.error(msg)
            report.errors.append(msg)
            report.status = "failed"
            return None

    def _safe_rerank(
        self,
        query: str,
        articles,
        report: ResearchReport,
        top_k: int = 10,
    ):
        """Rerank articles with LLM; fall back to fast heuristic on failure."""
        if self.reranker is None:
            return articles
        try:
            logger.info("Reranking %d articles -> top %d", len(articles), top_k)
            return self.reranker.rerank(query, articles, top_k=top_k)
        except Exception as exc:
            msg = f"Rerank failed, using fast heuristic: {exc}"
            logger.warning(msg)
            report.errors.append(msg)
            try:
                return LLMReranker.fast_rerank(query, articles, top_k=top_k)
            except Exception:
                return articles

    def _safe_compress(
        self,
        article_dicts: list[dict],
        query: str,
        report: ResearchReport,
    ) -> list[dict]:
        """Compress abstracts; fall back to raw articles on failure."""
        if self.compressor is None:
            return article_dicts
        try:
            logger.info("Compressing %d abstracts", len(article_dicts))
            return self.compressor.compress(article_dicts, query=query)
        except Exception as exc:
            msg = f"Compression failed, using raw abstracts: {exc}"
            logger.warning(msg)
            report.errors.append(msg)
            return article_dicts

    def _safe_summarize(
        self,
        articles: list[dict],
        language: str,
        report: ResearchReport,
    ) -> Optional[LiteratureSummary]:
        """Run LLM summarization (cached), capturing errors into the report."""

        def _call() -> LiteratureSummary:
            return self.summarizer.summarize(articles, language=language)

        if self.cache is not None:
            cache_key = (
                f"summarize:{language}:{self.summarizer.model}:"
                + ":".join(a.get("pmid", "") for a in articles)
            )
            try:
                value, hit = self.cache.get_or_compute(cache_key, _call)
                logger.info("Summary cache %s for %d articles", "HIT" if hit else "MISS", len(articles))
                if isinstance(value, dict):
                    return LiteratureSummary(**value)
                if isinstance(value, LiteratureSummary):
                    return value
            except LiteratureSummaryError as exc:
                msg = f"LLM summarization failed: {exc}"
                logger.error(msg)
                report.errors.append(msg)
                return None
            except Exception as exc:
                msg = f"LLM summarization unexpected error: {exc}"
                logger.error(msg)
                report.errors.append(msg)
                return None

        try:
            return _call()
        except LiteratureSummaryError as exc:
            msg = f"LLM summarization failed: {exc}"
            logger.error(msg)
            report.errors.append(msg)
            return None
        except Exception as exc:
            msg = f"LLM summarization unexpected error: {exc}"
            logger.error(msg)
            report.errors.append(msg)
            return None

    @staticmethod
    def _merge_summary(report: ResearchReport, summary: LiteratureSummary) -> None:
        """Merge LiteratureSummary fields into the ResearchReport."""
        report.research_background = summary.research_background
        report.main_findings = summary.main_findings
        report.current_hotspots = [
            h.model_dump() for h in summary.current_hotspots
        ]
        report.experimental_methods = [
            m.model_dump() for m in summary.experimental_methods
        ]
        report.future_directions = [
            d.model_dump() for d in summary.future_directions
        ]
        report.model_used = summary.model_used or report.model_used
