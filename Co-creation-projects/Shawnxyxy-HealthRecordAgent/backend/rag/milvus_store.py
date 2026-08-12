"""
Milvus 存储层（可选启用）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.config import get_config

logger = logging.getLogger(__name__)


def _import_milvus():
    try:
        from pymilvus import (  # type: ignore
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            connections,
            utility,
        )

        return Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    except Exception:
        return None


def _connect() -> bool:
    cfg = get_config().rag
    pkg = _import_milvus()
    if pkg is None:
        logger.warning("pymilvus 不可用，RAG 将回退 SQL 检索")
        return False
    _, _, _, _, connections, _ = pkg
    try:
        connections.connect(
            alias="default",
            uri=cfg.milvus_uri,
            token=cfg.milvus_token or None,
        )
        return True
    except Exception as e:
        logger.warning("Milvus 连接失败，RAG 回退 SQL 检索: %s", e)
        return False


def init_collection(dim: int) -> bool:
    cfg = get_config().rag
    pkg = _import_milvus()
    if pkg is None or not _connect():
        return False
    Collection, CollectionSchema, DataType, FieldSchema, _, utility = pkg
    name = cfg.milvus_collection
    try:
        if utility.has_collection(name):
            return True
        fields = [
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields=fields, description="Health memory chunks")
        col = Collection(name=name, schema=schema)
        index_params = {"metric_type": "IP", "index_type": "AUTOINDEX", "params": {}}
        col.create_index(field_name="vector", index_params=index_params)
        col.load()
        return True
    except Exception as e:
        logger.warning("Milvus 集合初始化失败: %s", e)
        return False


def upsert_chunks(chunks: List[Dict[str, Any]]) -> int:
    cfg = get_config().rag
    pkg = _import_milvus()
    if pkg is None or not chunks:
        return 0
    Collection, _, _, _, _, _ = pkg
    if not _connect():
        return 0
    dim = len(chunks[0].get("vector") or [])
    if dim <= 0 or not init_collection(dim):
        return 0
    try:
        col = Collection(cfg.milvus_collection)
        col.load()
        data = [
            [c["chunk_id"] for c in chunks],
            [c["user_id"] for c in chunks],
            [c["source_type"] for c in chunks],
            [c["source_id"] for c in chunks],
            [c.get("created_at", "") for c in chunks],
            [c["text"] for c in chunks],
            [c["vector"] for c in chunks],
        ]
        col.upsert(data)
        col.flush()
        return len(chunks)
    except Exception as e:
        logger.warning("Milvus upsert 失败: %s", e)
        return 0


def search(
    user_id: str,
    query_vector: List[float],
    top_k: int = 5,
    source_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    cfg = get_config().rag
    pkg = _import_milvus()
    if pkg is None or not query_vector:
        return []
    Collection, _, _, _, _, _ = pkg
    if not _connect():
        return []
    try:
        col = Collection(cfg.milvus_collection)
        col.load()
        expr = f'user_id == "{user_id}"'
        if source_types:
            src_expr = " or ".join([f'source_type == "{s}"' for s in source_types])
            expr = f"{expr} and ({src_expr})"
        res = col.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "IP", "params": {}},
            limit=max(1, min(top_k, 20)),
            expr=expr,
            output_fields=["chunk_id", "source_type", "source_id", "text", "created_at"],
        )
        rows: List[Dict[str, Any]] = []
        for hits in res:
            for h in hits:
                entity = h.entity
                rows.append(
                    {
                        "chunk_id": entity.get("chunk_id"),
                        "source_type": entity.get("source_type"),
                        "source_id": entity.get("source_id"),
                        "text": entity.get("text"),
                        "created_at": entity.get("created_at"),
                        "score": float(h.distance),
                    }
                )
        return rows
    except Exception as e:
        logger.warning("Milvus 检索失败: %s", e)
        return []
