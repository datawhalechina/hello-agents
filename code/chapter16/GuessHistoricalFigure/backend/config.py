"""Application configuration"""

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file at module import time
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


class Settings:
    """Application settings"""

    # ── Third-party service config (loaded from .env) ────────────────────────

    # LLM (ModelScope / OpenAI-compatible)
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "ZhipuAI/GLM-5")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/")

    # Qdrant vector database
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "hello_agents_vectors")
    QDRANT_VECTOR_SIZE: int = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
    QDRANT_DISTANCE: str = os.getenv("QDRANT_DISTANCE", "cosine")
    QDRANT_TIMEOUT: int = int(os.getenv("QDRANT_TIMEOUT", "30"))

    # Neo4j graph database
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: Optional[str] = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    NEO4J_MAX_CONNECTION_LIFETIME: int = int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600"))
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50"))
    NEO4J_CONNECTION_TIMEOUT: int = int(os.getenv("NEO4J_CONNECTION_TIMEOUT", "60"))

    # Embedding model
    EMBED_MODEL_TYPE: str = os.getenv("EMBED_MODEL_TYPE", "local")
    EMBED_MODEL_NAME: str = os.getenv("EMBED_MODEL_NAME", "")
    EMBED_API_KEY: Optional[str] = os.getenv("EMBED_API_KEY", "")
    EMBED_BASE_URL: str = os.getenv("EMBED_BASE_URL", "")

    # Tavily search API
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY", "")

    # ── Game config (code-level defaults, NOT stored in .env) ────────────────
    MAX_QUESTIONS: int = 20   # max questions per game
    MAX_HINTS: int = 3        # max hints per game

    # ── Server config (code-level defaults, NOT stored in .env) ─────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @classmethod
    def validate(cls):
        """Validate critical config values"""
        if not cls.LLM_API_KEY:
            print("⚠️  Warning: LLM_API_KEY is not set")
            print("   Please configure LLM_API_KEY in the .env file")
            return False
        print(f"✅ LLM config:")
        print(f"   Model   : {cls.LLM_MODEL_ID}")
        print(f"   Base URL: {cls.LLM_BASE_URL}")
        return True

_settings_instance: Optional[Settings] = None


def get_config() -> Settings:
    """Return the singleton application settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance