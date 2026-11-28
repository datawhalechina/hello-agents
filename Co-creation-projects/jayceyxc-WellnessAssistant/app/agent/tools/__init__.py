"""可被 ReAct Agent 调用的业务工具。"""

from app.agent.tools.health_tools import build_health_tools
from app.agent.tools.memory_tools import build_memory_tools
from app.agent.tools.plan_tools import build_plan_tools
from app.agent.tools.review_tools import build_review_tools


def build_tools():
    """注册式装配全部业务工具。"""
    return [
        *build_health_tools(),
        *build_plan_tools(),
        *build_memory_tools(),
        *build_review_tools(),
    ]


__all__ = ["build_tools"]
