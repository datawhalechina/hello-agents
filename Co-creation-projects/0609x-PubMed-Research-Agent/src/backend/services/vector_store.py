# -*- coding: utf-8 -*-
"""Qdrant vector store integration for semantic literature retrieval.

Problem Solved:
    PubMed keyword search + in-batch embedding cannot leverage previously
    indexed literature. A persistent vector store (Qdrant Cloud) lets the
    system reuse embeddings across queries and powers RAG-style retrieval.

How It Works:
    1. Articles are embedded with an OpenAI-compatible EmbeddingClient
       (DashScope text-embedding-v3) and upserted into a Qdrant collection.
    2. semantic_search() embeds the query and returns the top-k article
       payloads ranked by cosine similarity.

Design Notes:
    - qdrant-client is imported lazily so the rest of the app keeps working
      (with graceful degradation) when the package is not installed.
    - Point ids are stable UUIDs derived from the PMID, so re-upserting the
      same article overwrites its vector instead of duplicating it.

Usage:
    store = QdrantVectorStore(url, api_key, collection_name="pubmed_articles",
                              embedding_client=embed_client)
    store.upsert_articles(articles)          # list[PubMedArticle] or dicts
    hits = store.semantic_search(query, top_k=10)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from backend.services.hybrid_search import EmbeddingClient

logger = logging.getLogger(__name__)

try:  # lazy-friendly: expose the import target for tests and feature detection
    from qdrant_client import QdrantClient  # noqa: F401
    _QDRANT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when package is absent
    QdrantClient = None  # type: ignore[assignment]
    _QDRANT_AVAILABLE = False


class VectorStoreError(Exception):
    """Raised when the vector store is unavailable or a call fails."""


def _pmid_to_point_id(pmid: str) -> str:
    """Return a stable Qdrant point id (UUID v5) for a PubMed id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"pubmed:{pmid}"))


class QdrantVectorStore:
    """Qdrant Cloud-backed vector store for PubMed articles.

    Parameters
    ----------
    url : str
        Qdrant server URL (e.g. https://xxxx.aws.cloud.qdrant.io).
    api_key : str
        Qdrant API key.
    collection_name : str
        Name of the Qdrant collection to use.
    embedding_client : EmbeddingClient, optional
        OpenAI-compatible embedding client (DashScope text-embedding-v3).
    timeout : float
        HTTP timeout for Qdrant calls.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        collection_name: str = "pubmed_articles",
        embedding_client: Optional[EmbeddingClient] = None,
        timeout: float = 30.0,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embedding_client = embedding_client
        self.timeout = timeout
        self._client: Any = None
        logger.info(
            "QdrantVectorStore configured (url=%s, collection=%s)",
            url,
            collection_name,
        )

    # ------------------------------------------------------------------
    # Client access (lazy)
    # ------------------------------------------------------------------

    @property
    def client(self) -> Any:
        """Lazily instantiate the Qdrant client."""
        if self._client is None:
            if not _QDRANT_AVAILABLE:
                raise VectorStoreError(
                    "qdrant-client is not installed. "
                    "Run: pip install 'qdrant-client>=1.12.0'"
                )
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=self.timeout,
            )
            logger.info("Qdrant client connected: %s", self.url)
        return self._client

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True when the collection exists and is reachable."""
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception as exc:
            logger.warning("Qdrant readiness check failed: %s", exc)
            return False

    def count(self) -> int:
        """Return the number of stored points in the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return int(getattr(info, "points_count", 0) or 0)
        except Exception as exc:
            logger.warning("Qdrant count failed: %s", exc)
            return 0

    def ensure_collection(self, vector_size: int) -> None:
        """Create the collection if it does not already exist."""
        from qdrant_client.models import Distance, VectorParams

        client = self.client
        try:
            client.get_collection(self.collection_name)
            logger.debug("Qdrant collection exists: %s", self.collection_name)
            return
        except Exception:
            pass  # not found -> create below

        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(
            "Qdrant collection created: %s (dim=%d)",
            self.collection_name,
            vector_size,
        )

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def upsert_articles(self, articles: list[Any]) -> int:
        """Embed articles and upsert them into the collection.

        Accepts PubMedArticle objects or plain dicts (as produced by
        PubMedArticle.to_dict()). Returns the number of points upserted.
        """
        if not articles:
            return 0
        if self.embedding_client is None:
            raise VectorStoreError(
                "embedding_client is required to upsert articles"
            )

        from qdrant_client.models import PointStruct

        texts = [self._article_text(a) for a in articles]
        vectors = self.embedding_client.embed_documents(texts)
        if not vectors:
            raise VectorStoreError("Embedding API returned no vectors")

        self.ensure_collection(vector_size=len(vectors[0]))

        points = [
            PointStruct(
                id=_pmid_to_point_id(self._article_pmid(a)),
                vector=vectors[i],
                payload=self._article_payload(a),
            )
            for i, a in enumerate(articles)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info("Qdrant upserted %d articles", len(points))
        return len(points)

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        """Embed the query and return top-k article payloads with scores.

        Each returned dict is the stored article payload plus a "score" key.
        """
        if self.embedding_client is None:
            raise VectorStoreError(
                "embedding_client is required for semantic_search"
            )
        if top_k <= 0:
            return []

        query_vector = self.embedding_client.embed_query(query)
        hits = self._query_points(query_vector, top_k)

        results: list[dict] = []
        for hit in hits:
            payload = dict(getattr(hit, "payload", None) or {})
            payload["score"] = float(getattr(hit, "score", 0.0))
            results.append(payload)
        return results

    def _query_points(self, query_vector: list[float], top_k: int) -> list[Any]:
        """Call the client, tolerating both query_points and legacy search APIs."""
        client = self.client
        try:
            response = client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            return list(getattr(response, "points", []) or [])
        except AttributeError:
            response = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
            return list(response or [])

    # ------------------------------------------------------------------
    # Article helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _article_pmid(article: Any) -> str:
        if isinstance(article, dict):
            return str(article.get("pmid", ""))
        return str(getattr(article, "pmid", ""))

    @staticmethod
    def _article_text(article: Any) -> str:
        if isinstance(article, dict):
            title = article.get("title", "") or ""
            abstract = article.get("abstract", "") or ""
        else:
            title = getattr(article, "title", "") or ""
            abstract = getattr(article, "abstract", "") or ""
        return f"{title} {abstract}".strip()[:3000]

    @staticmethod
    def _article_payload(article: Any) -> dict:
        if isinstance(article, dict):
            return article
        if hasattr(article, "to_dict"):
            return article.to_dict()
        return {}
