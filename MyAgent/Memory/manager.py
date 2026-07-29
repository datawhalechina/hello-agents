import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from MyAgent.Memory.base import MemoryConfig, MemoryItem
from MyAgent.Memory.type.episodic import EpisodicMemory
from MyAgent.Memory.type.working import WorkingMemory

logger = logging.getLogger(__name__)
class MemoryManager:
    def __init__(
            self,
            config: Optional[MemoryConfig] = None,
            user_id: str = "default_user",
            enable_working: bool = True,
            enable_episodic: bool = True,
            enable_semantic: bool = True,
            enable_perceptual: bool = False
    ):
        self.config = config or MemoryConfig()
        self.user_id = user_id
        # 初始化各类型记忆
        self.memory_types = {}

        if enable_working:
            self.memory_types['working'] = WorkingMemory(self.config)

        if enable_episodic:
            self.memory_types['episodic'] = EpisodicMemory(self.config)
        #
        # if enable_semantic:
        #     self.memory_types['semantic'] = SemanticMemory(self.config)
        #
        # if enable_perceptual:
        #     self.memory_types['perceptual'] = PerceptualMemory(self.config)

        logger.info(f"MemoryManager初始化完成，启用记忆类型: {list(self.memory_types.keys())}")

    def add_memory(
            self,
            content: str,
            memory_type: str = "working",
            importance: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None,
            auto_classify: bool = True
    ) -> str:
        """添加记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性分数 (0-1)
            metadata: 元数据
            auto_classify: 是否自动分类到合适的记忆类型

        Returns:
            记忆ID
        """
        # 自动分类记忆类型
        if auto_classify:
            memory_type = self._classify_memory_type(content, metadata)

        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content, metadata)

        # 创建记忆项
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            user_id=self.user_id,
            timestamp=datetime.now(),
            importance=importance,
            metadata=metadata or {}
        )

        # 添加到对应的记忆类型
        if memory_type in self.memory_types:
            memory_id = self.memory_types[memory_type].add(memory_item)
            logger.debug(f"添加记忆到 {memory_type}: {memory_id}")
            return memory_id
        else:
            raise ValueError(f"不支持的记忆类型: {memory_type}")

    def _classify_memory_type(self, content: str, metadata: Optional[Dict[str, Any]]) -> str:
        """自动分类记忆类型"""
        if metadata and metadata.get("type"):
            return metadata["type"]

        # 简单的分类逻辑，可以扩展为更复杂的分类器
        if self._is_episodic_content(content):
            return "episodic"
        elif self._is_semantic_content(content):
            return "semantic"
        else:
            return "working"

    def _calculate_importance(self, content: str, metadata: Optional[Dict[str, Any]]) -> float:
        """计算记忆重要性"""
        importance = 0.5  # 基础重要性

        # 基于内容长度
        if len(content) > 100:
            importance += 0.1

        # 基于关键词
        important_keywords = ["重要", "关键", "必须", "注意", "警告", "错误"]
        if any(keyword in content for keyword in important_keywords):
            importance += 0.2

        # 基于元数据
        if metadata:
            if metadata.get("priority") == "high":
                importance += 0.3
            elif metadata.get("priority") == "low":
                importance -= 0.2

        return max(0.0, min(1.0, importance))


    def retrieve_memories(
            self,
            query: str,
            memory_types: Optional[List[str]] = None,
            limit: int = 10,
            min_importance: float = 0.0,
            time_range: Optional[tuple] = None
    ) -> List[MemoryItem]:
        """检索记忆

        Args:
            query: 查询内容
            memory_types: 要检索的记忆类型列表
            limit: 返回数量限制
            min_importance: 最小重要性阈值
            time_range: 时间范围 (start_time, end_time)

        Returns:
            检索到的记忆列表
        """
        if memory_types is None:
            memory_types = list(self.memory_types.keys())

        # 从各个记忆类型中检索
        all_results = []
        per_type_limit = max(1, limit // len(memory_types))

        for memory_type in memory_types:
            if memory_type in self.memory_types:
                memory_instance = self.memory_types[memory_type]
                try:
                    # 使用各个记忆类型自己的检索方法
                    type_results = memory_instance.retrieve(
                        query=query,
                        limit=per_type_limit,
                        min_importance=min_importance,
                        user_id=self.user_id
                    )
                    all_results.extend(type_results)
                except Exception as e:
                    logger.warning(f"检索 {memory_type} 记忆时出错: {e}")
                    continue

        # 按重要性和相关性排序
        all_results.sort(key=lambda x: x.importance, reverse=True)
        return all_results[:limit]