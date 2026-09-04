import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    应用配置类，用于加载和管理环境变量。
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    # LLM 配置
    LLM_MODEL_ID: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_TIMEOUT: int = 100

    # 特定服务商的API Keys (用于自动检测)
    OPENAI_API_KEY: Optional[str] = None
    ZHIPU_API_KEY: Optional[str] = None
    MODELSCOPE_API_KEY: Optional[str] = None

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 日志级别
    LOG_LEVEL: str = "INFO"

    # Unsplash API
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    UNSPLASH_SECRET_KEY: Optional[str] = None

    # 高德地图 API
    AMAP_API_KEY: str

    # AMAP MCP Server
    AMAP_MCP_SERVER_URL: str = "http://127.0.0.1:8000"

    # JWT 认证配置
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_EXPIRY_HOURS: int = 24

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool = True

    # 密码加密配置
    BCRYPT_ROUNDS: int = 12

    # 向量数据库配置
    VECTOR_MEMORY_DIR: str = "vector_memory"
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_DIM: int = 384

    # HuggingFace 配置
    HF_ENDPOINT: str = "https://hf-mirror.com"
    HF_HUB_OFFLINE: bool = False
    HF_HUB_CACHE_DIR: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

# 创建一个全局可用的配置实例
settings = Settings()

# 注意：logger现在在observability.logger中统一管理
# 这里不再创建logger，避免重复初始化
