"""
统一检索接口：retrieve(user_id, query_context)。
优先 Milvus 语义检索，不可用时回退 SQL 文本记忆。
"""

from __future__ import annotations

import time
from collections import Counter
from typing import Any, Dict, List

from core.config import get_config
from memory.store import list_user_memory_chunks_sql
from rag.embedding import embed_texts
from rag.milvus_store import search


def _build_query_text(query_context: Dict[str, Any]) -> str:
    if not query_context:
        return "健康记忆检索"
    keys = [
        "goal",
        "query",
        "scenario",
        "risk_focus",
        "free_notes",
        "today_food_log_text",
    ]
    pieces: List[str] = []
    for k in keys:
        if k in query_context and query_context[k]:
            pieces.append(f"{k}:{query_context[k]}")
    if not pieces:
        pieces.append(str(query_context))
    return " | ".join(pieces)[:4000]


def retrieve(user_id: str, query_context: Dict[str, Any], top_k: int | None = None) -> Dict[str, Any]:
    cfg = get_config().rag
    k = top_k or cfg.top_k
    t0 = time.perf_counter()
    query_text = _build_query_text(query_context)
    chunks: List[Dict[str, Any]] = []
    mode = "sql_fallback"

    if cfg.enabled:
        vec = embed_texts([query_text])[0]
        chunks = search(user_id=user_id, query_vector=vec, top_k=k)
        if chunks:
            mode = "milvus"

    if not chunks:
        rows = list_user_memory_chunks_sql(user_id=user_id, limit=max(8, k * 3))
        chunks = [
            {
                "chunk_id": r["chunk_id"],
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "text": r["text"],
                "created_at": r.get("created_at"),
                "score": 0.0,
            }
            for r in rows[:k]
        ]

    summary = "\n".join([f"- [{c['source_type']}] {c['text']}" for c in chunks[:k]]) or "（暂无检索结果）"
    source_breakdown = dict(Counter([c.get("source_type", "unknown") for c in chunks]))
    ms = int((time.perf_counter() - t0) * 1000)
    return {
        "chunks": chunks[:k],
        "summary": summary[:12000],
        "debug": {
            "rag_enabled": cfg.enabled,
            "mode": mode,
            "retrieved_count": len(chunks[:k]),
            "top_k": k,
            "retrieval_ms": ms,
            "source_breakdown": source_breakdown,
            "query_text_preview": query_text[:240],
        },
    }
