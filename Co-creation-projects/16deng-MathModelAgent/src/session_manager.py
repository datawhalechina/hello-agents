"""
会话管理模块

借鉴FirstCoder的会话持久化设计
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum


class EventType(Enum):
    """事件类型枚举"""
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL = "approval"
    TASK_BOUNDARY = "task_boundary"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class SessionEvent:
    """会话事件"""
    event_id: str
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionEvent':
        """从字典创建"""
        data['event_type'] = EventType(data['event_type'])
        return cls(**data)


@dataclass
class Session:
    """会话"""
    session_id: str
    project_name: str
    created_at: str
    updated_at: str
    name: str
    events: List[SessionEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "name": self.name,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """从字典创建"""
        data['events'] = [SessionEvent.from_dict(e) for e in data.get('events', [])]
        return cls(**data)


class SessionManager:
    """会话管理器"""
    
    def __init__(self, session_dir: str = "./sessions"):
        """
        初始化会话管理器
        
        Args:
            session_dir: 会话存储目录
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[Session] = None
        self.sessions: Dict[str, Session] = {}
        
        # 加载现有会话
        self._load_sessions()
    
    def _load_sessions(self):
        """加载现有会话"""
        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = Session.from_dict(data)
                self.sessions[session.session_id] = session
            except Exception as e:
                print(f"加载会话失败 {session_file}: {e}")
    
    def _save_session(self, session: Session):
        """保存会话"""
        session_file = self.session_dir / f"{session.session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    
    def create_session(self, project_name: str, name: Optional[str] = None) -> Session:
        """
        创建新会话
        
        Args:
            project_name: 项目名称
            name: 会话名称
            
        Returns:
            新会话
        """
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        session = Session(
            session_id=session_id,
            project_name=project_name,
            created_at=timestamp,
            updated_at=timestamp,
            name=name or f"Session {session_id}",
            events=[],
            metadata={}
        )
        
        # 添加会话开始事件
        self.add_event(session, EventType.SESSION_START, {
            "project_name": project_name
        })
        
        self.sessions[session_id] = session
        self.current_session = session
        self._save_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Session]:
        """列出所有会话"""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
    
    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        恢复会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            恢复的会话
        """
        session = self.sessions.get(session_id)
        if session:
            self.current_session = session
            return session
        return None
    
    def fork_session(self, session_id: str, new_name: Optional[str] = None) -> Optional[Session]:
        """
        分叉会话
        
        Args:
            session_id: 源会话ID
            new_name: 新会话名称
            
        Returns:
            新会话
        """
        source = self.sessions.get(session_id)
        if not source:
            return None
        
        new_session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        new_session = Session(
            session_id=new_session_id,
            project_name=source.project_name,
            created_at=timestamp,
            updated_at=timestamp,
            name=new_name or f"Fork of {source.name}",
            events=source.events.copy(),
            metadata={**source.metadata, "forked_from": session_id}
        )
        
        self.sessions[new_session_id] = new_session
        self.current_session = new_session
        self._save_session(new_session)
        
        return new_session
    
    def rename_session(self, session_id: str, new_name: str):
        """
        重命名会话
        
        Args:
            session_id: 会话ID
            new_name: 新名称
        """
        session = self.sessions.get(session_id)
        if session:
            session.name = new_name
            session.updated_at = datetime.now().isoformat()
            self._save_session(session)
    
    def add_event(self, session: Session, event_type: EventType, 
                  data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        添加事件
        
        Args:
            session: 会话
            event_type: 事件类型
            data: 事件数据
            metadata: 元数据
        """
        event = SessionEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            metadata=metadata or {}
        )
        
        session.events.append(event)
        session.updated_at = datetime.now().isoformat()
        self._save_session(session)
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息事件"""
        if self.current_session:
            self.add_event(self.current_session, EventType.MESSAGE, {
                "role": role,
                "content": content,
                **kwargs
            })
    
    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any], 
                      request_id: str):
        """添加工具调用事件"""
        if self.current_session:
            self.add_event(self.current_session, EventType.TOOL_CALL, {
                "tool_name": tool_name,
                "arguments": arguments,
                "request_id": request_id
            })
    
    def add_tool_result(self, request_id: str, result: Any, success: bool):
        """添加工具结果事件"""
        if self.current_session:
            self.add_event(self.current_session, EventType.TOOL_RESULT, {
                "request_id": request_id,
                "result": result,
                "success": success
            })
    
    def add_approval(self, request_id: str, approved: bool, 
                     approver: str = "user"):
        """添加审批事件"""
        if self.current_session:
            self.add_event(self.current_session, EventType.APPROVAL, {
                "request_id": request_id,
                "approved": approved,
                "approver": approver
            })
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话摘要
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话摘要
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        event_counts = {}
        for event in session.events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "session_id": session.session_id,
            "name": session.name,
            "project_name": session.project_name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "event_count": len(session.events),
            "event_counts": event_counts
        }
    
    def export_session(self, session_id: str) -> str:
        """导出会话"""
        session = self.sessions.get(session_id)
        if session:
            return json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
        return ""
    
    def import_session(self, data: str) -> Session:
        """导入会话"""
        parsed = json.loads(data)
        session = Session.from_dict(parsed)
        self.sessions[session.session_id] = session
        self._save_session(session)
        return session


# 测试代码
if __name__ == "__main__":
    # 测试会话管理器
    manager = SessionManager(session_dir="./test_sessions")
    
    # 创建会话
    session = manager.create_session("MathModelAgent", "测试会话")
    print(f"创建会话: {session.session_id}")
    
    # 添加消息
    manager.add_message("user", "请帮我分析这个数学建模问题")
    manager.add_message("assistant", "好的，我来帮你分析...")
    
    # 添加工具调用
    manager.add_tool_call("code_analysis", {"code": "print('hello')"}, "req-001")
    manager.add_tool_result("req-001", {"output": "hello"}, True)
    
    # 获取摘要
    summary = manager.get_session_summary(session.session_id)
    print(f"会话摘要: {summary}")
    
    # 列出会话
    sessions = manager.list_sessions()
    print(f"会话数量: {len(sessions)}")
    
    # 分叉会话
    forked = manager.fork_session(session.session_id, "分叉会话")
    print(f"分叉会话: {forked.session_id}")
    
    print("会话管理测试完成！")
    
    # 清理测试数据
    import shutil
    shutil.rmtree("./test_sessions", ignore_errors=True)
