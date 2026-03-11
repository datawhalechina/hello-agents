"""感知记忆实现（长存的多模态）

按照第8章架构设计的感知记忆（长期、多模态），提供：
- 多模态数据存储（文本、图像、音频等）
- 结构化元数据 + 向量索引（SQLite + Qdrant）
- 同模态检索（跨模态在无CLIP/CLAP依赖时有限）
- 懒加载编码：文本用 sentence-transformers；图像/音频用轻量确定性哈希向量
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import hashlib
import os
import random
import logging

logger = logging.getLogger(__name__)

from ..base import BaseMemory, MemoryItem, MemoryConfig
from ..storage import SQLiteDocumentStore, QdrantVectorStore
from ..embedding import get_text_embedder, get_dimension

class Perception:
    """感知数据实体"""
    
    def __init__(
        self,
        perception_id: str,
        data: Any,
        modality: str,
        encoding: Optional[List[float]] = None,
        metadata: Dict[str, Any] = None
    ):
        self.perception_id = perception_id
        self.data = data
        self.modality = modality  # text, image, audio, video, structured
        self.encoding = encoding or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.data_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """计算数据哈希"""
        if isinstance(self.data, str):
            return hashlib.md5(self.data.encode()).hexdigest()
        elif isinstance(self.data, bytes):
            return hashlib.md5(self.data).hexdigest()
        else:
            return hashlib.md5(str(self.data).encode()).hexdigest()

class PerceptualMemory(BaseMemory):
    """感知记忆实现
    
    特点：
    - 支持多模态数据（文本、图像、音频等）
    - 跨模态相似性搜索
    - 感知数据的语义理解
    - 支持内容生成和检索
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 感知数据存储（内存缓存）
        self.perceptions: Dict[str, Perception] = {}
        self.perceptual_memories: List[MemoryItem] = []
        
        # 模态索引
        self.modality_index: Dict[str, List[str]] = {}  # modality -> perception_ids
        
        # 支持的模态
        self.supported_modalities = set(self.config.perceptual_memory_modalities)
        
        # 文档权威存储（SQLite）
        db_dir = getattr(self.config, 'storage_path', "./memory_data")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "memory.db")
        self.doc_store = SQLiteDocumentStore(db_path=db_path)

        # 嵌入维度（与统一文本嵌入保持一致）
        self.text_embedder = get_text_embedder()
        self.vector_dim = get_dimension(getattr(self.text_embedder, 'dimension', 384))

        # 可选加载：图像CLIP与音频CLAP（缺依赖则优雅降级为哈希编码）
        self._clip_model = None
        self._clip_processor = None
        self._clap_model = None
        self._clap_processor = None
        self._image_dim = None
        self._audio_dim = None
        try:
            from transformers import CLIPModel, CLIPProcessor
            clip_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
            self._clip_model = CLIPModel.from_pretrained(clip_name)
            self._clip_processor = CLIPProcessor.from_pretrained(clip_name)
            # 估计输出维度
            self._image_dim = self._clip_model.config.projection_dim if hasattr(self._clip_model.config, 'projection_dim') else 512
        except Exception:
            self._clip_model = None
            self._clip_processor = None
            self._image_dim = self.vector_dim
        try:
            from transformers import ClapProcessor, ClapModel
            clap_name = os.getenv("CLAP_MODEL", "laion/clap-htsat-unfused")
            self._clap_model = ClapModel.from_pretrained(clap_name)
            self._clap_processor = ClapProcessor.from_pretrained(clap_name)
            # 估计输出维度
            self._audio_dim = getattr(self._clap_model.config, 'projection_dim', None) or 512
        except Exception:
            self._clap_model = None
            self._clap_processor = None
            self._audio_dim = self.vector_dim

        # 向量存储（Qdrant）— 按模态拆分集合，避免维度冲突，使用连接管理器避免重复连接
        from ..storage.qdrant_store import QdrantConnectionManager
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        base_collection = os.getenv("QDRANT_COLLECTION", "hello_agents_vectors")
        distance = os.getenv("QDRANT_DISTANCE", "cosine")
        
        self.vector_stores: Dict[str, QdrantVectorStore] = {}
        # 文本集合
        self.vector_stores["text"] = QdrantConnectionManager.get_instance(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=f"{base_collection}_perceptual_text",
            vector_size=self.vector_dim,
            distance=distance
        )
        # 图像集合（若CLIP不可用，维度退化为text维度）
        self.vector_stores["image"] = QdrantConnectionManager.get_instance(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=f"{base_collection}_perceptual_image",
            vector_size=int(self._image_dim or self.vector_dim),
            distance=distance
        )
        # 音频集合（若CLAP不可用，维度退化为text维度）
        self.vector_stores["audio"] = QdrantConnectionManager.get_instance(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=f"{base_collection}_perceptual_audio",
            vector_size=int(self._audio_dim or self.vector_dim),
            distance=distance
        )
        
        # 编码器（轻量实现；真实场景可替换为CLIP/CLAP等）
        self.encoders = self._init_encoders()
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加感知记忆（SQLite权威 + Qdrant向量）"""
        modality = memory_item.metadata.get("modality", "text")
        raw_data = memory_item.metadata.get("raw_data", memory_item.content)
        if modality not in self.supported_modalities:
            raise ValueError(f"不支持的模态类型: {modality}")

        # 编码感知数据
        perception = self._encode_perception(raw_data, modality, memory_item.id)

        # 缓存与索引
        self.perceptions[perception.perception_id] = perception
        if modality not in self.modality_index:
            self.modality_index[modality] = []
        self.modality_index[modality].append(perception.perception_id)

        # 存储记忆项（缓存）
        memory_item.metadata["perception_id"] = perception.perception_id
        memory_item.metadata["modality"] = modality
        # 不把大向量放到metadata中，避免膨胀
        self.perceptual_memories.append(memory_item)

        # 1) SQLite 权威入库
        ts_int = int(memory_item.timestamp.timestamp())
        self.doc_store.add_memory(
            memory_id=memory_item.id,
            user_id=memory_item.user_id,
            content=memory_item.content,
            memory_type="perceptual",
            timestamp=ts_int,
            importance=memory_item.importance,
            properties={
                "perception_id": perception.perception_id,
                "modality": modality,
                "context": memory_item.metadata.get("context", {}),
                "tags": memory_item.metadata.get("tags", []),
            }
        )

        # 2) Qdrant 向量入库（按模态写入对应集合）
        try:
            vector = perception.encoding
            store = self._get_vector_store_for_modality(modality)
            store.add_vectors(
                vectors=[vector],
                metadata=[{
                    "memory_id": memory_item.id,
                    "user_id": memory_item.user_id,
                    "memory_type": "perceptual",
                    "modality": modality,
                    "importance": memory_item.importance,
                    "content": memory_item.content,
                }],
                ids=[memory_item.id]
            )
        except Exception:
            pass

        return memory_item.id
    
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索感知记忆（可筛模态；同模态向量检索+时间/重要性融合）"""
        user_id = kwargs.get("user_id")
        target_modality = kwargs.get("target_modality")  # 可选：限制目标模态
        query_modality = kwargs.get("query_modality", target_modality or "text")

        # 仅在同模态情况下进行向量检索（跨模态需要CLIP/CLAP，此处保留简单回退）
        try:
            qvec = self._encode_data(query, query_modality)
            where = {"memory_type": "perceptual"}
            if user_id:
                where["user_id"] = user_id
            if target_modality:
                where["modality"] = target_modality
            store = self._get_vector_store_for_modality(target_modality or query_modality)
            hits = store.search_similar(
                query_vector=qvec,
                limit=max(limit * 5, 20),
                where=where
            )
        except Exception:
            hits = []

        # 融合排序
        now_ts = int(datetime.now().timestamp())
        results: List[Tuple[float, MemoryItem]] = []
        seen = set()
        for hit in hits:
            meta = hit.get("metadata", {})
            mem_id = meta.get("memory_id")
            if not mem_id or mem_id in seen:
                continue
            if target_modality and meta.get("modality") != target_modality:
                continue
            doc = self.doc_store.get_memory(mem_id)
            if not doc:
                continue
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
                importance=imp,
                metadata={**doc.get("properties", {}), "relevance_score": combined,
                          "vector_score": vec_score, "recency_score": recency_score}
            )
            results.append((combined, item))
            seen.add(mem_id)

        # 简单回退：若无命中且有目标模态，则按SQLite结构化过滤+关键词兜底
        if not results:
            for m in self.perceptual_memories:
                if target_modality and m.metadata.get("modality") != target_modality:
                    continue
                if query.lower() in (m.content or "").lower():
                    recency_score = 1.0 / (1.0 + max(0.0, (now_ts - int(m.timestamp.timestamp())) / 86400.0))
                    # 回退匹配：新评分算法
                    keyword_score = 0.5  # 简单关键词匹配的基础分数
                    base_relevance = keyword_score * 0.8 + recency_score * 0.2
                    importance_weight = 0.8 + (m.importance * 0.4)
                    combined = base_relevance * importance_weight
                    results.append((combined, m))

        results.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in results[:limit]]
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新感知记忆"""
        updated = False
        modality_cache = None
        for memory in self.perceptual_memories:
            if memory.id == memory_id:
                if content is not None:
                    memory.content = content
                if importance is not None:
                    memory.importance = importance
                if metadata is not None:
                    memory.metadata.update(metadata)
                modality_cache = memory.metadata.get("modality", "text")
                updated = True
                break

        # 更新SQLite
        self.doc_store.update_memory(
            memory_id=memory_id,
            content=content,
            importance=importance,
            properties=metadata
        )

        # 如内容或原始数据改变，则重嵌入并upsert到Qdrant
        if content is not None or (metadata and "raw_data" in metadata):
            modality = metadata.get("modality", modality_cache or "text") if metadata else (modality_cache or "text")
            raw = metadata.get("raw_data", content) if metadata else content
            try:
                perception = self._encode_perception(raw or "", modality, memory_id)
                payload = self.doc_store.get_memory(memory_id) or {}
                self.vector_store.add_vectors(
                    vectors=[perception.encoding],
                    metadata=[{
                        "memory_id": memory_id,
                        "user_id": payload.get("user_id", ""),
                        "memory_type": "perceptual",
                        "modality": modality,
                        "importance": (payload.get("importance") or importance) or 0.5,
                        "content": content or (payload.get("content", "")),
                    }],
                    ids=[memory_id]
                )
            except Exception:
                pass

        return updated
    
    def remove(self, memory_id: str) -> bool:
        """删除感知记忆"""
        removed = False
        for i, memory in enumerate(self.perceptual_memories):
            if memory.id == memory_id:
                removed_memory = self.perceptual_memories.pop(i)
                perception_id = removed_memory.metadata.get("perception_id")
                if perception_id and perception_id in self.perceptions:
                    perception = self.perceptions.pop(perception_id)
                    modality = perception.modality
                    if modality in self.modality_index:
                        if perception_id in self.modality_index[modality]:
                            self.modality_index[modality].remove(perception_id)
                        if not self.modality_index[modality]:
                            del self.modality_index[modality]
                removed = True
                break

        # 权威库删除
        self.doc_store.delete_memory(memory_id)
        # 向量库删除（所有模态集合尝试删除）
        for store in self.vector_stores.values():
            try:
                store.delete_memories([memory_id])
            except Exception:
                pass

        return removed
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(memory.id == memory_id for memory in self.perceptual_memories)
    
    def forget(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 30) -> int:
        """感知记忆遗忘机制（硬删除）"""
        forgotten_count = 0
        current_time = datetime.now()
        
        to_remove = []  # 收集要删除的记忆ID
        
        for memory in self.perceptual_memories:
            should_forget = False
            
            if strategy == "importance_based":
                # 基于重要性遗忘
                if memory.importance < threshold:
                    should_forget = True
            elif strategy == "time_based":
                # 基于时间遗忘
                cutoff_time = current_time - timedelta(days=max_age_days)
                if memory.timestamp < cutoff_time:
                    should_forget = True
            elif strategy == "capacity_based":
                # 基于容量遗忘（保留最重要的）
                if len(self.perceptual_memories) > self.config.max_capacity:
                    sorted_memories = sorted(self.perceptual_memories, key=lambda m: m.importance)
                    excess_count = len(self.perceptual_memories) - self.config.max_capacity
                    if memory in sorted_memories[:excess_count]:
                        should_forget = True
            
            if should_forget:
                to_remove.append(memory.id)
        
        # 执行硬删除
        for memory_id in to_remove:
            if self.remove(memory_id):
                forgotten_count += 1
                logger.info(f"感知记忆硬删除: {memory_id[:8]}... (策略: {strategy})")
        
        return forgotten_count

    def clear(self):
        """清空所有感知记忆"""
        self.perceptual_memories.clear()
        self.perceptions.clear()
        self.modality_index.clear()
        # 删除SQLite中的perceptual记录
        docs = self.doc_store.search_memories(memory_type="perceptual", limit=10000)
        ids = [d["memory_id"] for d in docs]
        for mid in ids:
            self.doc_store.delete_memory(mid)
        # 删除Qdrant向量（所有模态集合）
        for store in self.vector_stores.values():
            try:
                if ids:
                    store.delete_memories(ids)
            except Exception:
                pass

    def get_all(self) -> List[MemoryItem]:
        """获取所有感知记忆"""
        return self.perceptual_memories.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取感知记忆统计信息"""
        # 硬删除模式：所有记忆都是活跃的
        active_memories = self.perceptual_memories
        
        modality_counts = {modality: len(ids) for modality, ids in self.modality_index.items()}
        vs_stats_all = {}
        for mod, store in self.vector_stores.items():
            try:
                vs_stats_all[mod] = store.get_collection_stats()
            except Exception:
                vs_stats_all[mod] = {"store_type": "qdrant"}
        db_stats = self.doc_store.get_database_stats()
        
        return {
            "count": len(active_memories),  # 活跃记忆数量
            "forgotten_count": 0,  # 硬删除模式下已遗忘的记忆会被直接删除
            "total_count": len(self.perceptual_memories),  # 总记忆数量
            "perceptions_count": len(self.perceptions),
            "modality_counts": modality_counts,
            "supported_modalities": list(self.supported_modalities),
            "avg_importance": sum(m.importance for m in active_memories) / len(active_memories) if active_memories else 0.0,
            "memory_type": "perceptual",
            "vector_stores": vs_stats_all,
            "document_store": {k: v for k, v in db_stats.items() if k.endswith("_count") or k in ["store_type", "db_path"]}
        }
    
    def cross_modal_search(
        self,
        query: Any,
        query_modality: str,
        target_modality: str = None,
        limit: int = 5
    ) -> List[MemoryItem]:
        """跨模态搜索"""
        return self.retrieve(
            query=str(query),
            limit=limit,
            query_modality=query_modality,
            target_modality=target_modality
        )
    
    def get_by_modality(self, modality: str, limit: int = 10) -> List[MemoryItem]:
        """按模态获取记忆"""
        if modality not in self.modality_index:
            return []
        
        perception_ids = self.modality_index[modality]
        results = []
        
        for memory in self.perceptual_memories:
            if memory.metadata.get("perception_id") in perception_ids:
                results.append(memory)
                if len(results) >= limit:
                    break
        
        return results
    
    def generate_content(self, prompt: str, target_modality: str) -> Optional[str]:
        """基于感知记忆生成内容"""
        # 简化的内容生成实现
        # 实际应用中需要使用生成模型
        
        if target_modality not in self.supported_modalities:
            return None
        
        # 检索相关感知记忆
        relevant_memories = self.retrieve(prompt, limit=3)
        
        if not relevant_memories:
            return None
        
        # 简单的内容组合
        if target_modality == "text":
            contents = [memory.content for memory in relevant_memories]
            return f"基于感知记忆生成的内容：\n" + "\n".join(contents)
        
        return f"生成的{target_modality}内容（基于{len(relevant_memories)}个相关记忆）"
    
    def _init_encoders(self) -> Dict[str, Any]:
        """初始化编码器（轻量、确定性，统一输出self.vector_dim维）"""
        encoders = {}
        for modality in self.supported_modalities:
            if modality == "text":
                encoders[modality] = self._text_encoder
            elif modality == "image":
                encoders[modality] = self._image_encoder
            elif modality == "audio":
                encoders[modality] = self._audio_encoder
            else:
                encoders[modality] = self._default_encoder
        return encoders
    
    def _encode_perception(self, data: Any, modality: str, memory_id: str) -> Perception:
        """编码感知数据"""
        encoding = self._encode_data(data, modality)
        
        perception = Perception(
            perception_id=f"perception_{memory_id}",
            data=data,
            modality=modality,
            encoding=encoding,
            metadata={"source": "memory_system"}
        )
        
        return perception
    
    def _encode_data(self, data: Any, modality: str) -> List[float]:
        """编码数据为固定维度向量（按模态维度对齐）"""
        target_dim = self._get_dim_for_modality(modality)
        encoder = self.encoders.get(modality, self._default_encoder)
        vec = encoder(data)
        if not isinstance(vec, list):
            vec = list(vec)
        if len(vec) < target_dim:
            vec = vec + [0.0] * (target_dim - len(vec))
        elif len(vec) > target_dim:
            vec = vec[:target_dim]
        return vec
    
    def _text_encoder(self, text: str) -> List[float]:
        """文本编码器（使用嵌入模型）"""
        emb = self.text_embedder.encode(text or "")
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        return emb
    
    def _image_encoder_hash(self, image_data: Any) -> List[float]:
        """图像编码器（轻量确定性哈希向量，跨环境稳定）"""
        try:
            if isinstance(image_data, (bytes, bytearray)):
                data_bytes = bytes(image_data)
            elif isinstance(image_data, str) and os.path.exists(image_data):
                with open(image_data, 'rb') as f:
                    data_bytes = f.read()
            else:
                data_bytes = str(image_data).encode('utf-8', errors='ignore')
            hex_str = hashlib.sha256(data_bytes).hexdigest()
            return self._hash_to_vector(hex_str, self._get_dim_for_modality("image"))
        except Exception:
            return self._hash_to_vector(str(image_data), self._get_dim_for_modality("image"))

    def _image_encoder(self, image_data: Any) -> List[float]:
        """图像编码器（优先CLIP，不可用则哈希）"""
        if self._clip_model is None or self._clip_processor is None:
            return self._image_encoder_hash(image_data)
        try:
            from PIL import Image
            if isinstance(image_data, str) and os.path.exists(image_data):
                image = Image.open(image_data).convert('RGB')
            elif isinstance(image_data, (bytes, bytearray)):
                from io import BytesIO
                image = Image.open(BytesIO(bytes(image_data))).convert('RGB')
            else:
                # 退回到哈希
                return self._image_encoder_hash(image_data)
            inputs = self._clip_processor(images=image, return_tensors="pt")
            with self._no_grad():
                feats = self._clip_model.get_image_features(**inputs)
            vec = feats[0].detach().cpu().numpy().tolist()
            return vec
        except Exception:
            return self._image_encoder_hash(image_data)
    
    def _audio_encoder_hash(self, audio_data: Any) -> List[float]:
        """音频编码器（轻量确定性哈希向量）"""
        try:
            if isinstance(audio_data, (bytes, bytearray)):
                data_bytes = bytes(audio_data)
            elif isinstance(audio_data, str) and os.path.exists(audio_data):
                with open(audio_data, 'rb') as f:
                    data_bytes = f.read()
            else:
                data_bytes = str(audio_data).encode('utf-8', errors='ignore')
            hex_str = hashlib.sha256(data_bytes).hexdigest()
            return self._hash_to_vector(hex_str, self._get_dim_for_modality("audio"))
        except Exception:
            return self._hash_to_vector(str(audio_data), self._get_dim_for_modality("audio"))

    def _audio_encoder(self, audio_data: Any) -> List[float]:
        """音频编码器（优先CLAP，不可用则哈希）"""
        if self._clap_model is None or self._clap_processor is None:
            return self._audio_encoder_hash(audio_data)
        try:
            import numpy as np
            # 加载音频（需要 librosa）
            import librosa
            if isinstance(audio_data, str) and os.path.exists(audio_data):
                speech, sr = librosa.load(audio_data, sr=48000, mono=True)
            elif isinstance(audio_data, (bytes, bytearray)):
                # 临时文件方式加载
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(bytes(audio_data))
                    tmp_path = tmp.name
                speech, sr = librosa.load(tmp_path, sr=48000, mono=True)
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            else:
                return self._audio_encoder_hash(audio_data)
            inputs = self._clap_processor(audios=speech, sampling_rate=48000, return_tensors="pt")
            with self._no_grad():
                feats = self._clap_model.get_audio_features(**inputs)
            vec = feats[0].detach().cpu().numpy().tolist()
            return vec
        except Exception:
            return self._audio_encoder_hash(audio_data)

    def _default_encoder(self, data: Any) -> List[float]:
        """默认编码器（退化为文本嵌入或哈希）"""
        try:
            return self._text_encoder(str(data))
        except Exception:
            return self._hash_to_vector(str(data), self.vector_dim)
    
    def _calculate_similarity(self, encoding1: List[float], encoding2: List[float]) -> float:
        """计算编码相似度"""
        if not encoding1 or not encoding2:
            return 0.0
        
        # 确保长度一致
        min_len = min(len(encoding1), len(encoding2))
        if min_len == 0:
            return 0.0
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(encoding1[:min_len], encoding2[:min_len]))
        norm1 = sum(a * a for a in encoding1[:min_len]) ** 0.5
        norm2 = sum(a * a for a in encoding2[:min_len]) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def _hash_to_vector(self, data_str: str, dim: int) -> List[float]:
        """将字符串哈希为固定维度的[0,1]向量（确定性）"""
        seed = int(hashlib.sha256(data_str.encode("utf-8", errors="ignore")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return [rng.random() for _ in range(dim)]

    class _no_grad:
        def __enter__(self):
            try:
                import torch
                self.prev = torch.is_grad_enabled()
                torch.set_grad_enabled(False)
            except Exception:
                self.prev = None
            return self
        def __exit__(self, exc_type, exc, tb):
            try:
                import torch
                if self.prev is not None:
                    torch.set_grad_enabled(self.prev)
            except Exception:
                pass

    def _get_vector_store_for_modality(self, modality: Optional[str]) -> QdrantVectorStore:
        mod = (modality or "text").lower()
        return self.vector_stores.get(mod, self.vector_stores["text"])

    def _get_dim_for_modality(self, modality: Optional[str]) -> int:
        mod = (modality or "text").lower()
        if mod == "image":
            return int(self._image_dim or self.vector_dim)
        if mod == "audio":
            return int(self._audio_dim or self.vector_dim)
        return int(self.vector_dim)
