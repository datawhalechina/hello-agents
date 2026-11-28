"""Wellness Assistant 的 ReAct 智能体装配。"""

from __future__ import annotations

import threading

from hello_agents import Config, ReActAgent, ToolRegistry

from app.agent.llm_provider import build_llm
from app.agent.tools import build_tools
from app.core.config import settings

SYSTEM_PROMPT = f"""你是 Wellness Assistant Agent，一个面向个人健康管理的智能体。

## 可用能力
- get_health_context：获取用户画像、近期健康记录、长期记忆与当前运动计划
- record_health_metric / query_health_records / get_health_trends：记录与查询健康指标
- save_user_profile：保存基础信息、健康目标与运动限制
- generate_exercise_plan / adjust_exercise_plan / list_plan_versions：生成与动态调整运动计划
- add_health_memory / deactivate_health_memory：维护长期记忆
- generate_health_review：生成周期性健康复盘

## 工作规则
1. 先用 Thought 记录推理，再选择合适的工具，最后用 Finish 给出最终答案。
2. 记录健康数据前必须确认指标类型与数值；缺失数值、单位或明显异常时向用户追问，不要猜测。
3. 生成或调整运动计划必须调用对应工具，不要自行编造未持久化的计划。
4. 用户反馈疼痛、头晕、胸闷、明显不适或受伤时，优先降低训练强度，并建议停止训练、咨询专业人士。
5. 长期记忆只保存用户明确表述的事实，不保存推测内容。
6. 你不是医生，禁止给出诊断、处方或治疗结论；所有建议均为一般性健康提示。
7. 每次最终回复末尾必须附上免责声明：{settings.disclaimer}

## 回复风格
使用简洁中文，说明你完成了什么操作、数据变化与后续建议；工具失败时如实告知原因。
"""

_agent: ReActAgent | None = None
_agent_lock = threading.Lock()


def build_agent() -> ReActAgent:
    """构造带全部业务工具的 ReAct Agent。"""
    config = Config(
        trace_enabled=False,
        skills_enabled=False,
        session_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
        subagent_enabled=False,
        async_enabled=False,
        stream_enabled=False,
    )
    registry = ToolRegistry()
    for tool in build_tools():
        registry.register_tool(tool)
    return ReActAgent(
        name="WellnessAssistant",
        llm=build_llm(),
        tool_registry=registry,
        system_prompt=SYSTEM_PROMPT,
        config=config,
        max_steps=settings.agent_max_steps,
    )


def get_agent() -> ReActAgent:
    """进程内复用 Agent 实例，避免重复装配工具。"""
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                _agent = build_agent()
    return _agent
