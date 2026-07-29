import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from MyAgent.Memory.base import MemoryConfig
from MyAgent.Memory.embedding import get_text_embedder, get_dimension
from MyAgent.Memory.storage.document_store import SQLiteDocumentStore
from MyAgent.base.base import BaseMemory, MemoryItem


class Episode:
    def __init__(
            self,
            episode_id: str,
            user_id: str,
            session_id: str,
            timestamp: datetime,
            content: str,
            context: Dict[str, Any],
            outcome: Optional[str] = None,
            importance: float = 0.5
    ):
        self.episode_id = episode_id
        self.user_id = user_id
        self.session_id = session_id
        self.timestamp = timestamp
        self.content = content
        self.context = context
        self.outcome = outcome
        self.importance = importance


class EpisodicMemory(BaseMemory):
    """情景记忆实现

    特点：
    - 存储具体的交互事件
    - 包含丰富的上下文信息
    - 按时间序列组织
    - 支持模式识别和回溯
    """

    def update(
            self,
            memory_id: str,
            content: str = None,
            importance: float = None,
            metadata: Dict[str, Any] = None
    ) -> bool:
        """更新情景记忆（SQLite为权威，Qdrant按需重嵌入）"""
        updated = False
        for episode in self.episodes:
            if episode.episode_id == memory_id:
                if content is not None:
                    episode.content = content
                if importance is not None:
                    episode.importance = importance
                if metadata is not None:
                    episode.context.update(metadata.get("context", {}))
                    if "outcome" in metadata:
                        episode.outcome = metadata["outcome"]
                updated = True
                break

        # 更新SQLite
        doc_updated = self.doc_store.update_memory(
            memory_id=memory_id,
            content=content,
            importance=importance,
            properties=metadata
        )

        # 如内容变更，重嵌入并upsert到Qdrant
        if content is not None:
            try:
                embedding = self.embedder.encode(content)
                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()
                # 获取更新后的记录以同步payload
                doc = self.doc_store.get_memory(memory_id)
                payload = {
                    "memory_id": memory_id,
                    "user_id": doc["user_id"] if doc else "",
                    "memory_type": "episodic",
                    "importance": (doc.get("importance") if doc else importance) or 0.5,
                    "session_id": (doc.get("properties", {}) or {}).get("session_id"),
                    "content": content
                }
                self.vector_store.add_vectors(
                    vectors=[embedding],
                    metadata=[payload],
                    ids=[memory_id]
                )
            except Exception:
                pass

        return updated or doc_updated

    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)

        # 本地缓存（内存）
        self.episodes: List[Episode] = []
        self.sessions: Dict[str, List[str]] = {}  # session_id -> episode_ids

        # 模式识别缓存
        self.patterns_cache = {}
        self.last_pattern_analysis = None

        # 权威文档存储（SQLite）
        db_dir = self.config.storage_path if hasattr(self.config, 'storage_path') else "./memory_data"
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "memory.db")
        self.doc_store = SQLiteDocumentStore(db_path=db_path)

        # 统一嵌入模型（多语言，默认384维）
        self.embedder = get_text_embedder()

        # 向量存储（Qdrant - 使用连接管理器避免重复连接）
        from ..storage.qdrant_store import QdrantConnectionManager
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.vector_store = QdrantConnectionManager.get_instance(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=os.getenv("QDRANT_COLLECTION", "hello_agents_vectors"),
            vector_size=get_dimension(getattr(self.embedder, 'dimension', 384)),
            distance=os.getenv("QDRANT_DISTANCE", "cosine")
        )

    def add(self, memory_item: MemoryItem) -> str:
        """添加情景记忆"""
        # 从元数据中提取情景信息
        session_id = memory_item.metadata.get("session_id", "default_session")
        context = memory_item.metadata.get("context", {})
        outcome = memory_item.metadata.get("outcome")
        participants = memory_item.metadata.get("participants", [])
        tags = memory_item.metadata.get("tags", [])

        # 创建情景（内存缓存）
        episode = Episode(
            episode_id=memory_item.id,
            user_id=memory_item.user_id,
            session_id=session_id,
            timestamp=memory_item.timestamp,
            content=memory_item.content,
            context=context,
            outcome=outcome,
            importance=memory_item.importance
        )
        self.episodes.append(episode)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(episode.episode_id)

        # 1) 权威存储（SQLite）
        ts_int = int(memory_item.timestamp.timestamp())
        self.doc_store.add_memory(
            memory_id=memory_item.id,
            user_id=memory_item.user_id,
            content=memory_item.content,
            memory_type="episodic",
            timestamp=ts_int,
            importance=memory_item.importance,
            properties={
                "session_id": session_id,
                "context": context,
                "outcome": outcome,
                "participants": participants,
                "tags": tags
            }
        )
        # 2) 向量索引（Qdrant）
        try:
            embedding = self.embedder.encode(memory_item.content)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            self.vector_store.add_vectors(
                vectors=[embedding],
                metadata=[{
                    "memory_id": memory_item.id,
                    "user_id": memory_item.user_id,
                    "memory_type": "episodic",
                    "importance": memory_item.importance,
                    "session_id": session_id,
                    "content": memory_item.content
                }],
                ids=[memory_item.id]
            )
        except Exception:
            # 向量入库失败不影响权威存储
            pass

        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索情景记忆（结构化过滤 + 语义向量检索）"""
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        time_range: Optional[Tuple[datetime, datetime]] = kwargs.get("time_range")
        importance_threshold: Optional[float] = kwargs.get("importance_threshold")

        # 结构化过滤候选（来自权威库）
        candidate_ids: Optional[set] = None
        if time_range is not None or importance_threshold is not None:
            start_ts = int(time_range[0].timestamp()) if time_range else None
            end_ts = int(time_range[1].timestamp()) if time_range else None
            docs = self.doc_store.search_memories(
                user_id=user_id,
                memory_type="episodic",
                start_time=start_ts,
                end_time=end_ts,
                importance_threshold=importance_threshold,
                limit=1000
            )
            candidate_ids = {d["memory_id"] for d in docs}

        # 向量检索（Qdrant）
        try:
            query_vec = self.embedder.encode(query)
            if hasattr(query_vec, "tolist"):
                query_vec = query_vec.tolist()
            where = {"memory_type": "episodic"}
            if user_id:
                where["user_id"] = user_id
            hits = self.vector_store.search_similar(
                query_vector=query_vec,
                limit=max(limit * 5, 20),
                where=where
            )
        except Exception:
            hits = []

        # 过滤与重排
        now_ts = int(datetime.now().timestamp())
        results: List[Tuple[float, MemoryItem]] = []
        seen = set()
        for hit in hits:
            meta = hit.get("metadata", {})
            mem_id = meta.get("memory_id")
            if not mem_id or mem_id in seen:
                continue

            # 检查是否已遗忘
            episode = next((e for e in self.episodes if e.episode_id == mem_id), None)
            if episode and episode.context.get("forgotten", False):
                continue  # 跳过已遗忘的记忆

            if candidate_ids is not None and mem_id not in candidate_ids:
                continue
            if session_id and meta.get("session_id") != session_id:
                continue

            # 从权威库读取完整记录
            doc = self.doc_store.get_memory(mem_id)
            if not doc:
                continue

            # 计算综合分数：向量0.6 + 近因0.2 + 重要性0.2
            vec_score = float(hit.get("score", 0.0))
            age_days = max(0.0, (now_ts - int(doc["timestamp"])) / 86400.0)
            recency_score = 1.0 / (1.0 + age_days)
            imp = float(doc.get("importance", 0.5))

            # 新评分算法：向量检索纯基于相似度，重要性作为加权因子
            # 基础相似度得分（不受重要性影响）
            base_relevance = vec_score * 0.8 + recency_score * 0.2

            # 重要性作为乘法加权因子，范围 [0.8, 1.2]
            importance_weight = 0.8 + (imp * 0.4)

            # 最终得分：相似度 * 重要性权重
            combined = base_relevance * importance_weight

            item = MemoryItem(
                id=doc["memory_id"],
                content=doc["content"],
                memory_type=doc["memory_type"],
                user_id=doc["user_id"],
                timestamp=datetime.fromtimestamp(doc["timestamp"]),
                importance=doc.get("importance", 0.5),
                metadata={
                    **doc.get("properties", {}),
                    "relevance_score": combined,
                    "vector_score": vec_score,
                    "recency_score": recency_score
                }
            )
            results.append((combined, item))
            seen.add(mem_id)

        # 若向量检索无结果，回退到简单关键词匹配（内存缓存）
        if not results:
            fallback = super()._generate_id  # 占位以避免未使用警告
            query_lower = query.lower()
            for ep in self._filter_episodes(user_id, session_id, time_range):
                if query_lower in ep.content.lower():
                    recency_score = 1.0 / (1.0 + max(0.0, (now_ts - int(ep.timestamp.timestamp())) / 86400.0))
                    # 回退匹配：新评分算法
                    keyword_score = 0.5  # 简单关键词匹配的基础分数
                    base_relevance = keyword_score * 0.8 + recency_score * 0.2
                    importance_weight = 0.8 + (ep.importance * 0.4)
                    combined = base_relevance * importance_weight
                    item = MemoryItem(
                        id=ep.episode_id,
                        content=ep.content,
                        memory_type="episodic",
                        user_id=ep.user_id,
                        timestamp=ep.timestamp,
                        importance=ep.importance,
                        metadata={
                            "session_id": ep.session_id,
                            "context": ep.context,
                            "outcome": ep.outcome,
                            "relevance_score": combined
                        }
                    )
                    results.append((combined, item))

        results.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in results[:limit]]

    def remove(self, memory_id: str) -> bool:
        """删除情景记忆（SQLite + Qdrant）"""
        removed = False
        for i, episode in enumerate(self.episodes):
            if episode.episode_id == memory_id:
                removed_episode = self.episodes.pop(i)
                session_id = removed_episode.session_id
                if session_id in self.sessions:
                    self.sessions[session_id].remove(memory_id)
                    if not self.sessions[session_id]:
                        del self.sessions[session_id]
                removed = True
                break

        # 权威库删除
        doc_deleted = self.doc_store.delete_memory(memory_id)

        # 向量库删除
        try:
            self.vector_store.delete_memories([memory_id])
        except Exception:
            pass

        return removed or doc_deleted