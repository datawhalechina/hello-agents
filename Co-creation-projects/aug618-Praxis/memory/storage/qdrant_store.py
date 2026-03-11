"""
Qdrant向量数据库存储实现
使用专业的Qdrant向量数据库替代ChromaDB
"""

import logging
import os
import uuid
import threading
from typing import Dict, List, Optional, Any, Union
import numpy as np
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, MatchValue, SearchRequest
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None
    models = None

logger = logging.getLogger(__name__)

class QdrantConnectionManager:
    """Qdrant连接管理器 - 防止重复连接和初始化"""
    _instances = {}  # key: (url, collection_name) -> QdrantVectorStore instance
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(
        cls, 
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "hello_agents_vectors",
        vector_size: int = 384,
        distance: str = "cosine",
        timeout: int = 30,
        **kwargs
    ) -> 'QdrantVectorStore':
        """获取或创建Qdrant实例（单例模式）"""
        # 创建唯一键
        key = (url or "local", collection_name)
        
        if key not in cls._instances:
            with cls._lock:
                # 双重检查锁定
                if key not in cls._instances:
                    logger.debug(f"🔄 创建新的Qdrant连接: {collection_name}")
                    cls._instances[key] = QdrantVectorStore(
                        url=url,
                        api_key=api_key,
                        collection_name=collection_name,
                        vector_size=vector_size,
                        distance=distance,
                        timeout=timeout,
                        **kwargs
                    )
                else:
                    logger.debug(f"♻️ 复用现有Qdrant连接: {collection_name}")
        else:
            logger.debug(f"♻️ 复用现有Qdrant连接: {collection_name}")
            
        return cls._instances[key]

