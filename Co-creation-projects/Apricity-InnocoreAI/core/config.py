"""
InnoCore AI 核心配置模块
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    CLAUDE = "claude"
    MODELSCOPE = "modelscope"  # 阿里云 ModelScope
    OLLAMA = "ollama"  # 本地部署
    DASHSCOPE = "dashscope"  # 阿里云灵积（推荐用于 Qwen 系列）

class VectorDBType(Enum):
    """向量数据库类型枚举"""
    QDRANT = "qdrant"
    CHROMA = "chroma"
    PINECONE = "pinecone"

@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider = LLMProvider.OPENAI
    model_name: str = "gpt-5.6-terra"  # OpenAI: gpt-5.6-sol, gpt-5.6-terra
                                        # DashScope: qwen-turbo, qwen-plus, qwen-max
                                        # ModelScope: qwen/Qwen2.5-7B-Instruct
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60

@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    db_type: VectorDBType = VectorDBType.QDRANT
    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    collection_name_prefix: str = "innocore"
    embedding_model: str = "text-embedding-3-small"

@dataclass
class DatabaseConfig:
    """关系数据库配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "innocore_ai"
    username: str = "postgres"
    password: str = "password"
    pool_size: int = 10

@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 20

@dataclass
class ExternalAPIConfig:
    """外部API配置"""
    crossref_api_key: Optional[str] = None
    google_scholar_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    arxiv_base_url: str = "http://export.arxiv.org/api/query"
    ieee_base_url: str = "https://ieeexploreapi.ieee.org/api/v1"

@dataclass
class InnoCoreConfig:
    """InnoCore AI 主配置类"""
    
    # 基础配置
    app_name: str = "InnoCore AI"
    debug: bool = False
    log_level: str = "INFO"
    
    # LLM配置
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # 向量数据库配置
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    
    # 关系数据库配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # Redis配置
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # 外部API配置
    external_apis: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    
    # Agent配置
    agent_max_steps: int = 5
    agent_timeout: int = 300
    concurrent_agents: int = 4
    
    # RAG配置
    retrieval_top_k: int = 5
    similarity_threshold: float = 0.7
    hybrid_search_weights: Dict[str, float] = field(default_factory=lambda: {
        "vector": 0.7,
        "keyword": 0.3
    })
    
    # 性能配置
    cache_ttl: int = 3600  # 缓存过期时间(秒)
    batch_size: int = 10
    max_concurrent_requests: int = 50
    
    def __post_init__(self):
        """初始化后处理"""
        # 从环境变量加载配置
        self.llm.api_key = self.llm.api_key or os.getenv("OPENAI_API_KEY")
        self.llm.base_url = self.llm.base_url or os.getenv("OPENAI_BASE_URL")
        
        # 从环境变量加载模型名称（如果设置了）
        env_model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL")
        if env_model:
            self.llm.model_name = env_model
        
        self.database.password = self.database.password or os.getenv("DATABASE_PASSWORD")
        self.redis.password = self.redis.password or os.getenv("REDIS_PASSWORD")
        
        self.external_apis.crossref_api_key = self.external_apis.crossref_api_key or os.getenv("CROSSREF_API_KEY")
        self.external_apis.google_scholar_api_key = self.external_apis.google_scholar_api_key or os.getenv("GOOGLE_SCHOLAR_API_KEY")
        self.external_apis.serpapi_key = self.external_apis.serpapi_key or os.getenv("SERPAPI_KEY")
        
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

# 全局配置实例
config = InnoCoreConfig()

def get_config() -> InnoCoreConfig:
    """获取全局配置实例"""
    return config

def update_config(**kwargs) -> None:
    """更新配置"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)