"""语义记忆实现

结合向量检索和知识图谱的混合语义记忆，使用：
- HuggingFace 中文预训练模型进行文本嵌入
- 向量相似度检索进行快速初筛
- 知识图谱进行实体关系推理
- 混合检索策略优化结果质量
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
import logging
import math
import numpy as np

from ..base import BaseMemory, MemoryItem, MemoryConfig
from ..embedding import get_text_embedder, get_dimension
from core.database_config import get_database_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Entity:
    """实体类"""
    
    def __init__(
        self,
        entity_id: str,
        name: str,
        entity_type: str = "MISC",
        description: str = "",
        properties: Dict[str, Any] = None
    ):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type  # PERSON, ORG, PRODUCT, SKILL, CONCEPT等
        self.description = description
        self.properties = properties or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.frequency = 1  # 出现频率
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "properties": self.properties,
            "frequency": self.frequency
        }

class Relation:
    """关系类"""
    
    def __init__(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        strength: float = 1.0,
        evidence: str = "",
        properties: Dict[str, Any] = None
    ):
        self.from_entity = from_entity
        self.to_entity = to_entity
        self.relation_type = relation_type
        self.strength = strength
        self.evidence = evidence  # 支持该关系的原文本
        self.properties = properties or {}
        self.created_at = datetime.now()
        self.frequency = 1  # 关系出现频率
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "evidence": self.evidence,
            "properties": self.properties,
            "frequency": self.frequency
        }


class SemanticMemory(BaseMemory):
    """增强语义记忆实现
    
    特点：
    - 使用HuggingFace中文预训练模型进行文本嵌入
    - 向量检索进行快速相似度匹配
    - 知识图谱存储实体和关系
    - 混合检索策略：向量+图+语义推理
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 嵌入模型（统一提供）
        self.embedding_model = None
        self._init_embedding_model()
        
        # 专业数据库存储
        self.vector_store = None
        self.graph_store = None
        self._init_databases()
        
        # 实体和关系缓存 (用于快速访问)
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        
        # 实体识别器
        self.nlp = None
        self._init_nlp()
        
        # 记忆存储
        self.semantic_memories: List[MemoryItem] = []
        self.memory_embeddings: Dict[str, np.ndarray] = {}
        
        logger.info("增强语义记忆初始化完成（使用Qdrant+Neo4j专业数据库）")
    
    def _init_embedding_model(self):
        """初始化统一嵌入模型（由 embedding_provider 管理）。"""
        try:
            self.embedding_model = get_text_embedder()
            # 轻量健康检查与日志
            try:
                test_vec = self.embedding_model.encode("health_check")
                dim = getattr(self.embedding_model, "dimension", len(test_vec))
                logger.info(f"✅ 嵌入模型就绪，维度: {dim}")
            except Exception:
                logger.info("✅ 嵌入模型就绪")
        except Exception as e:
            logger.error(f"❌ 嵌入模型初始化失败: {e}")
            raise
    
    def _init_databases(self):
        """初始化专业数据库存储"""
        try:
            # 获取数据库配置
            db_config = get_database_config()
            
            # 初始化Qdrant向量数据库（使用连接管理器避免重复连接）
            from ..storage.qdrant_store import QdrantConnectionManager
            qdrant_config = db_config.get_qdrant_config() or {}
            qdrant_config["vector_size"] = get_dimension()
            self.vector_store = QdrantConnectionManager.get_instance(**qdrant_config)
            logger.info("✅ Qdrant向量数据库初始化完成")
            
            # 初始化Neo4j图数据库
            from ..storage.neo4j_store import Neo4jGraphStore
            neo4j_config = db_config.get_neo4j_config()
            self.graph_store = Neo4jGraphStore(**neo4j_config)
            logger.info("✅ Neo4j图数据库初始化完成")
            
            # 验证连接
            vector_health = self.vector_store.health_check()
            graph_health = self.graph_store.health_check()
            
            if not vector_health:
                logger.warning("⚠️ Qdrant连接异常，部分功能可能受限")
            if not graph_health:
                logger.warning("⚠️ Neo4j连接异常，图搜索功能可能受限")
            
            logger.info(f"🏥 数据库健康状态: Qdrant={'✅' if vector_health else '❌'}, Neo4j={'✅' if graph_health else '❌'}")
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            logger.info("💡 请检查数据库配置和网络连接")
            logger.info("💡 参考 DATABASE_SETUP_GUIDE.md 进行配置")
            raise
    
    def _init_nlp(self):
        """初始化NLP处理器 - 智能多语言支持"""
        try:
            import spacy
            self.nlp_models = {}
            
            # 尝试加载多语言模型
            models_to_try = [
                ("zh_core_web_sm", "中文"),
                ("en_core_web_sm", "英文")
            ]
            
            loaded_models = []
            for model_name, lang_name in models_to_try:
                try:
                    nlp = spacy.load(model_name)
                    self.nlp_models[model_name] = nlp
                    loaded_models.append(lang_name)
                    logger.info(f"✅ 加载{lang_name}spaCy模型: {model_name}")
                except OSError:
                    logger.warning(f"⚠️ {lang_name}spaCy模型不可用: {model_name}")
            
            # 设置主要NLP处理器
            if "zh_core_web_sm" in self.nlp_models:
                self.nlp = self.nlp_models["zh_core_web_sm"]
                logger.info("🎯 主要使用中文spaCy模型")
            elif "en_core_web_sm" in self.nlp_models:
                self.nlp = self.nlp_models["en_core_web_sm"]
                logger.info("🎯 主要使用英文spaCy模型")
            else:
                self.nlp = None
                logger.warning("⚠️ 无可用spaCy模型，实体提取将受限")
            
            if loaded_models:
                logger.info(f"📚 可用语言模型: {', '.join(loaded_models)}")
                
        except ImportError:
            logger.warning("⚠️ spaCy不可用，实体提取将受限")
            self.nlp = None
            self.nlp_models = {}
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加语义记忆"""
        try:
            # 1. 生成文本嵌入
            embedding = self.embedding_model.encode(memory_item.content)
            self.memory_embeddings[memory_item.id] = embedding
            
            # 2. 提取实体和关系
            entities = self._extract_entities(memory_item.content)
            relations = self._extract_relations(memory_item.content, entities)
            
            # 3. 存储到Neo4j图数据库
            for entity in entities:
                self._add_entity_to_graph(entity, memory_item)
            
            for relation in relations:
                self._add_relation_to_graph(relation, memory_item)
            
            # 4. 存储到Qdrant向量数据库
            metadata = {
                "memory_id": memory_item.id,
                "user_id": memory_item.user_id,
                "content": memory_item.content,
                "memory_type": memory_item.memory_type,
                "timestamp": int(memory_item.timestamp.timestamp()),
                "importance": memory_item.importance,
                "entities": [e.entity_id for e in entities],
                "entity_count": len(entities),
                "relation_count": len(relations)
            }
            
            success = self.vector_store.add_vectors(
                vectors=[embedding.tolist()],
                metadata=[metadata],
                ids=[memory_item.id]
            )
            
            if not success:
                logger.warning("⚠️ 向量存储失败，但记忆已添加到图数据库")
            
            # 5. 添加实体信息到元数据
            memory_item.metadata["entities"] = [e.entity_id for e in entities]
            memory_item.metadata["relations"] = [
                f"{r.from_entity}-{r.relation_type}-{r.to_entity}" for r in relations
            ]
            
            # 6. 存储记忆
            self.semantic_memories.append(memory_item)
            
            logger.info(f"✅ 添加语义记忆: {len(entities)}个实体, {len(relations)}个关系")
            return memory_item.id
        
        except Exception as e:
            logger.error(f"❌ 添加语义记忆失败: {e}")
            raise
    
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索语义记忆"""
        try:
            user_id = kwargs.get("user_id")

            # 1. 向量检索
            vector_results = self._vector_search(query, limit * 2, user_id)
            
            # 2. 图检索
            graph_results = self._graph_search(query, limit * 2, user_id)
            
            # 3. 混合排序
            combined_results = self._combine_and_rank_results(
                vector_results, graph_results, query, limit
            )

            # 3.1 计算概率（对 combined_score 做 softmax 归一化）
            scores = [r.get("combined_score", r.get("vector_score", 0.0)) for r in combined_results]
            if scores:
                import math
                max_s = max(scores)
                exps = [math.exp(s - max_s) for s in scores]
                denom = sum(exps) or 1.0
                probs = [e / denom for e in exps]
            else:
                probs = []
            
            # 4. 过滤已遗忘记忆并转换为MemoryItem
            result_memories = []
            for idx, result in enumerate(combined_results):
                memory_id = result.get("memory_id")
                
                # 检查是否已遗忘
                memory = next((m for m in self.semantic_memories if m.id == memory_id), None)
                if memory and memory.metadata.get("forgotten", False):
                    continue  # 跳过已遗忘的记忆
                
                # 处理时间戳
                timestamp = result.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        timestamp = datetime.now()
                elif isinstance(timestamp, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp)
                else:
                    timestamp = datetime.now()
                
                # 直接从结果数据构建MemoryItem（附带分数与概率）
                memory_item = MemoryItem(
                    id=result["memory_id"],
                    content=result["content"],
                    memory_type="semantic",
                    user_id=result.get("user_id", "default"),
                    timestamp=timestamp,
                    importance=result.get("importance", 0.5),
                    metadata={
                        **result.get("metadata", {}),
                        "combined_score": result.get("combined_score", 0.0),
                        "vector_score": result.get("vector_score", 0.0),
                        "graph_score": result.get("graph_score", 0.0),
                        "probability": probs[idx] if idx < len(probs) else 0.0,
                    }
                )
                result_memories.append(memory_item)
            
            logger.info(f"✅ 检索到 {len(result_memories)} 条相关记忆")
            return result_memories[:limit]
                
        except Exception as e:
            logger.error(f"❌ 检索语义记忆失败: {e}")
            return []
    
    def _vector_search(self, query: str, limit: int, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Qdrant向量搜索"""
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(query)
            
            # 构建过滤条件
            where_filter = {"memory_type": "semantic"}
            if user_id:
                where_filter["user_id"] = user_id

            # Qdrant向量检索
            results = self.vector_store.search_similar(
                query_vector=query_embedding.tolist(),
                limit=limit,
                where=where_filter if where_filter else None
            )

            # 转换结果格式以保持兼容性
            formatted_results = []
            for result in results:
                formatted_result = {
                    "id": result["id"],
                    "score": result["score"],
                    **result["metadata"]  # 包含所有元数据
                }
                formatted_results.append(formatted_result)

            logger.debug(f"🔍 Qdrant向量搜索返回 {len(formatted_results)} 个结果")
            return formatted_results
                
        except Exception as e:
            logger.error(f"❌ Qdrant向量搜索失败: {e}")
            return []

    def _graph_search(self, query: str, limit: int, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Neo4j图搜索"""
        try:
            # 从查询中提取实体
            query_entities = self._extract_entities(query)
            
            if not query_entities:
                # 如果没有提取到实体，尝试按名称搜索
                entities_by_name = self.graph_store.search_entities_by_name(
                    name_pattern=query, 
                    limit=10
                )
                if entities_by_name:
                    query_entities = [Entity(
                        entity_id=e["id"],
                        name=e["name"],
                        entity_type=e["type"]
                    ) for e in entities_by_name[:3]]
                else:
                    return []
            
            # 在Neo4j图中查找相关实体和记忆
            related_memory_ids = set()
            
            for entity in query_entities:
                try:
                    # 查找相关实体
                    related_entities = self.graph_store.find_related_entities(
                        entity_id=entity.entity_id,
                        max_depth=2,
                        limit=20
                    )
                    
                    # 收集相关记忆ID
                    for rel_entity in related_entities:
                        if "memory_id" in rel_entity:
                            related_memory_ids.add(rel_entity["memory_id"])
                    
                    # 也添加直接匹配的实体记忆
                    entity_rels = self.graph_store.get_entity_relationships(entity.entity_id)
                    for rel in entity_rels:
                        rel_data = rel.get("relationship", {})
                        if "memory_id" in rel_data:
                            related_memory_ids.add(rel_data["memory_id"])
                            
                except Exception as e:
                    logger.debug(f"图搜索实体 {entity.entity_id} 失败: {e}")
                    continue
            
            # 构建结果 - 从向量数据库获取完整记忆信息
            results = []
            for memory_id in list(related_memory_ids)[:limit * 2]:  # 获取更多候选
                try:
                    # 优先从本地缓存获取记忆详情，避免占位向量维度不一致问题
                    mem = self._find_memory_by_id(memory_id)
                    if not mem:
                        continue

                    if user_id and mem.user_id != user_id:
                        continue

                    metadata = {
                        "content": mem.content,
                        "user_id": mem.user_id,
                        "memory_type": mem.memory_type,
                        "importance": mem.importance,
                        "timestamp": int(mem.timestamp.timestamp()),
                        "entities": mem.metadata.get("entities", [])
                    }

                    # 计算图相关性分数
                    graph_score = self._calculate_graph_relevance_neo4j(metadata, query_entities)

                    results.append({
                        "id": memory_id,
                        "memory_id": memory_id,
                        "content": metadata.get("content", ""),
                        "similarity": graph_score,
                        "user_id": metadata.get("user_id"),
                        "memory_type": metadata.get("memory_type"),
                        "importance": metadata.get("importance", 0.5),
                        "timestamp": metadata.get("timestamp"),
                        "entities": metadata.get("entities", [])
                    })

                except Exception as e:
                    logger.debug(f"获取记忆 {memory_id} 详情失败: {e}")
                    continue
            
            # 按图相关性排序
            results.sort(key=lambda x: x["similarity"], reverse=True)
            logger.debug(f"🕸️ Neo4j图搜索返回 {len(results)} 个结果")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Neo4j图搜索失败: {e}")
            return []

    def _combine_and_rank_results(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """混合排序结果 - 仅基于向量与图分数的简单融合"""
        # 合并结果，按内容去重
        combined = {}
        content_seen = set()  # 用于内容去重
        
        # 添加向量结果
        for result in vector_results:
            memory_id = result["memory_id"]
            content = result.get("content", "")
            
            # 内容去重：检查是否已经有相同或高度相似的内容
            content_hash = hash(content.strip())
            if content_hash in content_seen:
                logger.debug(f"⚠️ 跳过重复内容: {content[:30]}...")
                continue
            
            content_seen.add(content_hash)
            combined[memory_id] = {
                **result,
                "vector_score": result.get("score", 0.0), 
                "graph_score": 0.0,
                "content_hash": content_hash
            }
        
        # 添加图结果
        for result in graph_results:
            memory_id = result["memory_id"]
            content = result.get("content", "")
            content_hash = hash(content.strip())
            
            if memory_id in combined:
                combined[memory_id]["graph_score"] = result.get("similarity", 0.0)
            elif content_hash not in content_seen:
                content_seen.add(content_hash)
                combined[memory_id] = {
                    **result,
                    "vector_score": 0.0,
                    "graph_score": result.get("similarity", 0.0),
                    "content_hash": content_hash
                }
        
        # 计算混合分数：相似度为主，重要性为辅助排序因子
        for memory_id, result in combined.items():
            vector_score = result["vector_score"]
            graph_score = result["graph_score"]
            importance = result.get("importance", 0.5)
            
            # 新评分算法：向量检索纯基于相似度，重要性作为加权因子
            # 基础相似度得分（不受重要性影响）
            base_relevance = vector_score * 0.7 + graph_score * 0.3
            
            # 重要性作为乘法加权因子，范围 [0.8, 1.2]
            # importance in [0,1] -> weight in [0.8,1.2]
            importance_weight = 0.8 + (importance * 0.4)
            
            # 最终得分：相似度 * 重要性权重
            combined_score = base_relevance * importance_weight
            
            # 调试信息：查看分数分解
            result["debug_info"] = {
                "base_relevance": base_relevance,
                "importance_weight": importance_weight,
                "combined_score": combined_score
            }

            result["combined_score"] = combined_score
        
        # 应用最小相关性阈值
        min_threshold = 0.1  # 最小相关性阈值
        filtered_results = [
            result for result in combined.values() 
            if result["combined_score"] >= min_threshold
        ]

        # 排序并返回
        sorted_results = sorted(
            filtered_results,
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        # 调试信息
        logger.debug(f"🔍 向量结果: {len(vector_results)}, 图结果: {len(graph_results)}")
        logger.debug(f"📝 去重后: {len(combined)}, 过滤后: {len(filtered_results)}")
        
        if logger.level <= logging.DEBUG:
            for i, result in enumerate(sorted_results[:3]):
                logger.debug(f"  结果{i+1}: 向量={result['vector_score']:.3f}, 图={result['graph_score']:.3f}, 精确={result.get('exact_match_bonus', 0):.3f}, 关键词={result.get('keyword_bonus', 0):.3f}, 公司={result.get('company_bonus', 0):.3f}, 实体={result.get('entity_type_bonus', 0):.3f}, 综合={result['combined_score']:.3f}")
        
        return sorted_results[:limit]
    
    def _detect_language(self, text: str) -> str:
        """简单的语言检测"""
        # 统计中文字符比例（无正则，逐字符判断范围）
        chinese_chars = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return "en"
        
        chinese_ratio = chinese_chars / total_chars
        return "zh" if chinese_ratio > 0.3 else "en"
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """智能多语言实体提取"""
        entities = []
        
        # 检测文本语言
        lang = self._detect_language(text)
        
        # 选择合适的spaCy模型
        selected_nlp = None
        if lang == "zh" and "zh_core_web_sm" in self.nlp_models:
            selected_nlp = self.nlp_models["zh_core_web_sm"]
        elif lang == "en" and "en_core_web_sm" in self.nlp_models:
            selected_nlp = self.nlp_models["en_core_web_sm"]
        else:
            # 使用默认模型
            selected_nlp = self.nlp
        
        logger.debug(f"🌐 检测语言: {lang}, 使用模型: {selected_nlp.meta['name'] if selected_nlp else 'None'}")
        
        # 使用spaCy进行实体识别和词法分析
        if selected_nlp:
            try:
                doc = selected_nlp(text)
                logger.debug(f"📝 spaCy处理文本: '{text}' -> {len(doc.ents)} 个实体")
                
                # 存储词法分析结果，供Neo4j使用
                self._store_linguistic_analysis(doc, text)
                
                if not doc.ents:
                    # 如果没有实体，记录详细的词元信息
                    logger.debug("🔍 未找到实体，词元分析:")
                    for token in doc[:5]:  # 只显示前5个词元
                        logger.debug(f"   '{token.text}' -> POS: {token.pos_}, TAG: {token.tag_}, ENT_IOB: {token.ent_iob_}")
                
                for ent in doc.ents:
                    entity = Entity(
                        entity_id=f"entity_{hash(ent.text)}",
                        name=ent.text,
                        entity_type=ent.label_,
                        description=f"从文本中识别的{ent.label_}实体"
                    )
                    entities.append(entity)
                    # 安全获取置信度信息
                    confidence = "N/A"
                    try:
                        if hasattr(ent._, 'confidence'):
                            confidence = getattr(ent._, 'confidence', 'N/A')
                    except Exception:
                        confidence = "N/A"
                    
                    logger.debug(f"🏷️ spaCy识别实体: '{ent.text}' -> {ent.label_} (置信度: {confidence})")
                
            except Exception as e:
                logger.warning(f"⚠️ spaCy实体识别失败: {e}")
                import traceback
                logger.debug(f"详细错误: {traceback.format_exc()}")
        else:
            logger.warning("⚠️ 没有可用的spaCy模型进行实体识别")
        
        return entities
    
    def _store_linguistic_analysis(self, doc, text: str):
        """存储spaCy词法分析结果到Neo4j"""
        if not self.graph_store:
            return
            
        try:
            # 为每个词元创建节点
            for token in doc:
                # 跳过标点符号和空格
                if token.is_punct or token.is_space:
                    continue
                    
                token_id = f"token_{hash(token.text + token.pos_)}"
                
                # 添加词元节点到Neo4j
                self.graph_store.add_entity(
                    entity_id=token_id,
                    name=token.text,
                    entity_type="TOKEN",
                    properties={
                        "pos": token.pos_,        # 词性（NOUN, VERB等）
                        "tag": token.tag_,        # 细粒度标签
                        "lemma": token.lemma_,    # 词元原形
                        "is_alpha": token.is_alpha,
                        "is_stop": token.is_stop,
                        "source_text": text[:50],  # 来源文本片段
                        "language": self._detect_language(text)
                    }
                )
                
                # 如果是名词，可能是潜在的概念
                if token.pos_ in ["NOUN", "PROPN"]:
                    concept_id = f"concept_{hash(token.text)}"
                    self.graph_store.add_entity(
                        entity_id=concept_id,
                        name=token.text,
                        entity_type="CONCEPT",
                        properties={
                            "category": token.pos_,
                            "frequency": 1,  # 可以后续累计
                            "source_text": text[:50]
                        }
                    )
                    
                    # 建立词元到概念的关系
                    self.graph_store.add_relationship(
                        from_entity_id=token_id,
                        to_entity_id=concept_id,
                        relationship_type="REPRESENTS",
                        properties={"confidence": 1.0}
                    )
            
            # 建立词元之间的依存关系
            for token in doc:
                if token.is_punct or token.is_space or token.head == token:
                    continue
                    
                from_id = f"token_{hash(token.text + token.pos_)}"
                to_id = f"token_{hash(token.head.text + token.head.pos_)}"
                
                # Neo4j不允许关系类型包含冒号，需要清理
                relation_type = token.dep_.upper().replace(":", "_")
                
                self.graph_store.add_relationship(
                    from_entity_id=from_id,
                    to_entity_id=to_id,
                    relationship_type=relation_type,  # 清理后的依存关系类型
                    properties={
                        "dependency": token.dep_,  # 保留原始依存关系
                        "source_text": text[:50]
                    }
                )
            
            logger.debug(f"🔗 已将词法分析结果存储到Neo4j: {len([t for t in doc if not t.is_punct and not t.is_space])} 个词元")
            
        except Exception as e:
            logger.warning(f"⚠️ 存储词法分析失败: {e}")
    
    def _extract_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """提取关系"""
        relations = []
        # 仅保留简单共现关系，不做任何正则/关键词匹配
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                relations.append(Relation(
                    from_entity=entity1.entity_id,
                    to_entity=entity2.entity_id,
                    relation_type="CO_OCCURS",
                    strength=0.5,
                    evidence=text[:100]
                ))
        return relations
    
    def _add_entity_to_graph(self, entity: Entity, memory_item: MemoryItem):
        """添加实体到Neo4j图数据库"""
        try:
            # 准备实体属性
            properties = {
                "name": entity.name,
                "description": entity.description,
                "frequency": entity.frequency,
                "memory_id": memory_item.id,
                "user_id": memory_item.user_id,
                "importance": memory_item.importance,
                **entity.properties
            }
            
            # 添加到Neo4j
            success = self.graph_store.add_entity(
                entity_id=entity.entity_id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=properties
            )
            
            if success:
                # 同时更新本地缓存
                if entity.entity_id in self.entities:
                    self.entities[entity.entity_id].frequency += 1
                    self.entities[entity.entity_id].updated_at = datetime.now()
                else:
                    self.entities[entity.entity_id] = entity
                    
            return success
            
        except Exception as e:
            logger.error(f"❌ 添加实体到图数据库失败: {e}")
            return False
    
    def _add_relation_to_graph(self, relation: Relation, memory_item: MemoryItem):
        """添加关系到Neo4j图数据库"""
        try:
            # 准备关系属性
            properties = {
                "strength": relation.strength,
                "memory_id": memory_item.id,
                "user_id": memory_item.user_id,
                "importance": memory_item.importance,
                "evidence": relation.evidence
            }
            
            # 添加到Neo4j
            success = self.graph_store.add_relationship(
                from_entity_id=relation.from_entity,
                to_entity_id=relation.to_entity,
                relationship_type=relation.relation_type,
                properties=properties
            )
            
            if success:
                # 同时更新本地缓存
                self.relations.append(relation)
                
            return success
            
        except Exception as e:
            logger.error(f"❌ 添加关系到图数据库失败: {e}")
            return False
    
    def _calculate_graph_relevance_neo4j(self, memory_metadata: Dict[str, Any], query_entities: List[Entity]) -> float:
        """计算Neo4j图相关性分数"""
        try:
            memory_entities = memory_metadata.get("entities", [])
            if not memory_entities or not query_entities:
                return 0.0
            
            # 实体匹配度
            query_entity_ids = {e.entity_id for e in query_entities}
            matching_entities = len(set(memory_entities).intersection(query_entity_ids))
            entity_score = matching_entities / len(query_entity_ids) if query_entity_ids else 0
            
            # 实体数量加权
            entity_count = memory_metadata.get("entity_count", 0)
            entity_density = min(entity_count / 10, 1.0)  # 归一化到[0,1]
            
            # 关系数量加权
            relation_count = memory_metadata.get("relation_count", 0)
            relation_density = min(relation_count / 5, 1.0)  # 归一化到[0,1]
            
            # 综合分数
            relevance_score = (
                entity_score * 0.6 +           # 实体匹配权重60%
                entity_density * 0.2 +         # 实体密度权重20%
                relation_density * 0.2         # 关系密度权重20%
            )
            
            return min(relevance_score, 1.0)
            
        except Exception as e:
            logger.debug(f"计算图相关性失败: {e}")
            return 0.0

    def _add_or_update_entity(self, entity: Entity):
        """添加或更新实体"""
        if entity.entity_id in self.entities:
            # 更新现有实体
            existing = self.entities[entity.entity_id]
            existing.frequency += 1
            existing.updated_at = datetime.now()
        else:
            # 添加新实体
            self.entities[entity.entity_id] = entity
    
    def _add_or_update_relation(self, relation: Relation):
        """添加或更新关系"""
        # 检查是否已存在相同关系
        existing_relation = None
        for r in self.relations:
            if (r.from_entity == relation.from_entity and
                r.to_entity == relation.to_entity and
                r.relation_type == relation.relation_type):
                existing_relation = r
                break
        
        if existing_relation:
            # 更新现有关系
            existing_relation.frequency += 1
            existing_relation.strength = min(1.0, existing_relation.strength + 0.1)
        else:
            # 添加新关系
            self.relations.append(relation)
    
    # 旧的图相关性计算方法已被 _calculate_graph_relevance_neo4j 替代
    
    def _find_memory_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """根据ID查找记忆"""
        logger.debug(f"🔍 查找记忆ID: {memory_id}, 当前记忆数: {len(self.semantic_memories)}")
        for memory in self.semantic_memories:
            if memory.id == memory_id:
                logger.debug(f"✅ 找到记忆: {memory.content[:50]}...")
                return memory
        logger.debug(f"❌ 未找到记忆ID: {memory_id}")
        return None
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新语义记忆"""
        memory = self._find_memory_by_id(memory_id)
        if not memory:
            return False
        
        try:
            if content is not None:
                # 重新生成嵌入和提取实体
                embedding = self.embedding_model.encode(content)
                self.memory_embeddings[memory_id] = embedding
                
                # 清理旧的实体关系
                old_entities = memory.metadata.get("entities", [])
                self._cleanup_entities_and_relations(old_entities)
                
                # 提取新的实体和关系
                memory.content = content
                entities = self._extract_entities(content)
                relations = self._extract_relations(content, entities)
                
                # 更新知识图谱
                for entity in entities:
                    self._add_or_update_entity(entity)
                for relation in relations:
                    self._add_or_update_relation(relation)
                
                # 更新元数据
                memory.metadata["entities"] = [e.entity_id for e in entities]
                memory.metadata["relations"] = [
                    f"{r.from_entity}-{r.relation_type}-{r.to_entity}" for r in relations
                ]
                
            if importance is not None:
                memory.importance = importance
            
            if metadata is not None:
                memory.metadata.update(metadata)
                
                return True
            
        except Exception as e:
            logger.error(f"❌ 更新记忆失败: {e}")
        return False
    
    def remove(self, memory_id: str) -> bool:
        """删除语义记忆"""
        memory = self._find_memory_by_id(memory_id)
        if not memory:
            return False
        
        try:
            # 删除向量
            self.vector_store.delete_memories([memory_id])
            
            # 清理实体和关系
            entities = memory.metadata.get("entities", [])
            self._cleanup_entities_and_relations(entities)
            
            # 删除记忆
            self.semantic_memories.remove(memory)
            if memory_id in self.memory_embeddings:
                del self.memory_embeddings[memory_id]
                
                return True
            
        except Exception as e:
            logger.error(f"❌ 删除记忆失败: {e}")
        return False
    
    def _cleanup_entities_and_relations(self, entity_ids: List[str]):
        """清理实体和关系"""
        # 这里可以实现更智能的清理逻辑
        # 例如，如果实体不再被任何记忆引用，则删除它
        pass
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return self._find_memory_by_id(memory_id) is not None
    
    def forget(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 30) -> int:
        """语义记忆遗忘机制（硬删除）"""
        forgotten_count = 0
        current_time = datetime.now()
        
        to_remove = []  # 收集要删除的记忆ID
        
        for memory in self.semantic_memories:
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
                if len(self.semantic_memories) > self.config.max_capacity:
                    sorted_memories = sorted(self.semantic_memories, key=lambda m: m.importance)
                    excess_count = len(self.semantic_memories) - self.config.max_capacity
                    if memory in sorted_memories[:excess_count]:
                        should_forget = True
            
            if should_forget:
                to_remove.append(memory.id)
        
        # 执行硬删除
        for memory_id in to_remove:
            if self.remove(memory_id):
                forgotten_count += 1
                logger.info(f"语义记忆硬删除: {memory_id[:8]}... (策略: {strategy})")
        
        return forgotten_count

    def clear(self):
        """清空所有语义记忆 - 包括专业数据库"""
        try:
            # 清空Qdrant向量数据库
            if self.vector_store:
                success = self.vector_store.clear_collection()
                if success:
                    logger.info("✅ Qdrant向量数据库已清空")
                else:
                    logger.warning("⚠️ Qdrant清空失败")
            
            # 清空Neo4j图数据库
            if self.graph_store:
                success = self.graph_store.clear_all()
                if success:
                    logger.info("✅ Neo4j图数据库已清空")
                else:
                    logger.warning("⚠️ Neo4j清空失败")
            
            # 清空本地缓存
            self.semantic_memories.clear()
            self.memory_embeddings.clear()
            self.entities.clear()
            self.relations.clear()
            
            logger.info("🧹 语义记忆系统已完全清空")
            
        except Exception as e:
            logger.error(f"❌ 清空语义记忆失败: {e}")
            # 即使数据库清空失败，也要清空本地缓存
        self.semantic_memories.clear()
        self.memory_embeddings.clear()
        self.entities.clear()
        self.relations.clear()

    def get_all(self) -> List[MemoryItem]:
        """获取所有语义记忆"""
        return self.semantic_memories.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取语义记忆统计信息"""
        graph_stats = {}
        try:
            if self.graph_store:
                graph_stats = self.graph_store.get_stats() or {}
        except Exception:
            graph_stats = {}

        # 硬删除模式：所有记忆都是活跃的
        active_memories = self.semantic_memories

        return {
            "count": len(active_memories),  # 活跃记忆数量
            "forgotten_count": 0,  # 硬删除模式下已遗忘的记忆会被直接删除
            "total_count": len(self.semantic_memories),  # 总记忆数量
            "entities_count": len(self.entities),
            "relations_count": len(self.relations),
            "graph_nodes": graph_stats.get("total_nodes", 0),
            "graph_edges": graph_stats.get("total_relationships", 0),
            "avg_importance": sum(m.importance for m in active_memories) / len(active_memories) if active_memories else 0.0,
            "memory_type": "enhanced_semantic"
        }
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def search_entities(self, query: str, limit: int = 10) -> List[Entity]:
        """搜索实体"""
        query_lower = query.lower()
        scored_entities = []
        
        for entity in self.entities.values():
            score = 0.0
            
            # 名称匹配
            if query_lower in entity.name.lower():
                score += 2.0
            
            # 类型匹配
            if query_lower in entity.entity_type.lower():
                score += 1.0
            
            # 描述匹配
            if query_lower in entity.description.lower():
                score += 0.5
            
            # 频率权重
            score *= math.log(1 + entity.frequency)
            
            if score > 0:
                scored_entities.append((score, entity))
        
        scored_entities.sort(key=lambda x: x[0], reverse=True)
        return [entity for _, entity in scored_entities[:limit]]
    
    def get_related_entities(
        self,
        entity_id: str,
        relation_types: List[str] = None,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """获取相关实体 - 使用Neo4j图数据库"""
        
        related = []
        
        try:
            # 使用Neo4j图数据库查找相关实体
            if not self.graph_store:
                logger.warning("⚠️ Neo4j图数据库不可用")
                return []
            
            # 使用Neo4j查找相关实体
            related_entities = self.graph_store.find_related_entities(
                entity_id=entity_id,
                relationship_types=relation_types,
                max_depth=max_hops,
                limit=50
            )
            
            # 转换格式以保持兼容性
            for entity_data in related_entities:
                # 尝试从本地缓存获取实体对象
                entity_obj = self.entities.get(entity_data.get("id"))
                if not entity_obj:
                    # 如果本地缓存没有，创建临时实体对象
                    entity_obj = Entity(
                        entity_id=entity_data.get("id", entity_id),
                        name=entity_data.get("name", ""),
                        entity_type=entity_data.get("type", "MISC")
                    )
                
                    related.append({
                    "entity": entity_obj,
                    "relation_type": entity_data.get("relationship_path", ["RELATED"])[-1] if entity_data.get("relationship_path") else "RELATED",
                    "strength": 1.0 / max(entity_data.get("distance", 1), 1),  # 距离越近强度越高
                    "distance": entity_data.get("distance", max_hops)
                })
            
            # 按距离和强度排序
            related.sort(key=lambda x: (x["distance"], -x["strength"]))
            
        except Exception as e:
            logger.error(f"❌ 获取相关实体失败: {e}")
        
        return related
    
    def export_knowledge_graph(self) -> Dict[str, Any]:
        """导出知识图谱 - 从Neo4j获取统计信息"""
        try:
            # 从Neo4j获取统计信息
            stats = {}
            if self.graph_store:
                stats = self.graph_store.get_stats()
            
            return {
                "entities": {eid: entity.to_dict() for eid, entity in self.entities.items()},
                "relations": [relation.to_dict() for relation in self.relations],
                "graph_stats": {
                    "total_nodes": stats.get("total_nodes", 0),
                    "entity_nodes": stats.get("entity_nodes", 0),
                    "memory_nodes": stats.get("memory_nodes", 0),
                    "total_relationships": stats.get("total_relationships", 0),
                    "cached_entities": len(self.entities),
                    "cached_relations": len(self.relations)
                }
            }
        except Exception as e:
            logger.error(f"❌ 导出知识图谱失败: {e}")
            return {
                "entities": {},
                "relations": [],
                "graph_stats": {"error": str(e)}
            }
