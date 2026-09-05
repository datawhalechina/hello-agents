"""LLM服务模块"""

from hello_agents import HelloAgentsLLM
from ..config import get_settings

_llm_instance = None


def get_llm() -> HelloAgentsLLM:
    """获取LLM实例（单例模式）"""
    global _llm_instance

    if _llm_instance is None:
        _llm_instance = HelloAgentsLLM()
        print(f"[OK] LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")

    return _llm_instance
