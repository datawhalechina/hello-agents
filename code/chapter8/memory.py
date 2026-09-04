"""记忆系统数据类

提供 MemoryConfig 和 MemoryItem，供 MemoryTool 及演示脚本使用。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class MemoryConfig:
    """记忆系统配置"""

    working_memory_capacity: int = 50
    working_memory_ttl_minutes: int = 60
    enable_working: bool = True
    enable_episodic: bool = True
    enable_semantic: bool = True
    enable_perceptual: bool = False


@dataclass
class MemoryItem:
    """单条记忆"""

    content: str
    memory_type: str = "working"
    importance: float = 0.5
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
