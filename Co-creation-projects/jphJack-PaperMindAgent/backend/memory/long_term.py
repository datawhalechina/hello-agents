"""长期知识记忆：基于 Chroma 向量库存储 Gap / Innovation / 通用知识

- 与 RAG 模块共用 Embedder（从 backend.rag.embedding 导入），但使用独立 collection
- Embedder 与 Chroma 均较重，采用懒加载
- 所有 IO 操作异步化（Chroma 为同步接口，用 asyncio.to_thread 包装）
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional

# 尝试从 RAG 模块导入 Embedder；若依赖未装或模块尚未实现，则兜底为 None，不影响模块定义
try:
    from backend.rag.embedding import Embedder  # type: ignore
except Exception:  # noqa: BLE001 - 兜底导入，任何失败都降级为 None
    Embedder = None  # type: ignore

from backend.config import settings


# 长期知识使用的独立 collection 名称
LONG_TERM_COLLECTION = "long_term_knowledge"


def _gap_to_text(gap: Any) -> str:
    """将 Gap 模型转为可向量化的文本"""
    # 兼容 pydantic 模型与普通对象
    gap_type = getattr(getattr(gap, "gap_type", None), "value", getattr(gap, "gap_type", ""))
    source_papers = getattr(gap, "source_papers", []) or []
    source_str = "; ".join(source_papers) if source_papers else "无"
    return (
        f"【研究空白 / {gap_type}】\n"
        f"描述：{getattr(gap, 'description', '')}\n"
        f"来源论文：{source_str}\n"
        f"论证：{getattr(gap, 'evidence', '')}\n"
        f"置信度：{getattr(gap, 'confidence', '')}"
    )


def _innovation_to_text(innovation: Any) -> str:
    """将 Innovation 模型转为可向量化的文本"""
    source = getattr(getattr(innovation, "source", None), "value", getattr(innovation, "source", ""))
    score = getattr(innovation, "score", None)
    score_str = ""
    if score is not None:
        novelty = getattr(score, "novelty", "")
        feasibility = getattr(score, "feasibility", "")
        significance = getattr(score, "significance", "")
        score_str = f"新颖性={novelty} 可行性={feasibility} 显著性={significance}"
    return (
        f"【创新点 / {source}】\n"
        f"标题：{getattr(innovation, 'title', '')}\n"
        f"思路：{getattr(innovation, 'idea', '')}\n"
        f"Gap 来源：{getattr(innovation, 'gap_origin', '')}\n"
        f"评分：{score_str}\n"
        f"论据支撑：{getattr(innovation, 'supporting_evidence', '')}"
    )


def _flatten_metadata(metadata: dict) -> dict:
    """将 metadata 中的复杂类型扁平化为 Chroma 支持的基本类型（str/int/float/bool/None）"""
    flat: dict[str, Any] = {}
    for k, v in (metadata or {}).items():
        if v is None or isinstance(v, (str, int, float, bool)):
            flat[k] = v
        else:
            # 列表/字典等转为字符串
            flat[k] = str(v)
    return flat


class LongTermMemory:
    """长期知识记忆：向量库存储与语义检索

    每条知识条目结构：{type: gap/innovation/knowledge, content, metadata}
    """

    def __init__(self) -> None:
        # 懒加载：仅在首次使用时初始化 Embedder 与 Chroma
        self._embedder: Any = None
        self._embedder_loaded: bool = False
        self._client: Any = None
        self._collection: Any = None

    # ---------- 懒加载 ----------

    def _get_embedder(self) -> Any:
        """懒加载 Embedder 实例"""
        if not self._embedder_loaded:
            self._embedder_loaded = True
            if Embedder is None:
                raise RuntimeError(
                    "Embedder 不可用：backend.rag.embedding 导入失败"
                    "（请安装 sentence-transformers 并实现 Embedder）"
                )
            # Embedder 可能是类或工厂，统一实例化
            self._embedder = Embedder()
        return self._embedder

    def _get_collection(self) -> Any:
        """懒加载 Chroma collection（同步，仅在主线程初始化一次）"""
        if self._collection is None:
            import chromadb  # 局部导入，避免模块加载即依赖

            path = str(settings.CHROMA_PATH)
            # PersistentClient 将数据持久化到磁盘
            self._client = chromadb.PersistentClient(path=path)
            self._collection = self._client.get_or_create_collection(
                name=LONG_TERM_COLLECTION,
                metadata={"description": "Paper Innovation Agent 长期知识记忆"},
            )
        return self._collection

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """异步向量化文本列表，兼容同步/异步 Embedder 接口

        依次尝试：aembed（异步）-> embed（同步，丢入线程池）-> encode（同步，丢入线程池）
        """
        embedder = self._get_embedder()
        # 1. 异步接口优先
        aembed = getattr(embedder, "aembed", None)
        if callable(aembed):
            result = await aembed(texts)
            return self._normalize_embeddings(result)
        # 2. 同步 embed 接口
        embed = getattr(embedder, "embed", None)
        if callable(embed):
            result = await asyncio.to_thread(embed, texts)
            return self._normalize_embeddings(result)
        # 3. sentence-transformers 风格 encode
        encode = getattr(embedder, "encode", None)
        if callable(encode):
            result = await asyncio.to_thread(encode, texts)
            return self._normalize_embeddings(result)
        raise RuntimeError("Embedder 未提供 aembed/embed/encode 方法")

    @staticmethod
    def _normalize_embeddings(result: Any) -> list[list[float]]:
        """将各种返回形态统一为 list[list[float]]"""
        # numpy ndarray / tensor 等
        if hasattr(result, "tolist"):
            result = result.tolist()
        # 嵌套列表直接返回
        if result and isinstance(result[0], (list, tuple)):
            return [list(v) for v in result]
        # 单条向量被压平的情况（不太可能，兜底）
        return [list(result)]

    # ---------- 写入 ----------

    async def _add(self, entry_type: str, content: str, metadata: dict) -> str:
        """通用写入：向量化 content 并存入 Chroma"""
        # 生成唯一 id
        entry_id = f"{entry_type}_{uuid.uuid4().hex[:12]}"
        flat_meta = _flatten_metadata({"type": entry_type, **metadata})

        # 向量化（异步）
        embeddings = await self._embed([content])

        # Chroma 写入为同步阻塞操作，丢入线程池
        collection = self._get_collection()

        def _do_add() -> None:
            collection.add(
                ids=[entry_id],
                documents=[content],
                metadatas=[flat_meta],
                embeddings=embeddings,
            )

        await asyncio.to_thread(_do_add)
        return entry_id

    async def save_gap(self, gap: Any) -> str:
        """保存 Gap 到长期记忆

        Args:
            gap: Gap 模型实例（backend.models.schemas.Gap）
        Returns:
            存入向量库的条目 id
        """
        content = _gap_to_text(gap)
        gap_type = getattr(getattr(gap, "gap_type", None), "value", getattr(gap, "gap_type", ""))
        metadata = {
            "gap_type": gap_type,
            "source_papers": getattr(gap, "source_papers", []),
            "confidence": getattr(gap, "confidence", 1.0),
            "description": getattr(gap, "description", ""),
        }
        return await self._add("gap", content, metadata)

    async def save_innovation(self, innovation: Any) -> str:
        """保存 Innovation 到长期记忆

        Args:
            innovation: Innovation 模型实例
        Returns:
            存入向量库的条目 id
        """
        content = _innovation_to_text(innovation)
        source = getattr(getattr(innovation, "source", None), "value", getattr(innovation, "source", ""))
        score = getattr(innovation, "score", None)
        metadata = {
            "title": getattr(innovation, "title", ""),
            "source": source,
            "gap_origin": getattr(innovation, "gap_origin", ""),
            "novelty": getattr(score, "novelty", 0.0) if score else 0.0,
            "feasibility": getattr(score, "feasibility", 0.0) if score else 0.0,
            "significance": getattr(score, "significance", 0.0) if score else 0.0,
        }
        return await self._add("innovation", content, metadata)

    async def save_knowledge(self, content: str, metadata: Optional[dict] = None) -> str:
        """保存通用知识条目

        Args:
            content: 知识文本
            metadata: 附加元数据
        Returns:
            存入向量库的条目 id
        """
        return await self._add("knowledge", content, metadata or {})

    # ---------- 检索 ----------

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None,
    ) -> list[dict]:
        """语义检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回条数上限
            filter_type: 可选，按类型过滤（gap/innovation/knowledge）
        Returns:
            命中条目列表，每条 {id, type, content, metadata, distance}
        """
        query_embeddings = await self._embed([query])
        collection = self._get_collection()

        where = {"type": filter_type} if filter_type else None

        def _do_query() -> dict:
            return collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k,
                where=where,
            )

        result = await asyncio.to_thread(_do_query)

        # 解析 Chroma 返回结构（每项都是 list[list[...]]，对应批量查询）
        ids_batch = result.get("ids", [[]])
        docs_batch = result.get("documents", [[]])
        metas_batch = result.get("metadatas", [[]])
        dists_batch = result.get("distances", [[]])

        ids = ids_batch[0] if ids_batch else []
        docs = docs_batch[0] if docs_batch else []
        metas = metas_batch[0] if metas_batch else []
        dists = dists_batch[0] if dists_batch else []

        items: list[dict] = []
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            items.append({
                "id": ids[i] if i < len(ids) else "",
                "type": meta.get("type", ""),
                "content": doc,
                "metadata": meta,
                "distance": dists[i] if i < len(dists) else None,
            })
        return items

    async def load_relevant(self, query: str, top_k: int = 5) -> list[dict]:
        """加载与查询相关的历史 Gap 和 Innovation（用于创新点去重）

        分别按 gap / innovation 类型检索，合并后按距离排序取 top_k
        """
        # 每类各取 top_k，合并后截断
        gaps = await self.search(query, top_k=top_k, filter_type="gap")
        innovations = await self.search(query, top_k=top_k, filter_type="innovation")
        merged = gaps + innovations
        # 距离越小越相关，升序排序
        merged.sort(key=lambda x: x.get("distance") if x.get("distance") is not None else float("inf"))
        return merged[:top_k]
