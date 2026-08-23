"""
上下文管理模块

借鉴FirstCoder的上下文压缩和归档设计
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ContextWindow:
    """上下文窗口"""
    system_prefix: str
    current_messages: List[Dict[str, Any]]
    tool_results_preview: List[Dict[str, Any]]
    total_tokens: int = 0
    max_tokens: int = 4000
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "system_prefix_length": len(self.system_prefix),
            "message_count": len(self.current_messages),
            "tool_result_count": len(self.tool_results_preview),
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round(self.total_tokens / self.max_tokens * 100, 2)
        }


@dataclass
class ArchiveEntry:
    """归档条目"""
    archive_id: str
    content: str
    content_hash: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "archive_id": self.archive_id,
            "content": self.content,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveEntry':
        """从字典创建"""
        return cls(**data)


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, max_tokens: int = 4000, archive_dir: str = "./archives"):
        """
        初始化上下文管理器
        
        Args:
            max_tokens: 最大token数
            archive_dir: 归档目录
        """
        self.max_tokens = max_tokens
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.system_prefix: str = ""
        self.messages: List[Dict[str, Any]] = []
        self.tool_results: Dict[str, Any] = {}
        self.archives: Dict[str, ArchiveEntry] = {}
        
        # 加载现有归档
        self._load_archives()
    
    def _load_archives(self):
        """加载现有归档"""
        for archive_file in self.archive_dir.glob("*.json"):
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                entry = ArchiveEntry.from_dict(data)
                self.archives[entry.archive_id] = entry
            except Exception as e:
                print(f"加载归档失败 {archive_file}: {e}")
    
    def _save_archive(self, entry: ArchiveEntry):
        """保存归档"""
        archive_file = self.archive_dir / f"{entry.archive_id}.json"
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _generate_archive_id(self, content: str) -> str:
        """生成归档ID"""
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"archive-{hash_value}"
    
    def set_system_prefix(self, prefix: str):
        """设置系统前缀"""
        self.system_prefix = prefix
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
    
    def add_tool_result(self, request_id: str, result: Any, 
                        preview: Optional[str] = None):
        """
        添加工具结果
        
        Args:
            request_id: 请求ID
            result: 完整结果
            preview: 预览内容
        """
        # 保存完整结果
        self.tool_results[request_id] = result
        
        # 如果结果太大，归档并只保留预览
        result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
        
        if len(result_str) > 500:  # 超过500字符归档
            archive_id = self._generate_archive_id(result_str)
            entry = ArchiveEntry(
                archive_id=archive_id,
                content=result_str,
                content_hash=hashlib.sha256(result_str.encode()).hexdigest(),
                created_at=datetime.now().isoformat(),
                metadata={"request_id": request_id, "original_length": len(result_str)}
            )
            self.archives[archive_id] = entry
            self._save_archive(entry)
            
            # 只保留预览
            self.tool_results[request_id] = {
                "_archived": True,
                "archive_id": archive_id,
                "preview": preview or result_str[:200] + "...",
                "original_length": len(result_str)
            }
    
    def retrieve_archive(self, archive_id: str, 
                         max_length: int = 1000) -> Optional[str]:
        """
        读取归档内容
        
        Args:
            archive_id: 归档ID
            max_length: 最大读取长度
            
        Returns:
            归档内容
        """
        entry = self.archives.get(archive_id)
        if entry:
            if len(entry.content) > max_length:
                return entry.content[:max_length] + "\n...(已截断)"
            return entry.content
        return None
    
    def get_context_window(self) -> ContextWindow:
        """获取当前上下文窗口"""
        # 估算token数（简化：1个中文字符≈2token，1个英文单词≈1token）
        total_tokens = len(self.system_prefix) * 2
        
        for msg in self.messages:
            content = msg.get("content", "")
            total_tokens += len(content) * 2
        
        for result in self.tool_results.values():
            if isinstance(result, dict) and result.get("_archived"):
                total_tokens += len(result.get("preview", "")) * 2
            elif isinstance(result, str):
                total_tokens += len(result) * 2
        
        # 构建工具结果预览
        tool_results_preview = []
        for request_id, result in self.tool_results.items():
            if isinstance(result, dict) and result.get("_archived"):
                tool_results_preview.append({
                    "request_id": request_id,
                    "preview": result.get("preview", ""),
                    "archived": True,
                    "archive_id": result.get("archive_id")
                })
            else:
                tool_results_preview.append({
                    "request_id": request_id,
                    "result": result,
                    "archived": False
                })
        
        return ContextWindow(
            system_prefix=self.system_prefix,
            current_messages=self.messages.copy(),
            tool_results_preview=tool_results_preview,
            total_tokens=total_tokens,
            max_tokens=self.max_tokens
        )
    
    def compact(self, keep_recent: int = 10):
        """
        压缩上下文
        
        Args:
            keep_recent: 保留最近的消息数
        """
        if len(self.messages) > keep_recent:
            # 归档旧消息
            old_messages = self.messages[:-keep_recent]
            old_content = json.dumps(old_messages, ensure_ascii=False)
            
            archive_id = self._generate_archive_id(old_content)
            entry = ArchiveEntry(
                archive_id=archive_id,
                content=old_content,
                content_hash=hashlib.sha256(old_content.encode()).hexdigest(),
                created_at=datetime.now().isoformat(),
                metadata={
                    "type": "messages_archive",
                    "message_count": len(old_messages)
                }
            )
            self.archives[archive_id] = entry
            self._save_archive(entry)
            
            # 只保留最近的消息
            self.messages = self.messages[-keep_recent:]
            
            # 在消息开头添加归档引用
            self.messages.insert(0, {
                "role": "system",
                "content": f"[已归档 {len(old_messages)} 条历史消息，归档ID: {archive_id}]"
            })
    
    def is_near_limit(self, threshold: float = 0.8) -> bool:
        """
        是否接近token限制
        
        Args:
            threshold: 阈值
            
        Returns:
            是否接近限制
        """
        window = self.get_context_window()
        return window.total_tokens > window.max_tokens * threshold
    
    def auto_compact(self):
        """自动压缩"""
        if self.is_near_limit(0.9):
            self.compact(keep_recent=5)
        elif self.is_near_limit(0.8):
            self.compact(keep_recent=8)
    
    def get_full_context(self) -> Dict[str, Any]:
        """获取完整上下文"""
        return {
            "system_prefix": self.system_prefix,
            "messages": self.messages,
            "tool_results": self.tool_results,
            "archive_ids": list(self.archives.keys())
        }
    
    def export_context(self) -> str:
        """导出上下文"""
        return json.dumps(self.get_full_context(), ensure_ascii=False, indent=2)
    
    def import_context(self, data: str):
        """导入上下文"""
        parsed = json.loads(data)
        self.system_prefix = parsed.get("system_prefix", "")
        self.messages = parsed.get("messages", [])
        self.tool_results = parsed.get("tool_results", {})


# 测试代码
if __name__ == "__main__":
    # 测试上下文管理器
    manager = ContextManager(max_tokens=1000)
    
    # 设置系统前缀
    manager.set_system_prefix("你是一个数学建模助手。")
    
    # 添加消息
    manager.add_message("user", "请帮我分析这个优化问题")
    manager.add_message("assistant", "好的，我来分析...")
    
    # 添加大结果（会自动归档）
    large_result = "x" * 1000
    manager.add_tool_result("req-001", large_result)
    
    # 获取上下文窗口
    window = manager.get_context_window()
    print(f"上下文窗口: {window.get_summary()}")
    
    # 读取归档
    for archive_id in manager.archives:
        content = manager.retrieve_archive(archive_id, max_length=100)
        print(f"归档 {archive_id}: {content[:50]}...")
    
    # 测试压缩
    for i in range(20):
        manager.add_message("user", f"消息 {i}")
    
    print(f"压缩前消息数: {len(manager.messages)}")
    manager.compact(keep_recent=5)
    print(f"压缩后消息数: {len(manager.messages)}")
    
    print("上下文管理测试完成！")
