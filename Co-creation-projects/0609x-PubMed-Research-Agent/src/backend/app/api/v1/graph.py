# -*- coding: utf-8 -*-
"""Knowledge-graph endpoints backed by Neo4j."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.schemas.graph import GraphStatsOut, GraphSubgraphOut, RelatedPapersOut
from backend.services.agent_factory import build_graph_store
from backend.services.neo4j_store import Neo4jGraphStore

router = APIRouter(prefix="/graph", tags=["graph"])
logger = logging.getLogger(__name__)

_store: Optional[Neo4jGraphStore] = None


def get_graph_store() -> Optional[Neo4jGraphStore]:
    """Lazily build (and reuse) the Neo4j store for the app lifetime."""
    global _store
    if _store is None:
        _store = build_graph_store(settings)
        logger.info("Graph store ready: %s", bool(_store))
    return _store


@router.get("/stats", response_model=GraphStatsOut)
async def graph_stats() -> GraphStatsOut:
    """Return graph node counts and connectivity status."""
    store = get_graph_store()
    if store is None:
        return GraphStatsOut(ready=False, error="Neo4j is not configured or disabled")
    try:
        ready, error = await asyncio.to_thread(store.diagnose)
        if not ready:
            return GraphStatsOut(ready=False, error=error or "Neo4j is unreachable")
        counts = await asyncio.to_thread(store.stats)
        return GraphStatsOut(ready=True, **counts)
    except Exception as exc:
        logger.exception("Graph stats failed")
        raise HTTPException(status_code=500, detail=f"Graph stats failed: {exc}")


@router.get("/subgraph/{pmid}", response_model=GraphSubgraphOut)
async def graph_subgraph(pmid: str, limit: int = 10) -> GraphSubgraphOut:
    """Return a 1-hop subgraph (nodes + links) centered on a paper."""
    store = get_graph_store()
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j graph store is not configured. Run a search first to index papers.",
        )
    try:
        data = await asyncio.to_thread(store.subgraph, pmid, max(1, min(limit, 50)))
        return GraphSubgraphOut(**data)
    except Exception as exc:
        logger.exception("Graph subgraph query failed")
        raise HTTPException(status_code=500, detail=f"Graph subgraph query failed: {exc}")


@router.get("/related/{pmid}", response_model=RelatedPapersOut)
async def related_papers(pmid: str, limit: int = 10) -> RelatedPapersOut:
    """Return papers sharing authors/journals with the given PMID."""
    store = get_graph_store()
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j graph store is not configured. Run a search first to index papers.",
        )
    try:
        rows = await asyncio.to_thread(store.related_papers, pmid, max(1, min(limit, 50)))
        return RelatedPapersOut(pmid=pmid, related=rows)
    except Exception as exc:
        logger.exception("Related papers query failed")
        raise HTTPException(status_code=500, detail=f"Related papers query failed: {exc}")
