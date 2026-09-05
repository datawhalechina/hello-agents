"""Application configuration loaded from environment (.env).

Uses pydantic-settings. Every external service credential is read here
so that services/ and agents/ never touch os.environ directly.
"""

from __future__ import annotations

from pathlib import Path

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
    debug: bool = True
    log_level: str = "INFO"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/pubmed_agent.db"

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

    # Qdrant Cloud
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "pubmed_articles"

    # Neo4j Aura
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Feature switches
    vector_store_enabled: bool = True
    neo4j_enabled: bool = True
    tavily_enabled: bool = False

    @property
    def llm_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }


settings = Settings()
