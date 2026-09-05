from hello_agents.core import HelloAgentsLLM
from ..config import get_settings

_llm_instance = None

def get_llm() -> HelloAgentsLLM:
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()

        _llm_instance = HelloAgentsLLM()

        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")

    return _llm_instance

def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None