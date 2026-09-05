from typing import Optional
import os

# 处理pydantic v2兼容性
try:
    from pydantic import BaseSettings
except ImportError:
    # pydantic v2需要安装pydantic-settings
    try:
        from pydantic_settings import BaseSettings
    except ImportError:
        # 如果都没有，使用普通类
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

class Settings(BaseSettings):
    # AI模型配置
    openai_api_key: str
    base_url: Optional[str] = None
    model_name: str = "qwen3-max"
    temperature: float = 0.7
    max_tokens: int = 1000

    # 缓存配置
    cache_enabled: bool = True
    cache_expire_seconds: int = 3600

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # 其他配置
    max_generation_attempts: int = 3
    default_generation_type: str = "novel"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # 允许额外的字段
    model_config = {
        "extra": "allow"
    }

# 全局设置实例
settings = Settings()