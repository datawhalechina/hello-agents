"""应用配置：统一从 .env 与环境变量读取。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DISCLAIMER = (
    "以上内容仅供参考，不构成医疗诊断或治疗建议，不能替代专业医师诊疗；"
    "如出现疼痛或明显不适，请暂停训练并咨询专业人士。"
)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_bool(name: str, default: str = "true") -> bool:
    return _env(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """运行期配置，API Key 只从环境变量读取。"""

    app_name: str = "Wellness Assistant Agent"
    host: str = Field(default_factory=lambda: _env("APP_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(_env("APP_PORT", "8000")))
    debug: bool = Field(default_factory=lambda: _env_bool("APP_DEBUG", "false"))
    database_url: str = Field(
        default_factory=lambda: _env("DATABASE_URL", "sqlite:///./wellness.db")
    )

    llm_provider: str = Field(default_factory=lambda: _env("LLM_PROVIDER", "ollama"))
    llm_model_id: str = Field(default_factory=lambda: _env("LLM_MODEL_ID", "qwen2.5:7b"))
    llm_api_key: str = Field(default_factory=lambda: _env("LLM_API_KEY", "ollama"))
    llm_base_url: str = Field(
        default_factory=lambda: _env("LLM_BASE_URL", "http://localhost:11434/v1")
    )
    llm_timeout: int = Field(default_factory=lambda: int(_env("LLM_TIMEOUT", "60")))
    llm_temperature: float = Field(
        default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.3"))
    )

    agent_max_steps: int = Field(
        default_factory=lambda: int(_env("AGENT_MAX_STEPS", "8"))
    )
    trace_enabled: bool = Field(
        default_factory=lambda: _env_bool("TRACE_ENABLED", "true")
    )
    disclaimer: str = DISCLAIMER


settings = Settings()
