"""
Embedding 封装。默认使用 OpenAI 兼容 embedding 接口。
"""

from __future__ import annotations

import hashlib
import logging
from typing import List

from core.config import get_config

logger = logging.getLogger(__name__)


def _hash_embedding(text: str, dim: int = 64) -> List[float]:
    """
    本地兜底 embedding（仅在外部 embedding 失败时使用）。
    目的不是高质量召回，而是保证流程可运行。
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals: List[float] = []
    for i in range(dim):
        b = digest[i % len(digest)]
        vals.append((b / 255.0) * 2.0 - 1.0)
    return vals


def embed_texts(texts: List[str]) -> List[List[float]]:
    cfg = get_config()
    model = cfg.rag.embedding_model
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=cfg.rag.embedding_api_key or cfg.llm.api_key,
            base_url=cfg.rag.embedding_base_url or cfg.llm.base_url,
        )
        resp = client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]
    except Exception as e:
        logger.warning("Embedding API 调用失败，回退哈希向量: %s", e)
        return [_hash_embedding(t, dim=cfg.rag.fallback_embedding_dim) for t in texts]
