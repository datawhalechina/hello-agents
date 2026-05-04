"""
LLM 配置 - 英语句子扩写智能体
"""
import os
import logging
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

load_dotenv()

logger = logging.getLogger(__name__)

def tool_listener(call_info):
    logger.info(f"Agent: {call_info['agent_name']}")
    logger.info(f"Tool: {call_info['tool_name']}")
    logger.info(f"Parameters: {call_info['parsed_parameters']}")
    logger.info(f"Result: {call_info['result']}")

# LLM 配置
class LLMConfig:
    """LLM 配置类"""
    
    # 从环境变量读取配置
    API_KEY = os.getenv("LLM_API_KEY", "")
    MODEL_ID = os.getenv("LLM_MODEL_ID", "")
    BASE_URL = os.getenv("LLM_BASE_URL", "")
    
    @classmethod
    def create_llm(cls) -> HelloAgentsLLM:
        """
        创建 LLM 实例
        
        Returns:
            HelloAgentsLLM: 配置好的 LLM 实例
        """
        return HelloAgentsLLM(
            api_key=cls.API_KEY,
            model_id=cls.MODEL_ID,
            base_url=cls.BASE_URL
        )


# 全局 LLM 实例（懒加载）
_llm_instance = None


def get_llm() -> HelloAgentsLLM:
    """
    获取全局 LLM 实例（单例模式）
    
    Returns:
        HelloAgentsLLM: LLM 实例
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMConfig.create_llm()
    return _llm_instance


def reset_llm():
    """重置 LLM 实例（用于测试或配置变更）"""
    global _llm_instance
    _llm_instance = None
