"""Unit tests for agents/research_agent.py"""

from __future__ import annotations

import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.agents.research_agent import ResearchAgent, ResearchReport
from backend.tools.pubmed_tool import (
    PubMedSearchTool,
    PubMedSearchResult,
    PubMedArticle,
    Author,
)
from backend.services.literature_summary import (
    LiteratureSummarizer,
    LiteratureSummary,
    LiteratureSummaryError,
    ResearchHotspot,
    FutureDirection,
    ExperimentalMethod,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def make_articles(n: int = 3) -> list[PubMedArticle]:
    """Create n sample PubMedArticle objects."""
    return [
        PubMedArticle(
            pmid=str(10000 + i),
            title=f"Sample study {i} about SEC61G",
            abstract=f"This is the abstract of study {i}. Methods included...",
            doi=f"10.1000/test{i}",
            authors=[Author(last_name="Smith", fore_name="John")],
            journal="Journal of Test",
            publish_date="2024",
        )
        for i in range(n)
    ]


def make_search_result(query: str, n: int = 3) -> PubMedSearchResult:
    return PubMedSearchResult(
        query=query,
        total_count=n,
        articles=make_articles(n),
    )


def make_summary() -> LiteratureSummary:
    return LiteratureSummary(
        research_background="SEC61G background summary.",
        current_hotspots=[
            ResearchHotspot(
                topic="Prognostic biomarker",
                description="High SEC61G predicts poor survival.",
                evidence=["PMID:10000"],
            )
        ],
        main_findings=["Finding A", "Finding B"],
        experimental_methods=[
            ExperimentalMethod(method="IHC", purpose="Expression", frequency=2)
        ],
        future_directions=[
            FutureDirection(
                direction="Targeted therapy",
                rationale="SEC61G is a driver.",
                challenges=["Selectivity"],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pubmed():
    tool = MagicMock(spec=PubMedSearchTool)
    tool.search.return_value = make_search_result("SEC61G", n=5)
    return tool


@pytest.fixture
def mock_summarizer():
    s = MagicMock(spec=LiteratureSummarizer)
    s.model = "gpt-4o-mini"
    s.summarize.return_value = make_summary()
    return s


@pytest.fixture
def agent(mock_pubmed, mock_summarizer):
    return ResearchAgent(
        pubmed=mock_pubmed,
        summarizer=mock_summarizer,
        max_articles=10,
        language="en",
    )


# ---------------------------------------------------------------------------
# ResearchReport
# ---------------------------------------------------------------------------

class TestResearchReport:
    def test_to_json(self):
        report = ResearchReport(
            query="test query",
            model_used="gpt-4o",
            status="completed",
            articles=[{"pmid": "1", "title": "T"}],
            main_findings=["Finding A"],
        )
        result = report.to_json()
        data = json.loads(result)
        assert data["query"] == "test query"
        assert data["status"] == "completed"
        assert len(data["articles"]) == 1
        assert "Finding A" in data["main_findings"]

    def test_default_values(self):
        report = ResearchReport(query="q", model_used="m")
        assert report.total_pubmed_hits == 0
        assert report.articles == []
        assert report.errors == []
        assert report.status == "pending"
        assert report.research_background == ""


# ---------------------------------------------------------------------------
# ResearchAgent
# ---------------------------------------------------------------------------

class TestResearchAgent:
    def test_reports_monotonic_pipeline_progress(self, agent):
        events = []

        report = agent.research(
            "SEC61G in Lung Cancer",
            progress_callback=lambda stage, percent, message: events.append(
                (stage, percent, message)
            ),
        )

        assert report.status == "completed"
        assert [event[0] for event in events] == [
            "preparing_query",
            "searching",
            "filtering",
            "indexing_graph",
            "reranking",
            "compressing",
            "summarizing",
            "finalizing",
        ]
        assert [event[1] for event in events] == sorted(event[1] for event in events)
        assert all(event[2] for event in events)

    def test_happy_path(self, agent):
        report = agent.research("SEC61G in Lung Cancer")

        assert report.status == "completed"
        assert report.query == "SEC61G in Lung Cancer"
        assert report.total_pubmed_hits == 5
        assert len(report.articles) == 5
        assert report.articles[0]["pmid"] == "10000"
        assert "SEC61G background" in report.research_background
        assert len(report.current_hotspots) == 1
        assert len(report.main_findings) == 2
        assert len(report.experimental_methods) == 1
        assert len(report.future_directions) == 1
        assert report.model_used == "gpt-4o-mini"
        assert report.elapsed_seconds >= 0
        assert report.errors == []

    def test_custom_max_results(self, agent, mock_pubmed):
        report = agent.research("query", max_results=5)
        mock_pubmed.search.assert_called_once_with("query", max_results=5)

    def test_custom_language(self, agent, mock_summarizer):
        report = agent.research("query", language="zh")
        mock_summarizer.summarize.assert_called_once()
        call_kwargs = mock_summarizer.summarize.call_args
        assert call_kwargs[1]["language"] == "zh"

    def test_pubmed_failure(self, mock_summarizer):
        mock_pubmed = MagicMock(spec=PubMedSearchTool)
        mock_pubmed.search.side_effect = RuntimeError("API down")

        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
        )
        report = agent.research("query")

        assert report.status == "failed"
        assert "API down" in report.errors[0]
        assert report.total_pubmed_hits == 0
        assert report.articles == []

    def test_no_articles_found(self, agent, mock_pubmed):
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="rare query",
            total_count=0,
            articles=[],
        )
        report = agent.research("rare query")

        assert report.status == "completed"
        assert report.total_pubmed_hits == 0
        assert not report.articles
        assert report.research_background == ""

    def test_summarizer_failure(self, mock_pubmed):
        mock_summarizer = MagicMock(spec=LiteratureSummarizer)
        mock_summarizer.model = "test-model"
        mock_summarizer.summarize.side_effect = LiteratureSummaryError("timeout")

        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
        )
        report = agent.research("query")

        assert report.status == "partial"
        assert report.total_pubmed_hits == 5
        assert len(report.articles) == 5
        assert "timeout" in report.errors[0]
        assert report.research_background == ""

    def test_to_json_output(self, agent):
        report = agent.research("SEC61G")
        json_str = report.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["query"] == "SEC61G"
        assert data["status"] == "completed"
        assert "current_hotspots" in data
        assert "future_directions" in data

    def test_uses_default_max_articles(self, agent, mock_pubmed):
        report = agent.research("query")
        mock_pubmed.search.assert_called_once_with("query", max_results=10)

    def test_default_language(self, agent, mock_summarizer):
        agent.language = "zh"
        report = agent.research("query")
        call_kwargs = mock_summarizer.summarize.call_args
        assert call_kwargs[1]["language"] == "zh"


# ---------------------------------------------------------------------------
# Phase 2: Optional components (rewriter / hybrid / rerank / compress / cache / memory)
# ---------------------------------------------------------------------------

class TestOptionalComponents:
    def test_rewriter_used_and_query_passed(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = {
            "pubmed_query": "SEC61G[All Fields] AND Lung Neoplasms[MeSH]",
            "concepts": ["SEC61G"],
            "mesh_terms": ["Lung Neoplasms"],
        }
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
        )
        report = agent.research("SEC61G in Lung Cancer")
        mock_rewriter.rewrite.assert_called_once_with("SEC61G in Lung Cancer")
        mock_pubmed.search.assert_called_once_with(
            "SEC61G[All Fields] AND Lung Neoplasms[MeSH]", max_results=20
        )
        assert report.rewritten_query == "SEC61G[All Fields] AND Lung Neoplasms[MeSH]"

    def test_rewriter_failure_falls_back_to_raw_query(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.side_effect = RuntimeError("llm down")
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
        )
        report = agent.research("raw query")
        mock_pubmed.search.assert_called_once_with("raw query", max_results=20)
        assert report.errors, "expected a non-fatal error recorded"
        assert report.status == "completed"

    def test_hybrid_searcher_used(self, mock_pubmed, mock_summarizer):
        mock_hybrid = MagicMock()
        mock_hybrid.search.return_value = make_search_result("hybrid", n=5)
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            hybrid_searcher=mock_hybrid,
        )
        report = agent.research("query")
        mock_hybrid.search.assert_called_once()
        # hybrid search must not ALSO call raw pubmed
        mock_pubmed.search.assert_not_called()
        assert report.total_pubmed_hits == 5

    def test_hybrid_failure_falls_back_to_keyword(self, mock_pubmed, mock_summarizer):
        mock_hybrid = MagicMock()
        mock_hybrid.search.side_effect = RuntimeError("semantic search unavailable")
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            hybrid_searcher=mock_hybrid,
        )
        report = agent.research("query")
        mock_pubmed.search.assert_called_once_with("query", max_results=20)
        assert report.errors, "expected non-fatal error recorded"
        assert report.status == "completed"

    def test_reranker_used(self, mock_pubmed, mock_summarizer):
        mock_rerank = MagicMock()
        # rerank returns the same articles (order preserved by mock)
        mock_rerank.rerank.side_effect = lambda q, arts, top_k=10: arts[:top_k]
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            reranker=mock_rerank,
        )
        report = agent.research("query")
        mock_rerank.rerank.assert_called_once()
        assert report.total_pubmed_hits == 5

    def test_reranker_respects_requested_result_count(self, mock_pubmed, mock_summarizer):
        mock_pubmed.search.return_value = make_search_result("query", n=20)
        mock_rerank = MagicMock()
        mock_rerank.rerank.side_effect = lambda q, arts, top_k=10: arts[:top_k]
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            reranker=mock_rerank,
        )

        report = agent.research("query", max_results=20)

        mock_rerank.rerank.assert_called_once()
        assert mock_rerank.rerank.call_args.kwargs["top_k"] == 20
        assert len(report.articles) == 20

    def test_reranker_failure_falls_back_to_fast(self, mock_pubmed, mock_summarizer):
        mock_rerank = MagicMock()
        mock_rerank.rerank.side_effect = RuntimeError("llm down")
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            reranker=mock_rerank,
        )
        report = agent.research("SEC61G lung cancer")
        assert report.errors, "expected non-fatal error recorded"
        assert report.status == "completed"
        assert report.total_pubmed_hits == 5

    def test_compressor_used(self, mock_pubmed, mock_summarizer):
        mock_comp = MagicMock()
        mock_comp.compress.side_effect = lambda arts, query="", max_chars=400: [
            {**a, "abstract": a["abstract"][:50], "compressed": True} for a in arts
        ]
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            compressor=mock_comp,
        )
        report = agent.research("query")
        mock_comp.compress.assert_called_once()
        assert report.status == "completed"

    def test_compressor_failure_falls_back_to_raw(self, mock_pubmed, mock_summarizer):
        mock_comp = MagicMock()
        mock_comp.compress.side_effect = RuntimeError("regex bug")
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            compressor=mock_comp,
        )
        report = agent.research("query")
        assert report.errors
        assert report.status == "completed"
        # articles still have original abstract text
        assert report.articles[0]["abstract"].startswith("This is the abstract")

    def test_cache_hit_skips_llm_call(self, mock_pubmed, mock_summarizer):
        mock_cache = MagicMock()
        # Cache HIT: return pre-built summary dict
        mock_cache.get_or_compute.return_value = (make_summary().model_dump(), True)
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            cache=mock_cache,
        )
        report = agent.research("query")
        mock_cache.get_or_compute.assert_called_once()
        # summarize must NOT be called on cache hit
        mock_summarizer.summarize.assert_not_called()
        assert report.status == "completed"
        assert "SEC61G background" in report.research_background

    def test_cache_miss_calls_llm(self, mock_pubmed, mock_summarizer):
        mock_cache = MagicMock()
        mock_cache.get_or_compute.side_effect = lambda key, fn: (fn(), False)
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            cache=mock_cache,
        )
        report = agent.research("query")
        mock_summarizer.summarize.assert_called_once()
        assert report.status == "completed"

    def test_memory_records_turn(self, mock_pubmed, mock_summarizer):
        mock_mem = MagicMock()
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            memory=mock_mem,
        )
        report = agent.research("query")
        mock_mem.add_turn.assert_called_once()
        turn = mock_mem.add_turn.call_args[0]
        assert turn[0] == "query"
        assert isinstance(turn[1], dict)
        assert turn[1]["status"] == "completed"

    def test_memory_failure_ignored(self, mock_pubmed, mock_summarizer):
        mock_mem = MagicMock()
        mock_mem.add_turn.side_effect = RuntimeError("disk full")
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            memory=mock_mem,
        )
        report = agent.research("query")
        assert report.status == "completed"  # memory failure must not break report

    def test_all_components_together(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = {"pubmed_query": "rewritten"}
        mock_hybrid = MagicMock()
        mock_hybrid.search.return_value = make_search_result("hybrid", n=5)
        mock_rerank = MagicMock()
        mock_rerank.rerank.side_effect = lambda q, arts, top_k=10: arts[:top_k]
        mock_comp = MagicMock()
        mock_comp.compress.side_effect = lambda arts, query="", max_chars=400: arts
        mock_cache = MagicMock()
        mock_cache.get_or_compute.side_effect = lambda key, fn: (fn(), False)
        mock_mem = MagicMock()

        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
            hybrid_searcher=mock_hybrid,
            reranker=mock_rerank,
            compressor=mock_comp,
            cache=mock_cache,
            memory=mock_mem,
        )
        report = agent.research("query")
        assert report.status == "completed"
        mock_rewriter.rewrite.assert_called_once()
        mock_hybrid.search.assert_called_once()
        mock_rerank.rerank.assert_called_once()
        mock_comp.compress.assert_called_once()
        mock_cache.get_or_compute.assert_called_once()
        mock_mem.add_turn.assert_called_once()


