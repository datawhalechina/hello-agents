# -*- coding: utf-8 -*-
"""Unit tests for in-batch semantic ranking and keyword fallback paths."""

from __future__ import annotations

from backend.services.hybrid_search import EmbeddingClient, HybridSearcher
from backend.tools.pubmed_tool import PubMedArticle, PubMedSearchResult


class FakePubMedTool:
    def __init__(self, articles):
        self.articles = articles

    def search(self, query, max_results=20):
        return PubMedSearchResult(
            query=query,
            total_count=len(self.articles),
            articles=self.articles[:max_results],
        )


class FakeEmbeddingClient(EmbeddingClient):
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.embedded = []

    def embed_query(self, text):
        if self.fail:
            raise RuntimeError("embedding unavailable")
        return [1.0, 0.0, 0.0]

    def embed_documents(self, texts):
        if self.fail:
            raise RuntimeError("embedding unavailable")
        self.embedded.append(list(texts))
        # PMID 3 is most semantically similar, followed by 2 and then 1.
        return [
            [0.0, 1.0, 0.0],
            [0.8, 0.2, 0.0],
            [1.0, 0.0, 0.0],
        ][: len(texts)]


def _article(pmid):
    return PubMedArticle(pmid=pmid, title=f"Title {pmid}", abstract=f"Abstract {pmid}")


ARTICLES = [_article("1"), _article("2"), _article("3")]


def test_uses_in_batch_embeddings_for_semantic_ranking():
    embed = FakeEmbeddingClient()
    searcher = HybridSearcher(FakePubMedTool(ARTICLES), embed)
    semantic_ids = searcher._semantic_search("SEC61G", ARTICLES, top_k=3)

    assert embed.embedded
    assert semantic_ids == ["3", "2", "1"]


def test_embedding_failure_falls_back_to_keyword_order():
    searcher = HybridSearcher(FakePubMedTool(ARTICLES), FakeEmbeddingClient(fail=True))
    result = searcher.search("SEC61G", top_k=3, keyword_k=5)
    assert [article.pmid for article in result.articles] == ["1", "2", "3"]


def test_keyword_only_when_no_embedding_client():
    searcher = HybridSearcher(FakePubMedTool(ARTICLES), embed_client=None)
    result = searcher.search("SEC61G", top_k=3, keyword_k=5)
    assert [article.pmid for article in result.articles] == ["1", "2", "3"]


def test_hybrid_search_preserves_candidate_set_and_count():
    searcher = HybridSearcher(FakePubMedTool(ARTICLES), FakeEmbeddingClient())
    result = searcher.search("SEC61G", top_k=3, keyword_k=5)
    assert {article.pmid for article in result.articles} == {"1", "2", "3"}
    assert result.total_count == 3


def test_empty_keyword_pool_returns_empty():
    searcher = HybridSearcher(FakePubMedTool([]), embed_client=None)
    result = searcher.search("nothing", top_k=3, keyword_k=5)
    assert result.articles == []
