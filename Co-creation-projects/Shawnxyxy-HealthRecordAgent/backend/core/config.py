"""
HealthAgent 核心配置模块
"""

from dataclasses import dataclass, field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# ========== LLM ==========
@dataclass
class LLMConfig:
    model_name: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL_ID", "qwen-turbo")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL")
    )
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
# ========== Agent ==========
@dataclass
class AgentConfig:
    max_steps: int = 5
    timeout: int = 300
    history_limit: int = 50
# ========== RAG ==========
@dataclass
class RAGConfig:
    enabled: bool = field(
        default_factory=lambda: os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")
    )
    top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "5")))
    milvus_uri: str = field(default_factory=lambda: os.getenv("MILVUS_URI", "http://127.0.0.1:19530"))
    milvus_token: Optional[str] = field(default_factory=lambda: os.getenv("MILVUS_TOKEN"))
    milvus_collection: str = field(default_factory=lambda: os.getenv("MILVUS_COLLECTION", "health_memory_chunks"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-v1"))
    embedding_api_key: Optional[str] = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY"))
    embedding_base_url: Optional[str] = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL"))
    fallback_embedding_dim: int = field(default_factory=lambda: int(os.getenv("RAG_FALLBACK_EMBED_DIM", "64")))
# ========== App ==========
@dataclass
class AppConfig:
    app_name: str = "HealthRecordAgent"
    debug: bool = False
    log_level: str = "INFO"

# ========== Main ==========
@dataclass
class HealthAgentConfig:
    app: AppConfig = field(default_factory=AppConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)

# 全局配置
_config = HealthAgentConfig()


def get_config() -> HealthAgentConfig:
    return _config