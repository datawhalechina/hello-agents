"""Unit tests for agents/query_rewrite.py (translation + rewrite)."""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.agents.query_rewrite import QueryRewriter
from backend.services.prompt_cache import PromptCache


@pytest.fixture
def llm():
    mock = MagicMock()
    return mock


@pytest.fixture
def rewriter(llm):
    return QueryRewriter(llm=llm)


class TestTranslateToEnglish:
    def test_cjk_query_translated(self, rewriter, llm):
        llm._call_llm.return_value = '{"translated_query": "SEC61G in lung cancer"}'
        out = rewriter.translate_to_english("SEC61G在肺癌中的作用")
        assert out == "SEC61G in lung cancer"

    def test_english_query_passthrough(self, rewriter, llm):
        out = rewriter.translate_to_english("SEC61G in lung cancer")
        assert out == "SEC61G in lung cancer"
        llm._call_llm.assert_not_called()

    def test_mixed_cjk_detected(self, rewriter, llm):
        llm._call_llm.return_value = '{"translated_query": "PD-L1 expression"}'
        out = rewriter.translate_to_english("PD-L1在肺癌中的表达")
        assert out == "PD-L1 expression"

    def test_llm_failure_falls_back(self, rewriter, llm):
        llm._call_llm.side_effect = RuntimeError("boom")
        out = rewriter.translate_to_english("肺癌的免疫治疗")
        assert out == "肺癌的免疫治疗"

    def test_empty_translation_falls_back(self, rewriter, llm):
        llm._call_llm.return_value = '{"translated_query": ""}'
        out = rewriter.translate_to_english("肺癌的免疫治疗")
        assert out == "肺癌的免疫治疗"

    def test_cache_hit_skips_llm(self, rewriter, llm):
        llm._call_llm.return_value = '{"translated_query": "lung cancer"}'
        first = rewriter.translate_to_english("肺癌")
        second = rewriter.translate_to_english("肺癌")
        assert first == second == "lung cancer"
        assert llm._call_llm.call_count == 1


class TestRewrite:
    def test_rewrite_calls_llm(self, rewriter, llm):
        llm._call_llm.return_value = (
            '{"pubmed_query": "SEC61G[Title/Abstract] AND Lung Neoplasms[MeSH]", '
            '"concepts": ["SEC61G"], "mesh_terms": ["Lung Neoplasms"]}'
        )
        result = rewriter.rewrite("SEC61G in lung cancer")
        assert result["pubmed_query"].startswith("SEC61G[Title/Abstract]")
        assert result["concepts"] == ["SEC61G"]
        assert result["cached"] is False

    def test_rewrite_failure_returns_original(self, rewriter, llm):
        llm._call_llm.side_effect = RuntimeError("boom")
        result = rewriter.rewrite("some query")
        assert result["pubmed_query"] == "some query"
        assert result["cached"] is False

    def test_expand_with_synonyms(self, rewriter):
        out = rewriter.expand_with_synonyms("lung cancer treatment")
        assert "NSCLC" in out

    def test_shared_cache_reuses_rewrite_across_agents(self, tmp_path):
        cache = PromptCache(cache_dir=str(tmp_path / "shared-cache"))
        first_llm = MagicMock()
        first_llm._call_llm.return_value = (
            '{"pubmed_query": "SEC61G[Title/Abstract]", "concepts": ["SEC61G"]}'
        )
        second_llm = MagicMock()

        first = QueryRewriter(first_llm, cache=cache)
        second = QueryRewriter(second_llm, cache=cache)

        assert first.rewrite("SEC61G")["cached"] is False
        reused = second.rewrite("SEC61G")

        assert reused["cached"] is True
        assert reused["pubmed_query"] == "SEC61G[Title/Abstract]"
        second_llm._call_llm.assert_not_called()
