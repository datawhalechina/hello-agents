"""
上下文管理器
管理智能体之间的上下文共享和传递
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.observability.logger import default_logger as logger


class ContextManager:
    """
    上下文管理器
    管理请求的上下文信息，支持在智能体间共享和传递
    """
    
    def __init__(self, request_id: str):
        """
        初始化上下文管理器
        
        Args:
            request_id: 请求ID
        """
        self.request_id = request_id
        self.context: Dict[str, Any] = {
            "request_id": request_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
            "history": [],
            "agent_contexts": {},
            "shared_data": {}
        }
        logger.info(f"上下文管理器初始化 - RequestID: {request_id}")
    
    def update_context(
        self,
        agent_name: str,
        context_data: Dict[str, Any],
        context_type: str = "info"
    ):
        """
        更新上下文
        
        Args:
            agent_name: 智能体名称
            context_data: 上下文数据
            context_type: 上下文类型（info, result, error, feedback等）
        """
        if agent_name not in self.context["agent_contexts"]:
            self.context["agent_contexts"][agent_name] = {
                "created_at": datetime.now().isoformat(),
                "updates": []
            }
        
        update_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": context_type,
            "data": context_data
        }
        
        self.context["agent_contexts"][agent_name]["updates"].append(update_entry)
        self.context["agent_contexts"][agent_name]["last_updated"] = datetime.now().isoformat()
        self.context["updated_at"] = datetime.now().isoformat()
        self.context["version"] += 1
        
        # 记录历史
        self.context["history"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": "update_context",
            "type": context_type
        })
        
        logger.debug(f"上下文已更新 - Agent: {agent_name}, Type: {context_type}")
    
    def get_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """
        获取指定智能体的上下文
        
        Args:
            agent_name: 智能体名称
        
        Returns:
            智能体上下文数据
        """
        return self.context["agent_contexts"].get(agent_name, {})
    
    def get_all_context(self) -> Dict[str, Any]:
        """
        获取所有上下文
        
        Returns:
            完整上下文数据
        """
        return self.context
    
    def share_data(
        self,
        key: str,
        data: Any,
        from_agent: Optional[str] = None
    ):
        """
        共享数据给其他智能体
        
        Args:
            key: 数据键
            data: 数据内容
            from_agent: 来源智能体名称
        """
        self.context["shared_data"][key] = {
            "data": data,
            "from_agent": from_agent,
            "timestamp": datetime.now().isoformat()
        }
        
        self.context["updated_at"] = datetime.now().isoformat()
        
        logger.debug(f"数据已共享 - Key: {key}, From: {from_agent}")
    
    def get_shared_data(self, key: str) -> Optional[Any]:
        """
        获取共享数据
        
        Args:
            key: 数据键
        
        Returns:
            数据内容，如果不存在则返回None
        """
        shared_item = self.context["shared_data"].get(key)
        if shared_item:
            return shared_item["data"]
        return None
    
    def get_all_shared_data(self) -> Dict[str, Any]:
        """
        获取所有共享数据
        
        Returns:
            所有共享数据
        """
        return {k: v["data"] for k, v in self.context["shared_data"].items()}
    
    def add_memory_context(
        self,
        memory_type: str,
        memory_data: Dict[str, Any]
    ):
        """
        添加上下文中的记忆信息
        
        Args:
            memory_type: 记忆类型
            memory_data: 记忆数据
        """
        if "memory_context" not in self.context:
            self.context["memory_context"] = {}
        
        self.context["memory_context"][memory_type] = memory_data
        self.context["updated_at"] = datetime.now().isoformat()
    
    def get_memory_context(self) -> Dict[str, Any]:
        """
        获取记忆上下文
        
        Returns:
            记忆上下文数据
        """
        return self.context.get("memory_context", {})
    
    def create_snapshot(self) -> Dict[str, Any]:
        """
        创建上下文快照（用于回溯）
        
        Returns:
            上下文快照
        """
        snapshot = {
            "snapshot_id": f"{self.request_id}_snapshot_{self.context['version']}",
            "timestamp": datetime.now().isoformat(),
            "context": self.context.copy()
        }
        return snapshot
    
    def restore_from_snapshot(self, snapshot: Dict[str, Any]):
        """
        从快照恢复上下文
        
        Args:
            snapshot: 上下文快照
        """
        if "context" in snapshot:
            self.context = snapshot["context"].copy()
            self.context["updated_at"] = datetime.now().isoformat()
            logger.info(f"上下文已从快照恢复 - SnapshotID: {snapshot.get('snapshot_id')}")


# 全局上下文管理器存储（按请求ID）
_context_managers: Dict[str, ContextManager] = {}


def get_context_manager(request_id: str) -> ContextManager:
    """
    获取或创建上下文管理器
    
    Args:
        request_id: 请求ID
    
    Returns:
        上下文管理器实例
    """
    if request_id not in _context_managers:
        _context_managers[request_id] = ContextManager(request_id)
    return _context_managers[request_id]


def remove_context_manager(request_id: str):
    """
    移除上下文管理器（请求完成后清理）
    
    Args:
        request_id: 请求ID
    """
    if request_id in _context_managers:
        del _context_managers[request_id]
        logger.debug(f"上下文管理器已移除 - RequestID: {request_id}")

