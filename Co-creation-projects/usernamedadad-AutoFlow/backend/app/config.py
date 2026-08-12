import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


@dataclass
class Settings:
    app_name: str = "AutoFlow API"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "*"

    llm_model_id: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout: int = 60

    agent_max_steps: int = 6
    validator_max_retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "AutoFlow API"),
            app_env=os.getenv("APP_ENV", "dev"),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8000")),
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
            llm_model_id=os.getenv("LLM_MODEL_ID", ""),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_base_url=os.getenv("LLM_BASE_URL", ""),
            llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
            agent_max_steps=int(os.getenv("AGENT_MAX_STEPS", "6")),
            validator_max_retries=int(os.getenv("VALIDATOR_MAX_RETRIES", "2")),
        )


settings = Settings.from_env()
