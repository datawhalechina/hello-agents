"""第十六章：多角色历史辩论 + 轻量网络附录 + 终局综合。"""

from .config import create_llm
from .debate_orchestrator import run_historical_debate

__all__ = ["create_llm", "run_historical_debate"]
