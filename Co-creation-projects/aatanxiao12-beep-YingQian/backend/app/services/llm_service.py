"""LLM 进程内单例（多智能体共享同一模型客户端，避免重复初始化）。"""

from hello_agents import HelloAgentsLLM

from ..utils.logger import get_logger

logger = get_logger("app.llm")

_llm_instance: HelloAgentsLLM | None = None


def get_llm() -> HelloAgentsLLM:
    """HelloAgentsLLM 自动读取 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID。"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = HelloAgentsLLM()
        logger.info(
            "LLM 初始化: provider=%s model=%s",
            getattr(_llm_instance, "provider", "?"),
            getattr(_llm_instance, "model", "?"),
        )
    return _llm_instance


def reset_llm() -> None:
    global _llm_instance
    _llm_instance = None
