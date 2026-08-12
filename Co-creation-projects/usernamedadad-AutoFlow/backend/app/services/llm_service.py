from hello_agents import HelloAgentsLLM
from app.config import settings


class LLMService:
    @staticmethod
    def create_llm() -> HelloAgentsLLM:
        return HelloAgentsLLM(
            model=settings.llm_model_id,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout,
            temperature=0.3,
        )
