"""Explicit, local-first application configuration."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


ROOT = Path(os.environ.get("WORKFLOW_ROOT", Path(__file__).resolve().parents[2])).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKFLOW_", env_file=".env", extra="ignore")

    database_path: str = str(ROOT / "data" / "workflow.db")
    api_token: str = ""
    provider: str = "local-demo"
    external_llm_enabled: bool = False
    external_data_authorized: bool = False
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_batch_size: int = Field(default=5, ge=1, le=10)
    llm_thinking: bool = False
    feishu_sync_enabled: bool = False
    feishu_access_token: str = ""
    max_body_bytes: int = 10 * 1024 * 1024