# ---------------------------------------------------------------------------
# Graph store integration
# ---------------------------------------------------------------------------


class FakeGraphStore:
    def __init__(self, fail=False):
        self.fail = fail
        self.upserted = []

    def upsert_articles(self, articles):
        if self.fail:
            raise RuntimeError("neo4j down")
        self.upserted.append(list(articles))


class TestGraphStore:
    def test_graph_store_used_after_search(self, mock_pubmed, mock_summarizer):
        graph = FakeGraphStore()
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            graph_store=graph,
        )
        report = agent.research("SEC61G")
        assert report.status == "completed"
        assert graph.upserted and len(graph.upserted[0]) == 5
        assert not any("Neo4j" in e for e in report.errors)

    def test_graph_store_failure_ignored(self, mock_pubmed, mock_summarizer):
        graph = FakeGraphStore(fail=True)
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            graph_store=graph,
        )
        report = agent.research("SEC61G")
        assert report.status == "completed"
        assert any("Neo4j" in e for e in report.errors)

    def test_graph_store_none_is_noop(self, mock_pubmed, mock_summarizer):
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
        )
        report = agent.research("SEC61G")
        assert report.status == "completed"
        assert not any("Neo4j" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Search modes, sorting and filtering
# ---------------------------------------------------------------------------

class TestSearchModes:
    def test_keyword_mode_skips_rewrite_and_hybrid(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.translate_to_english.return_value = "SEC61G"
        mock_rewriter.rewrite.return_value = {
            "pubmed_query": "should not be used",
            "concepts": [],
            "mesh_terms": [],
        }
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
        )
        report = agent.research("SEC61G", search_mode="keyword")
        assert report.search_mode == "keyword"
        assert report.rewritten_query == "SEC61G"
        mock_rewriter.rewrite.assert_not_called()
        mock_pubmed.search.assert_called_once_with("SEC61G", max_results=20)
        assert report.status in ("completed", "partial")

    def test_advanced_mode_uses_rewrite(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.translate_to_english.return_value = "SEC61G in lung cancer"
        mock_rewriter.rewrite.return_value = {
            "pubmed_query": "SEC61G[Title/Abstract] AND Lung Neoplasms[MeSH]",
            "concepts": ["SEC61G"],
            "mesh_terms": ["Lung Neoplasms"],
        }
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
        )
        report = agent.research("SEC61G in lung cancer", search_mode="advanced")
        mock_rewriter.translate_to_english.assert_called_once_with("SEC61G in lung cancer")
        mock_rewriter.rewrite.assert_called_once_with("SEC61G in lung cancer")
        assert report.rewritten_query == "SEC61G[Title/Abstract] AND Lung Neoplasms[MeSH]"

    def test_chinese_query_auto_translated(self, mock_pubmed, mock_summarizer):
        mock_rewriter = MagicMock()
        mock_rewriter.translate_to_english.return_value = "SEC61G in lung cancer"
        mock_rewriter.rewrite.return_value = {
            "pubmed_query": "SEC61G AND Lung Neoplasms",
            "concepts": [],
            "mesh_terms": [],
        }
        agent = ResearchAgent(
            pubmed=mock_pubmed,
            summarizer=mock_summarizer,
            rewriter=mock_rewriter,
        )
        report = agent.research("SEC61G在肺癌中的作用", search_mode="advanced")
        mock_rewriter.translate_to_english.assert_called_once_with("SEC61G在肺癌中的作用")
        assert report.rewritten_query == "SEC61G AND Lung Neoplasms"


class TestSorting:
    def test_date_desc_sort_applied(self, mock_pubmed, mock_summarizer):
        articles = [
            PubMedArticle(pmid="1", title="old", abstract="a", journal="J",
                          publish_date="2021 Jan"),
            PubMedArticle(pmid="2", title="new", abstract="b", journal="J",
                          publish_date="2025 Mar"),
            PubMedArticle(pmid="3", title="mid", abstract="c", journal="J",
                          publish_date="2023"),
        ]
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="q", total_count=3, articles=articles,
        )
        agent = ResearchAgent(pubmed=mock_pubmed, summarizer=mock_summarizer)
        report = agent.research("SEC61G", search_mode="keyword", sort_by="date_desc")
        pmids = [a["pmid"] for a in report.articles]
        assert pmids == ["2", "3", "1"]
        assert report.sort_by == "date_desc"

    def test_date_asc_sort_applied(self, mock_pubmed, mock_summarizer):
        articles = [
            PubMedArticle(pmid="1", title="old", abstract="a", journal="J",
                          publish_date="2021 Jan"),
            PubMedArticle(pmid="2", title="new", abstract="b", journal="J",
                          publish_date="2025 Mar"),
        ]
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="q", total_count=2, articles=articles,
        )
        agent = ResearchAgent(pubmed=mock_pubmed, summarizer=mock_summarizer)
        report = agent.research("SEC61G", search_mode="keyword", sort_by="date_asc")
        assert [a["pmid"] for a in report.articles] == ["1", "2"]