class QdrantVectorStore:
    """Qdrant向量数据库存储实现"""
    
    def __init__(
        self, 
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "hello_agents_vectors",
        vector_size: int = 384,
        distance: str = "cosine",
        timeout: int = 30,
        **kwargs
    ):
        """
        初始化Qdrant向量存储 (支持云API)
        
        Args:
            url: Qdrant云服务URL (如果为None则使用本地)
            api_key: Qdrant云服务API密钥
            collection_name: 集合名称
            vector_size: 向量维度
            distance: 距离度量方式 (cosine, dot, euclidean)
            timeout: 连接超时时间
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client未安装。请运行: pip install qdrant-client>=1.6.0"
            )
        
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.timeout = timeout
        # HNSW/Query params via env
        try:
            self.hnsw_m = int(os.getenv("QDRANT_HNSW_M", "32"))
        except Exception:
            self.hnsw_m = 32
        try:
            self.hnsw_ef_construct = int(os.getenv("QDRANT_HNSW_EF_CONSTRUCT", "256"))
        except Exception:
            self.hnsw_ef_construct = 256
        try:
            self.search_ef = int(os.getenv("QDRANT_SEARCH_EF", "128"))
        except Exception:
            self.search_ef = 128
        self.search_exact = os.getenv("QDRANT_SEARCH_EXACT", "0") == "1"
        
        # 距离度量映射
        distance_map = {
            "cosine": Distance.COSINE,
            "dot": Distance.DOT,
            "euclidean": Distance.EUCLID,
        }
        self.distance = distance_map.get(distance.lower(), Distance.COSINE)
        
        # 初始化客户端
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """初始化Qdrant客户端和集合"""
        try:
            # 根据配置创建客户端连接
            if self.url and self.api_key:
                # 使用云服务API
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=self.timeout
                )
                logger.info(f"✅ 成功连接到Qdrant云服务: {self.url}")
            elif self.url:
                # 使用自定义URL（无API密钥）
                self.client = QdrantClient(
                    url=self.url,
                    timeout=self.timeout
                )
                logger.info(f"✅ 成功连接到Qdrant服务: {self.url}")
            else:
                # 使用本地服务（默认）
                self.client = QdrantClient(
                    host="localhost",
                    port=6333,
                    timeout=self.timeout
                )
                logger.info("✅ 成功连接到本地Qdrant服务: localhost:6333")
            
            # 检查连接
            collections = self.client.get_collections()
            
            # 创建或获取集合
            self._ensure_collection()
            
        except Exception as e:
            logger.error(f"❌ Qdrant连接失败: {e}")
            if not self.url:
                logger.info("💡 本地连接失败，可以考虑使用Qdrant云服务")
                logger.info("💡 或启动本地服务: docker run -p 6333:6333 qdrant/qdrant")
            else:
                logger.info("💡 请检查URL和API密钥是否正确")
            raise
    
    def _ensure_collection(self):
        """确保集合存在，不存在则创建"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # 创建新集合
                hnsw_cfg = None
                try:
                    hnsw_cfg = models.HnswConfigDiff(m=self.hnsw_m, ef_construct=self.hnsw_ef_construct)
                except Exception:
                    hnsw_cfg = None
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance
                    ),
                    hnsw_config=hnsw_cfg
                )
                logger.info(f"✅ 创建Qdrant集合: {self.collection_name}")
            else:
                logger.info(f"✅ 使用现有Qdrant集合: {self.collection_name}")
                # 尝试更新 HNSW 配置
                try:
                    self.client.update_collection(
                        collection_name=self.collection_name,
                        hnsw_config=models.HnswConfigDiff(m=self.hnsw_m, ef_construct=self.hnsw_ef_construct)
                    )
                except Exception as ie:
                    logger.debug(f"跳过更新HNSW配置: {ie}")
            # 确保必要的payload索引
            self._ensure_payload_indexes()
                
        except Exception as e:
            logger.error(f"❌ 集合初始化失败: {e}")
            raise

    def _ensure_payload_indexes(self):
        """为常用过滤字段创建payload索引"""
        try:
            index_fields = [
                ("memory_type", models.PayloadSchemaType.KEYWORD),
                ("user_id", models.PayloadSchemaType.KEYWORD),
                ("memory_id", models.PayloadSchemaType.KEYWORD),
                ("timestamp", models.PayloadSchemaType.INTEGER),
                ("modality", models.PayloadSchemaType.KEYWORD),  # 感知记忆模态筛选
                ("source", models.PayloadSchemaType.KEYWORD),
                ("external", models.PayloadSchemaType.BOOL),
                ("namespace", models.PayloadSchemaType.KEYWORD),
                # RAG相关字段索引
                ("is_rag_data", models.PayloadSchemaType.BOOL),
                ("rag_namespace", models.PayloadSchemaType.KEYWORD),
                ("data_source", models.PayloadSchemaType.KEYWORD),
            ]
            for field_name, schema_type in index_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=schema_type,
                    )
                except Exception as ie:
                    # 索引已存在会报错，忽略
                    logger.debug(f"索引 {field_name} 已存在或创建失败: {ie}")
        except Exception as e:
            logger.debug(f"创建payload索引时出错: {e}")
    
    def add_vectors(
        self, 
        vectors: List[List[float]], 
        metadata: List[Dict[str, Any]], 
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        添加向量到Qdrant
        
        Args:
            vectors: 向量列表
            metadata: 元数据列表
            ids: 可选的ID列表
        
        Returns:
            bool: 是否成功
        """
        try:
            if not vectors:
                logger.warning("⚠️ 向量列表为空")
                return False
                
            # 生成ID（如果未提供）
            if ids is None:
                ids = [f"vec_{i}_{int(datetime.now().timestamp() * 1000000)}" 
                       for i in range(len(vectors))]
            
            # 构建点数据
            logger.info(f"[Qdrant] add_vectors start: n_vectors={len(vectors)} n_meta={len(metadata)} collection={self.collection_name}")
            points = []
            for i, (vector, meta, point_id) in enumerate(zip(vectors, metadata, ids)):
                # 确保向量是正确的维度
                try:
                    vlen = len(vector)
                except Exception:
                    logger.error(f"[Qdrant] 非法向量类型: index={i} type={type(vector)} value={vector}")
                    continue
                if vlen != self.vector_size:
                    logger.warning(f"⚠️ 向量维度不匹配: 期望{self.vector_size}, 实际{len(vector)}")
                    continue
                    
                # 添加时间戳到元数据
                meta_with_timestamp = meta.copy()
                meta_with_timestamp["timestamp"] = int(datetime.now().timestamp())
                meta_with_timestamp["added_at"] = int(datetime.now().timestamp())
                if "external" in meta_with_timestamp and not isinstance(meta_with_timestamp.get("external"), bool):
                    # normalize to bool
                    val = meta_with_timestamp.get("external")
                    meta_with_timestamp["external"] = True if str(val).lower() in ("1", "true", "yes") else False
                # 确保点ID是Qdrant接受的类型（无符号整数或UUID字符串）
                safe_id: Any
                if isinstance(point_id, int):
                    safe_id = point_id
                elif isinstance(point_id, str):
                    try:
                        uuid.UUID(point_id)
                        safe_id = point_id
                    except Exception:
                        safe_id = str(uuid.uuid4())
                else:
                    safe_id = str(uuid.uuid4())

                point = PointStruct(
                    id=safe_id,
                    vector=vector,
                    payload=meta_with_timestamp
                )
                points.append(point)
            
            if not points:
                logger.warning("⚠️ 没有有效的向量点")
                return False
            
            # 批量插入
            logger.info(f"[Qdrant] upsert begin: points={len(points)}")
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            logger.info("[Qdrant] upsert done")
            
            logger.info(f"✅ 成功添加 {len(points)} 个向量到Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加向量失败: {e}")
            return False
    
    def search_similar(
        self, 
        query_vector: List[float], 
        limit: int = 10, 
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量
        
        Args:
            query_vector: 查询向量
            limit: 返回结果数量限制
            score_threshold: 相似度阈值
            where: 过滤条件
        
        Returns:
            List[Dict]: 搜索结果
        """
        try:
            if len(query_vector) != self.vector_size:
                logger.error(f"❌ 查询向量维度错误: 期望{self.vector_size}, 实际{len(query_vector)}")
                return []
            
            # 构建过滤器
            query_filter = None
            if where:
                conditions = []
                for key, value in where.items():
                    if isinstance(value, (str, int, float, bool)):
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # 执行搜索
            # 搜索参数
            search_params = None
            try:
                search_params = models.SearchParams(hnsw_ef=self.search_ef, exact=self.search_exact)
            except Exception:
                search_params = None
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
                search_params=search_params
            )
            search_result = response.points
            
            # 转换结果格式
            results = []
            for hit in search_result:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": hit.payload or {}
                }
                results.append(result)
            
            logger.debug(f"🔍 Qdrant搜索返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ 向量搜索失败: {e}")
            return []
    
    def delete_vectors(self, ids: List[str]) -> bool:
        """
        删除向量
        
        Args:
            ids: 要删除的向量ID列表
        
        Returns:
            bool: 是否成功
        """
        try:
            if not ids:
                return True
                
            operation_info = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=ids
                ),
                wait=True
            )
            
            logger.info(f"✅ 成功删除 {len(ids)} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除向量失败: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """
        清空集合
        
        Returns:
            bool: 是否成功
        """
        try:
            # 删除并重新创建集合
            self.client.delete_collection(collection_name=self.collection_name)
            self._ensure_collection()
            
            logger.info(f"✅ 成功清空Qdrant集合: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 清空集合失败: {e}")
            return False
    
    def delete_memories(self, memory_ids: List[str]):
        """
        删除指定记忆（通过payload中的 memory_id 过滤删除）
        
        注意：由于写入时可能将非UUID的点ID转换为UUID，这里不再依赖点ID，
        而是通过payload中的memory_id来匹配删除，确保一致性。
        """
        try:
            if not memory_ids:
                return
            # 构建 should 过滤条件：memory_id 等于任一给定值
            conditions = [
                FieldCondition(key="memory_id", match=MatchValue(value=mid))
                for mid in memory_ids
            ]
            query_filter = Filter(should=conditions)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=query_filter),
                wait=True,
            )
            logger.info(f"✅ 成功按memory_id删除 {len(memory_ids)} 个Qdrant向量")
        except Exception as e:
            logger.error(f"❌ 删除记忆失败: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        
        Returns:
            Dict: 集合信息
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            info = {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "vector_size": self.vector_size,
                    "distance": self.distance.value,
                }
            }
            
            return info
            
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {e}")
            return {}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息（兼容抽象接口）
        """
        info = self.get_collection_info()
        if not info:
            return {"store_type": "qdrant", "name": self.collection_name}
        info["store_type"] = "qdrant"
        return info
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 服务是否健康
        """
        try:
            # 尝试获取集合列表
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant健康检查失败: {e}")
            return False
    
    def __del__(self):
        """析构函数，清理资源"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.close()
            except:
                pass
