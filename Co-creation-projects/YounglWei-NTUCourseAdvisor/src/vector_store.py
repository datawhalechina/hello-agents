"""向量检索后端：RAGStore 快照 → 智谱 embedding → 余弦排序。

实现 hello_agents 检索层 SearchBackend 协议，与 RAGStore 的 BM25
经 HybridSearch 做 RRF 融合（框架原生组件，见教程第 7 章）。

向量缓存落盘（JSON），按 (model_id, store revision, chunk 集合) 判失效；
未命中时对全量 chunk 重新 embedding 并写回缓存。
规模说明：~190 卡 × 2048 维纯 Python 余弦，单查询 <0.5s，不引 numpy。
"""

import json
import math
from dataclasses import replace
from pathlib import Path

from hello_agents.retrieval import OpenAIEmbeddingProvider, RAGStore, RetrievalResult

# 智谱 embeddings 接口单次批量上限（保守取 16）
EMBED_BATCH_SIZE = 16


def make_zhipu_provider(model: str, api_key: str, base_url: str) -> OpenAIEmbeddingProvider:
    """构造智谱 embedding provider（OpenAI 兼容 client）。"""
    from openai import OpenAI  # 延迟导入，避免不联网场景也拉起 client

    client = OpenAI(api_key=api_key, base_url=base_url)
    dimension = {"embedding-2": 1024, "embedding-3": 2048}[model]
    return OpenAIEmbeddingProvider(client, model, dimension)


class VectorSearchBackend:
    """余弦向量检索；实现 SearchBackend 协议（search(query, limit)）。

    传入 RAGStore 与 EmbeddingProvider；首次检索时构建/加载向量索引。
    暴露 .store 属性供 HybridSearch 核对修订号（框架约定）。
    """

    def __init__(self, store: RAGStore, provider: OpenAIEmbeddingProvider,
                 cache_path: Path):
        self.store = store
        self.provider = provider
        self.cache_path = Path(cache_path)
        self._chunks: list[RetrievalResult] | None = None
        self._vectors: list[list[float]] | None = None
        self._norms: list[float] | None = None

    # ---------- 索引构建 / 缓存 ----------

    def _ensure_index(self) -> None:
        if self._chunks is not None:
            return
        revision, chunks = self.store.snapshot()
        cache = self._load_cache()
        vectors = None
        if cache and cache["model_id"] == self.provider.model_id \
                and cache["revision"] == revision \
                and set(cache["vectors"]) == {c.chunk_id for c in chunks}:
            vectors = [cache["vectors"][c.chunk_id] for c in chunks]
            print(f"[vector] 命中缓存 {self.cache_path.name}"
                  f"（model={self.provider.model} revision={revision}）")
        if vectors is None:
            vectors = self._embed_all(chunks)
            self._save_cache(revision, chunks, vectors)
        self._chunks = chunks
        self._vectors = vectors
        self._norms = [math.sqrt(sum(x * x for x in v)) for v in vectors]

    def _embed_all(self, chunks: list[RetrievalResult]) -> list[list[float]]:
        texts = [c.content for c in chunks]
        vectors: list[list[float]] = []
        total = len(texts)
        for start in range(0, total, EMBED_BATCH_SIZE):
            batch = texts[start:start + EMBED_BATCH_SIZE]
            vectors.extend(self.provider.embed_documents(batch))
            print(f"[vector] embedding {min(start + EMBED_BATCH_SIZE, total)}/{total}")
        return vectors

    def _load_cache(self) -> dict | None:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None  # 缓存损坏视为未命中，重建

    def _save_cache(self, revision: int, chunks: list[RetrievalResult],
                    vectors: list[list[float]]) -> None:
        # 7 位小数足够余弦排序，体积缩小约一半
        payload = {
            "model_id": self.provider.model_id,
            "model": self.provider.model,
            "revision": revision,
            "vectors": {c.chunk_id: [round(x, 7) for x in v]
                        for c, v in zip(chunks, vectors)},
        }
        self.cache_path.write_text(json.dumps(payload), encoding="utf-8")
        print(f"[vector] 缓存写出 {self.cache_path.name}"
              f"（{len(chunks)} 条，model={self.provider.model}）")

    # ---------- 检索 ----------

    def search(self, query: str, limit: int = 5) -> list[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1 到 100 的整数")
        self._ensure_index()
        qv = self.provider.embed_query(query)
        qn = math.sqrt(sum(x * x for x in qv))
        scored = []
        for chunk, vec, norm in zip(self._chunks, self._vectors, self._norms):
            score = sum(a * b for a, b in zip(qv, vec)) / (qn * norm)
            scored.append((score, chunk))
        scored.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))
        return [replace(chunk, score=score) for score, chunk in scored[:limit]]
