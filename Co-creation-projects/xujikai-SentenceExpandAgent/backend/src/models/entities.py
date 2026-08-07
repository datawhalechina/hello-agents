"""
数据实体定义 - 英语句子扩写智能体
"""
from pydantic import BaseModel
from typing import Optional, Literal


# 扩写阶段枚举
Stage = Literal["stage1", "stage2", "stage3", "done"]


# 单次扩写轮次记录
class RoundRecord(BaseModel):
    """记录单个扩写轮次的完整信息"""
    stage: Stage
    question: str  # 记者提问
    user_answer: str  # 用户输入的句子
    evaluation: str  # 语法点评
    expanded_sentence: str  # 本轮扩写结果


# 整个会话状态
class SessionState(BaseModel):
    """会话完整状态管理"""
    session_id: str
    mode: Literal["manual", "auto"]
    seed_sentence: str
    current_stage: Stage
    rounds: list[RoundRecord] = []
    final_polished: Optional[str] = None


# 前端发起请求
class StartRequest(BaseModel):
    """开始新的扩写会话"""
    seed_sentence: str
    mode: Literal["manual", "auto"]


# 用户提交扩写句子（手动模式）
class SubmitRequest(BaseModel):
    """提交用户扩写的句子"""
    session_id: str
    user_sentence: str


# 智能体单次响应
class AgentResponse(BaseModel):
    """智能体响应数据"""
    session_id: str
    stage: Stage
    question: Optional[str] = None
    evaluation: Optional[str] = None
    expanded_sentence: Optional[str] = None
    final_polished: Optional[str] = None
    is_done: bool = False
