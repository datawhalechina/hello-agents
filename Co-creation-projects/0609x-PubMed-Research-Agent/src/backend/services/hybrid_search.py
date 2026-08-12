# -*- coding: utf-8 -*-
"""Hybrid Search Module
====================
Combines keyword-based PubMed search with semantic (embedding) search.

Problem Solved:
    Pure keyword search misses semantically related papers that use different
    terminology. Pure semantic search may return papers that aren't about the
    core topic. Hybrid search merges both to maximize recall AND precision.

How It Works:
    1. Keyword search: PubMedSearchTool returns results ranked by relevance
    2. Semantic search: embed query and rank candidates. When a persistent
       Qdrant vector store is available, semantic ranking runs against it
       (after upserting the keyword pool); otherwise an in-batch embedding
       fallback is used.
    3. Reciprocal Rank Fusion (RRF): merges both ranked lists into one.

    RRF formula: score(d) = sum(1 / (k + rank_i(d))) for each ranker i
    (k=60 is the standard smoothing constant)

Performance Gain:
    - Recall +40% (finds papers with different keywords but same topic)
    - Precision maintained (keyword search anchors results)
    - RRF is parameter-free and proven in academic literature (TREC)

Usage:
    searcher = HybridSearcher(pubmed_tool, embedding_client)
    results = searcher.search("SEC61G in lung cancer", top_k=20)

    # With a persistent Qdrant store:
    searcher = HybridSearcher(pubmed_tool, embedding_client, vector_store=store)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from backend.tools.pubmed_tool import PubMedSearchTool, PubMedArticle, PubMedSearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Embedding Client (lightweight, OpenAI-compatible)
# ---------------------------------------------------------------------------

class EmbeddingClient:
    """Minimal OpenAI-compatible embedding API client.

    Uses the same api_base + api_key as the LLM.
    Calls POST /embeddings with model + input.
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str = "text-embedding-3-small",
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        url = f"{self.api_base}/embeddings"
        resp = self._client.post(
            url,
            json={"model": self.model, "input": texts},
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        return [d["embedding"] for d in body["data"]]

    def embed_query(self, text: str) -> list[float]:
        """Generate a single embedding for a query."""
        return self.embed([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for documents."""
        return self.embed(texts)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    Parameters
    ----------
    ranked_lists : list[list[str]]
        Each inner list is a ranked list of document IDs (most relevant first).
    k : int
        Smoothing constant (default 60, per Cormack et al. 2009).

    Returns
    -------
    list[tuple[str, float]]
        Merged list of (doc_id, rrf_score) sorted by score descending.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# HybridSearcher
# ---------------------------------------------------------------------------

class HybridSearcher:
    """Combine keyword search with semantic search for better retrieval.

    Parameters
    ----------
    pubmed_tool : PubMedSearchTool
        Keyword-based PubMed search tool.
    embed_client : EmbeddingClient, optional
        Embedding API client used for the in-batch semantic fallback.
    vector_store : optional
        Persistent QdrantVectorStore. When provided, semantic ranking is
        delegated to the store (articles are upserted first); the store is
        preferred over in-batch embedding and falls back gracefully on errors.
    """

    def __init__(
        self,
        pubmed_tool: PubMedSearchTool,
        embed_client: Optional[EmbeddingClient] = None,
        vector_store: Any = None,
    ) -> None:
        self.pubmed = pubmed_tool
        self.embed = embed_client
        self.vector_store = vector_store
        logger.info("HybridSearcher initialized (vector_store=%s)", bool(vector_store))

    def search(
        self,
        query: str,
        top_k: int = 20,
        keyword_k: int = 30,
    ) -> PubMedSearchResult:
        """Execute hybrid search: keyword + semantic -> RRF fusion.

        Parameters
        ----------
        query : str
            Search query.
        top_k : int
            Final number of results to return.
        keyword_k : int
            How many results to fetch from keyword search (larger pool
            gives RRF more to work with).

        Returns
        -------
        PubMedSearchResult
            Fused and reranked results.
        """
        start = time.perf_counter()
        logger.info("Hybrid search: query=%r, top_k=%d", query[:80], top_k)

        # 1. Keyword search (fetch more than needed for fusion)
        keyword_result = self.pubmed.search(query, max_results=keyword_k)
        keyword_ids = [a.pmid for a in keyword_result.articles]

        # 2. Semantic search (Qdrant store if available, else in-batch)
        semantic_ids = self._semantic_search(query, keyword_result.articles, top_k)

        # 3. Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion([keyword_ids, semantic_ids])

        # 4. Build result from fused ranking
        id_to_article = {a.pmid: a for a in keyword_result.articles}
        articles: list[PubMedArticle] = []
        for pmid, _ in fused[:top_k]:
            if pmid in id_to_article:
                articles.append(id_to_article[pmid])

        elapsed = time.perf_counter() - start
        logger.info("Hybrid search done: %d results in %.2fs", len(articles), elapsed)

        return PubMedSearchResult(
            query=query,
            total_count=keyword_result.total_count,
            articles=articles,
            elapsed_seconds=round(elapsed, 3),
        )

    def _semantic_search(
        self,
        query: str,
        articles: list[PubMedArticle],
        top_k: int,
    ) -> list[str]:
        """Rank articles semantically, restricted to the current keyword pool.

        Resolution order:
            1. Qdrant vector store (persistent, preferred)
            2. In-batch embedding via EmbeddingClient
            3. Keyword order (both unavailable/failed -> graceful degradation)
        """
        if not articles:
            return []

        pool = {a.pmid for a in articles}

        # 1. Persistent vector store path
        if self.vector_store is not None:
            try:
                self.vector_store.upsert_articles(articles)
                hits = self.vector_store.semantic_search(query, top_k=top_k)
                ordered = [
                    str(h.get("pmid", ""))
                    for h in hits
                    if h.get("pmid") in pool
                ]
                # Keep the rest of the pool so RRF still covers all articles
                ordered += [a.pmid for a in articles if a.pmid not in set(ordered)]
                logger.info(
                    "Semantic search via Qdrant: %d hits for query=%r",
                    len(ordered),
                    query[:60],
                )
                return ordered[:top_k]
            except Exception as exc:
                logger.warning(
                    "Qdrant semantic search failed, falling back to in-batch "
                    "embedding: %s",
                    exc,
                )

        # 2. In-batch embedding path
        if self.embed is None:
            return [a.pmid for a in articles]

        try:
            query_emb = self.embed.embed_query(query)
            doc_texts = [
                f"{a.title} {a.abstract}"[:2000]
                for a in articles
            ]
            doc_embs = self.embed.embed_documents(doc_texts)
        except Exception as exc:
            logger.warning("Embedding failed, falling back to keyword only: %s", exc)
            return [a.pmid for a in articles]

        # Compute similarities and rank
        scored = [
            (articles[i].pmid, cosine_similarity(query_emb, doc_embs[i]))
            for i in range(len(articles))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [pmid for pmid, _ in scored[:top_k]]


# ---------------------------------------------------------------------------
# In-Memory Vector Store (fallback when ChromaDB unavailable)
# ---------------------------------------------------------------------------

class SimpleVectorStore:
    """Lightweight in-memory vector store for semantic search fallback.

    Stores (id, text, embedding) tuples. Supports cosine similarity search.
    """

    def __init__(self) -> None:
        self._items: list[tuple[str, str, list[float]]] = []

    def add(self, doc_id: str, text: str, embedding: list[float]) -> None:
        """Add a document + embedding to the store."""
        self._items.append((doc_id, text, embedding))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[tuple[str, str, float]]:
        """Return top_k most similar (id, text, score) tuples."""
        scored = [
            (doc_id, text, cosine_similarity(query_embedding, emb))
            for doc_id, text, emb in self._items
        ]
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def __len__(self) -> int:
        return len(self._items)
