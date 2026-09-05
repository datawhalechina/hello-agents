from typing import Dict, Optional, List

from pydantic import BaseModel, Field


class UserMemory(BaseModel):
    """用户长期记忆：保存用户基础信息、习惯、约束、历史计划反馈"""
    user_id: str
    work_start: str
    work_end: str
    rest_days: List[str]
    avoid_time: List[str]
    preference: Dict[str,str]
    hobbies: List[str]
    dislike: List[str]
    history_task: List[Dict] = Field(default_factory=list)
    custorm_constraints: List[Dict] = Field(default_factory=list)


class Task(BaseModel):
    """解析用户自然语言后得到的结构化任务实体"""
    task_id: str
    task_name: str
    description: str
    estimated_duration_min: int
    deadline: Optional[str] = None
    priority: str = Field(default="medium")
    fixed_time: Optional[str] = None
    allowed_time: Optional[List[str]] = None
    depend_on: List[str] = Field(default_factory=list)


class ScheduleItem(BaseModel):
    """分配好具体起止时间的日程条目，Task经过规划之后生成"""
    task_id: str
    task_name: str
    start_time: str
    end_time: str
    duration_min: int
    note: str = Field(default="")


class Plan(BaseModel):
    """完整的一份用户生成计划"""
    plan_id: str
    plan_name: str
    create_time: str
    source_user_input: str
    tasks: List[Task]
    schedule_items: List[ScheduleItem]
    plan_summary: str
    conflict_check_result: str
    modify_log: List[str] = Field(default_factory=list)


class AgentMessage(BaseModel):
    """Agent多轮对话消息结构体，用于保存对话上下文"""
    role: str
    content: str
    history_text: Optional[Dict] = None