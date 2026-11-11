# -*- coding: utf-8 -*-
"""Build the full ResearchAgent pipeline from application settings.

Keeps the API layer thin: every endpoint asks this factory for the
components it needs, and all external-service credentials come from
pydantic-settings (never os.environ directly).

Usage:
    from backend.services.agent_factory import build_agent
    agent = build_agent(settings)
    report = agent.research("SEC61G in lung cancer")
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.agents.query_rewrite import QueryRewriter
from backend.agents.research_agent import ResearchAgent
from backend.services.context_compressor import ContextCompressor
from backend.services.hybrid_search import EmbeddingClient, HybridSearcher
from backend.services.literature_summary import LiteratureSummarizer
from backend.services.memory import ConversationMemory
from backend.services.neo4j_store import Neo4jGraphStore
from backend.services.prompt_cache import PromptCache
from backend.services.reranker import LLMReranker
from backend.tools.pubmed_tool import PubMedSearchTool

logger = logging.getLogger(__name__)


def build_pubmed_tool(settings) -> PubMedSearchTool:
    """Create the PubMed E-utilities search tool from settings."""
    return PubMedSearchTool(
        email=settings.pubmed_email,
        api_key=settings.pubmed_api_key or None,
        tool_name=settings.pubmed_tool_name,
        verify_ssl=settings.pubmed_verify_ssl,
    )


def build_summarizer(settings) -> LiteratureSummarizer:
    """Create the OpenAI-compatible LLM summarizer from settings."""
    return LiteratureSummarizer(
        api_base=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
    )


def build_embedding_client(settings) -> EmbeddingClient:
    """Create the DashScope-compatible embedding client from settings."""
    return EmbeddingClient(
        api_base=settings.embed_base_url,
        api_key=settings.embed_api_key,
        model=settings.embed_model_name,
        timeout=30.0,
    )


def build_graph_store(settings) -> Optional[Neo4jGraphStore]:
    """Create the Neo4j graph store when configured and enabled."""
    if not settings.neo4j_enabled:
        logger.info("Neo4j disabled by settings; skipping graph store")
        return None
    if not settings.neo4j_uri or not settings.neo4j_password:
        logger.warning("Neo4j URI/password not configured; skipping graph store")
        return None
    try:
        return Neo4jGraphStore(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
    except Exception as exc:
        logger.warning("Neo4j store initialization failed: %s", exc)
        return None


def build_prompt_cache(settings) -> PromptCache:
    """Build the shared production cache or explicit offline disk backend."""
    backend = settings.prompt_cache_backend.strip().lower()
    if backend not in {"redis", "disk"}:
        raise ValueError("PROMPT_CACHE_BACKEND must be 'redis' or 'disk'")
    return PromptCache(
        cache_dir="./data/cache",
        redis_url=settings.prompt_cache_redis_url if backend == "redis" else None,
        ttl_hours=settings.prompt_cache_ttl_hours,
        namespace=settings.prompt_cache_namespace,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
        lock_timeout=settings.prompt_cache_lock_timeout,
        lock_wait_timeout=settings.prompt_cache_lock_wait_timeout,
    )


def build_agent(settings) -> ResearchAgent:
    """Assemble the complete ResearchAgent with all optional components."""
    pubmed = build_pubmed_tool(settings)
    summarizer = build_summarizer(settings)
    embed = build_embedding_client(settings)
    graph_store = build_graph_store(settings)
    prompt_cache = build_prompt_cache(settings)

    hybrid = HybridSearcher(
        pubmed_tool=pubmed,
        embed_client=embed,
    )

    agent = ResearchAgent(
        pubmed=pubmed,
        summarizer=summarizer,
        rewriter=QueryRewriter(llm=summarizer, cache=prompt_cache),
        hybrid_searcher=hybrid,
        reranker=LLMReranker(llm=summarizer, strategy="pointwise"),
        compressor=ContextCompressor(strategy="hybrid", llm=summarizer),
        cache=prompt_cache,
        memory=ConversationMemory(session_dir="./data/sessions"),
        graph_store=graph_store,
    )
    logger.info(
        "Agent assembled: model=%s, neo4j=%s",
        summarizer.model,
        bool(graph_store),
    )
    return agent
