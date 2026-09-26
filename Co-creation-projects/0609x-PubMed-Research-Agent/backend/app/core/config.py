"""Application configuration loaded from environment (.env).

Uses pydantic-settings. Every external service credential is read here
so that services/ and agents/ never touch os.environ directly.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: backend/app/core/config.py -> repo root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "PubMed-Research-Agent"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    log_format: str = "text"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    cors_allow_credentials: bool = False
    trusted_hosts: str = "*"
    enable_api_docs: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/pubmed_agent.db"

    # Background jobs
    redis_url: str = "redis://localhost:6379/0"
    redis_socket_connect_timeout: float = 2.0
    redis_socket_timeout: float = 5.0
    celery_task_time_limit: int = 1800
    celery_task_soft_time_limit: int = 1740
    search_job_stale_after_seconds: int = Field(default=2100, ge=300)

    # Shared LLM/query cache
    prompt_cache_backend: str = "redis"
    prompt_cache_redis_url: str = "redis://localhost:6379/1"
    prompt_cache_ttl_hours: int = 24
    prompt_cache_namespace: str = "pubmed-agent:prompt-cache"
    prompt_cache_lock_timeout: int = 300
    prompt_cache_lock_wait_timeout: int = 30

    # PubMed
    pubmed_api_key: str = ""
    pubmed_email: str = "your_email@example.com"
    pubmed_tool_name: str = "PubMed-Research-Agent"
    pubmed_verify_ssl: bool = True

    # LLM (OpenAI compatible)
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_timeout: float = 240.0

    # Embedding (DashScope / Alibaba Cloud)
    embed_model_type: str = "dashscope"
    embed_model_name: str = "text-embedding-v3"
    embed_api_key: str = ""
    embed_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Neo4j Aura
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Feature switches
    neo4j_enabled: bool = True
    tavily_enabled: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.search_job_stale_after_seconds <= self.celery_task_time_limit:
            raise ValueError(
                "SEARCH_JOB_STALE_AFTER_SECONDS must exceed CELERY_TASK_TIME_LIMIT"
            )
        if not self.is_production:
            return self
        errors = []
        if self.debug:
            errors.append("DEBUG must be false")
        if self.database_url.startswith("sqlite"):
            errors.append("DATABASE_URL must use PostgreSQL")
        if "pubmed_agent_change_me" in self.database_url:
            errors.append("the default PostgreSQL password must be replaced")
        if "*" in self.cors_origin_list:
            errors.append("CORS_ORIGINS cannot contain '*'")
        if not self.cors_origin_list:
            errors.append("CORS_ORIGINS must list at least one production origin")
        if not self.trusted_host_list or "*" in self.trusted_host_list:
            errors.append("TRUSTED_HOSTS must list explicit production hosts")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @property
    def llm_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }


settings = Settings()
