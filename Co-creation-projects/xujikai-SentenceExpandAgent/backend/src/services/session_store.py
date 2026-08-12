"""
内存会话管理 - 英语句子扩写智能体
"""
import uuid
from typing import Optional
from models.entities import SessionState


class SessionStore:
    """内存会话存储（支持并发）"""
    
    def __init__(self):
        """初始化会话存储"""
        self._sessions: dict[str, SessionState] = {}
    
    def create_session(
        self,
        seed_sentence: str,
        mode: str = "manual"
    ) -> SessionState:
        """
        创建新会话
        
        Args:
            seed_sentence: 种子句
            mode: 模式（manual/auto）
            
        Returns:
            SessionState: 新创建的会话状态
        """
        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            mode=mode,
            seed_sentence=seed_sentence,
            current_stage="stage1",
            rounds=[]
        )
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        获取会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[SessionState]: 会话状态，不存在则返回 None
        """
        return self._sessions.get(session_id)
    
    def update_session(self, session: SessionState) -> None:
        """
        更新会话
        
        Args:
            session: 更新后的会话状态
        """
        self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 删除成功返回 True，会话不存在返回 False
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> list[SessionState]:
        """
        列出所有会话
        
        Returns:
            list[SessionState]: 所有会话状态列表
        """
        return list(self._sessions.values())
    
    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 存在返回 True，否则返回 False
        """
        return session_id in self._sessions


# 全局会话存储实例（单例）
_session_store_instance = None


def get_session_store() -> SessionStore:
    """
    获取全局会话存储实例（单例模式）
    
    Returns:
        SessionStore: 会话存储实例
    """
    global _session_store_instance
    if _session_store_instance is None:
        _session_store_instance = SessionStore()
    return _session_store_instance


def reset_session_store():
    """重置会话存储（用于测试）"""
    global _session_store_instance
    _session_store_instance = None
