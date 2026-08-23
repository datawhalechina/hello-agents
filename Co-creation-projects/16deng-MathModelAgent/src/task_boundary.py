"""
任务边界管理模块

借鉴FirstCoder的设计，实现任务边界追踪
"""

import hashlib
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import json


class TaskStatus(Enum):
    """任务状态枚举"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class TaskBoundary:
    """任务边界数据类"""
    task_id: str
    task_hash: str
    user_message: str
    created_at: str
    status: TaskStatus
    parent_task_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskBoundary':
        """从字典创建"""
        data['status'] = TaskStatus(data['status'])
        return cls(**data)


class TaskBoundaryManager:
    """任务边界管理器"""
    
    def __init__(self):
        """初始化任务边界管理器"""
        self.tasks: Dict[str, TaskBoundary] = {}
        self.current_task: Optional[TaskBoundary] = None
        self.task_history: List[str] = []
    
    def _generate_task_hash(self, user_message: str, timestamp: str) -> str:
        """
        生成任务哈希
        
        Args:
            user_message: 用户消息
            timestamp: 时间戳
            
        Returns:
            任务哈希值
        """
        content = f"{user_message}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def create_task(self, user_message: str, parent_task_id: Optional[str] = None) -> TaskBoundary:
        """
        创建新任务
        
        Args:
            user_message: 用户消息
            parent_task_id: 父任务ID
            
        Returns:
            任务边界对象
        """
        task_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        task_hash = self._generate_task_hash(user_message, timestamp)
        
        task = TaskBoundary(
            task_id=task_id,
            task_hash=task_hash,
            user_message=user_message,
            created_at=timestamp,
            status=TaskStatus.CREATED,
            parent_task_id=parent_task_id,
            metadata={}
        )
        
        self.tasks[task_id] = task
        self.current_task = task
        self.task_history.append(task_id)
        
        return task
    
    def get_current_task(self) -> Optional[TaskBoundary]:
        """获取当前任务"""
        return self.current_task
    
    def get_task(self, task_id: str) -> Optional[TaskBoundary]:
        """获取指定任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                           metadata: Optional[Dict[str, Any]] = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            metadata: 元数据
        """
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if metadata:
                self.tasks[task_id].metadata.update(metadata)
    
    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        """
        完成任务
        
        Args:
            task_id: 任务ID
            result: 任务结果
        """
        self.update_task_status(task_id, TaskStatus.COMPLETED, {"result": result})
    
    def fail_task(self, task_id: str, error: str):
        """
        任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        self.update_task_status(task_id, TaskStatus.FAILED, {"error": error})
    
    def pause_task(self, task_id: str, reason: str):
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            reason: 暂停原因
        """
        self.update_task_status(task_id, TaskStatus.PAUSED, {"pause_reason": reason})
    
    def resume_task(self, task_id: str) -> Optional[TaskBoundary]:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            恢复的任务
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PAUSED:
                task.status = TaskStatus.IN_PROGRESS
                self.current_task = task
                return task
        return None
    
    def is_new_task(self, user_message: str) -> bool:
        """
        判断是否是新任务
        
        Args:
            user_message: 用户消息
            
        Returns:
            是否是新任务
        """
        if not self.current_task:
            return True
        
        # 简单判断：如果消息完全不同，可能是新任务
        # 实际应用中可以使用更复杂的语义相似度计算
        current_msg = self.current_task.user_message
        return user_message != current_msg
    
    def get_task_chain(self, task_id: str) -> List[TaskBoundary]:
        """
        获取任务链
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务链
        """
        chain = []
        current_id = task_id
        
        while current_id:
            task = self.tasks.get(current_id)
            if task:
                chain.append(task)
                current_id = task.parent_task_id
            else:
                break
        
        return list(reversed(chain))
    
    def get_all_tasks(self) -> List[TaskBoundary]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def export_tasks(self) -> str:
        """导出任务数据"""
        data = {
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "current_task_id": self.current_task.task_id if self.current_task else None,
            "task_history": self.task_history
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def import_tasks(self, data: str):
        """导入任务数据"""
        parsed = json.loads(data)
        
        self.tasks = {
            k: TaskBoundary.from_dict(v) 
            for k, v in parsed["tasks"].items()
        }
        
        if parsed.get("current_task_id"):
            self.current_task = self.tasks.get(parsed["current_task_id"])
        
        self.task_history = parsed.get("task_history", [])


class TaskContext:
    """任务上下文"""
    
    def __init__(self, task: TaskBoundary):
        """
        初始化任务上下文
        
        Args:
            task: 任务边界
        """
        self.task = task
        self.messages: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.tool_results: List[Dict[str, Any]] = []
        self.artifacts: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
    
    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any], 
                      request_id: str):
        """添加工具调用"""
        self.tool_calls.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_tool_result(self, request_id: str, result: Any, success: bool):
        """添加工具结果"""
        self.tool_results.append({
            "request_id": request_id,
            "result": result,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def set_artifact(self, key: str, value: Any):
        """设置产物"""
        self.artifacts[key] = value
    
    def get_artifact(self, key: str) -> Any:
        """获取产物"""
        return self.artifacts.get(key)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "task_id": self.task.task_id,
            "task_hash": self.task.task_hash,
            "message_count": len(self.messages),
            "tool_call_count": len(self.tool_calls),
            "tool_result_count": len(self.tool_results),
            "artifact_keys": list(self.artifacts.keys())
        }
    
    def compact(self, max_messages: int = 10) -> 'TaskContext':
        """
        压缩上下文
        
        Args:
            max_messages: 最大保留消息数
            
        Returns:
            压缩后的上下文
        """
        compacted = TaskContext(self.task)
        
        # 保留最近的消息
        if len(self.messages) > max_messages:
            compacted.messages = self.messages[-max_messages:]
        else:
            compacted.messages = self.messages.copy()
        
        # 保留工具调用和结果的摘要
        compacted.tool_calls = self.tool_calls.copy()
        compacted.tool_results = self.tool_results.copy()
        compacted.artifacts = self.artifacts.copy()
        
        return compacted


# 测试代码
if __name__ == "__main__":
    # 测试任务边界管理器
    manager = TaskBoundaryManager()
    
    # 创建任务
    task1 = manager.create_task("分析数学建模问题")
    print(f"创建任务: {task1.task_id}")
    
    # 更新状态
    manager.update_task_status(task1.task_id, TaskStatus.IN_PROGRESS)
    
    # 创建子任务
    task2 = manager.create_task("生成求解代码", parent_task_id=task1.task_id)
    print(f"创建子任务: {task2.task_id}")
    
    # 完成任务
    manager.complete_task(task2.task_id, {"code": "print('Hello')"})
    
    # 获取任务链
    chain = manager.get_task_chain(task2.task_id)
    print(f"任务链长度: {len(chain)}")
    
    # 导出任务
    exported = manager.export_tasks()
    print(f"导出数据长度: {len(exported)}")
    
    print("任务边界管理测试完成！")
