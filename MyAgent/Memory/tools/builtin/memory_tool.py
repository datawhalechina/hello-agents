from datetime import datetime, timedelta
from typing import List, Dict, Any

from MyAgent.Memory.base import MemoryConfig
from MyAgent.Memory.manager import MemoryManager


class MemoryTool():
    def __init__(
            self,
            user_id: str = "default_user",
            memory_config: MemoryConfig = None,
            memory_types: List[str] = None
    ):
        self.user_id = user_id

        # 初始化记忆管理器
        self.memory_config = memory_config or MemoryConfig()
        self.memory_types = memory_types or ["working", "episodic", "semantic"]

        self.memory_manager = MemoryManager(
            config=self.memory_config,
            user_id=user_id,
            enable_working="working" in self.memory_types,
            enable_episodic="episodic" in self.memory_types,
            enable_semantic="semantic" in self.memory_types,
            enable_perceptual="perceptual" in self.memory_types
        )

        # 会话状态
        self.current_session_id = None
        self.conversation_count = 0


    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具 - Tool基类要求的接口

        Args:
            parameters: 工具参数字典，必须包含action参数

        Returns:
            执行结果字符串
        """
        # if not self.validate_parameters(parameters):
        #     return "❌ 参数验证失败：缺少必需的参数"

        action = parameters.get("action")
        # 移除action参数，传递其余参数给execute方法
        kwargs = {k: v for k, v in parameters.items() if k != "action"}

        return self.execute(action, **kwargs)


    def execute(self, action: str, **kwargs) -> str:
        """执行记忆操作

        支持的操作：
        - add: 添加记忆
        - search: 搜索记忆
        - summary: 获取记忆摘要
        - stats: 获取统计信息
        """

        if action == "add":
            return self._add_memory(**kwargs)
        elif action == "search":
            return self._search_memory(**kwargs)
        elif action == "summary":
            return self._get_summary(**kwargs)
        elif action == "stats":
            return self._get_stats()
        elif action == "update":
            return self._update_memory(**kwargs)
        elif action == "remove":
            return self._remove_memory(**kwargs)
        elif action == "forget":
            return self._forget(**kwargs)
        elif action == "consolidate":
            return self._consolidate(**kwargs)
        elif action == "clear_all":
            return self._clear_all()
        else:
            return f"不支持的操作: {action}。支持的操作: add, search, summary, stats, update, remove, forget, consolidate, clear_all"

    def _add_memory(
            self,
            content: str = "",
            memory_type: str = "working",
            importance: float = 0.5,
            file_path: str = None,
            modality: str = None,
            **metadata
    ) -> str:
        """添加记忆"""
        try:
            # 确保会话ID存在
            if self.current_session_id is None:
                self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                # 感知记忆文件支持：注入 raw_data 与模态
            if memory_type == "perceptual" and file_path:
                inferred = modality or self._infer_modality(file_path)
                metadata.setdefault("modality", inferred)
                metadata.setdefault("raw_data", file_path)
            memory_id = self.memory_manager.add_memory(
                content=content,
                memory_type=memory_type,
                importance=importance,
                metadata=metadata,
                auto_classify=False  # 禁用自动分类，使用明确指定的类型
            )

            return f"✅ 记忆已添加 (ID: {memory_id[:8]}...)"

        except Exception as e:
            return f"❌ 添加记忆失败: {str(e)}"

    def _search_memory(
        self,
        query: str,
        limit: int = 5,
        memory_types: List[str] = None,
        memory_type: str = None,  # 添加单数形式的参数支持
        min_importance: float = 0.1
    ) -> str:
        """搜索记忆"""
        try:
            # 处理单数形式的memory_type参数
            if memory_type and not memory_types:
                memory_types = [memory_type]

            results = self.memory_manager.retrieve_memories(
                query=query,
                limit=limit,
                memory_types=memory_types,
                min_importance=min_importance
            )

            if not results:
                return f"🔍 未找到与 '{query}' 相关的记忆"

            # 格式化结果
            formatted_results = []
            formatted_results.append(f"🔍 找到 {len(results)} 条相关记忆:")

            for i, memory in enumerate(results, 1):
                memory_type_label = {
                    "working": "工作记忆",
                    "episodic": "情景记忆",
                    "semantic": "语义记忆",
                    "perceptual": "感知记忆"
                }.get(memory.memory_type, memory.memory_type)

                content_preview = memory.content[:80] + "..." if len(memory.content) > 80 else memory.content
                formatted_results.append(
                    f"{i}. [{memory_type_label}] {content_preview} (重要性: {memory.importance:.2f})"
                )

            return "\n".join(formatted_results)

        except Exception as e:
            return f"❌ 搜索记忆失败: {str(e)}"