class TestFiltering:
    def test_year_filter(self, mock_pubmed, mock_summarizer):
        articles = [
            PubMedArticle(pmid="1", title="a", abstract="x", journal="J",
                          publish_date="2020"),
            PubMedArticle(pmid="2", title="b", abstract="y", journal="J",
                          publish_date="2024"),
        ]
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="q", total_count=2, articles=articles,
        )
        agent = ResearchAgent(pubmed=mock_pubmed, summarizer=mock_summarizer)
        report = agent.research("SEC61G", search_mode="keyword", min_year=2022)
        assert [a["pmid"] for a in report.articles] == ["2"]
        assert any("筛选" in e for e in report.errors)

    def test_impact_factor_filter(self, mock_pubmed, mock_summarizer):
        articles = [
            PubMedArticle(pmid="1", title="a", abstract="x", journal="Nature",
                          publish_date="2023"),
            PubMedArticle(pmid="2", title="b", abstract="y", journal="Sci Rep",
                          publish_date="2023"),
            PubMedArticle(pmid="3", title="c", abstract="z", journal="Unknown J",
                          publish_date="2023"),
        ]
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="q", total_count=3, articles=articles,
        )
        agent = ResearchAgent(pubmed=mock_pubmed, summarizer=mock_summarizer)
        report = agent.research(
            "SEC61G", search_mode="keyword", min_impact_factor=10.0
        )
        # Nature (50.5) kept; Sci Rep (3.8) dropped; unknown journal kept
        assert [a["pmid"] for a in report.articles] == ["1", "3"]

    def test_all_filtered_out_returns_empty(self, mock_pubmed, mock_summarizer):
        articles = [
            PubMedArticle(pmid="1", title="a", abstract="x", journal="J",
                          publish_date="2020"),
        ]
        mock_pubmed.search.return_value = PubMedSearchResult(
            query="q", total_count=1, articles=articles,
        )
        agent = ResearchAgent(pubmed=mock_pubmed, summarizer=mock_summarizer)
        report = agent.research("SEC61G", search_mode="keyword", min_year=2030)
        assert report.articles == []
        assert report.status == "completed"
