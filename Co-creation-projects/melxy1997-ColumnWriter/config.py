"""配置管理模块"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    
    # LLM配置（支持多种命名方式）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_id: str = "gpt-5.6-sol"
    llm_timeout: int = 180
    
    # 兼容旧字段名
    openai_api_key: str = ""  # 兼容字段，会自动映射到 llm_api_key
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.6-sol"
    
    # 搜索 API 配置
    tavily_api_key: str = ""
    serpapi_api_key: str = ""
    
    # 系统配置
    max_depth: int = 3
    approval_threshold: int = 75  # 评审通过阈值（分数 >= 此值则通过）
    revision_threshold: int = 60  # 修改阈值（分数 < 此值则需要重写）
    enable_parallel: bool = False
    enable_search: bool = True  # 是否启用搜索功能
    enable_review: bool = True  # 是否启用评审功能（仅 ReAct 模式）
    max_revisions: int = 2  # 最大修改次数
    
    # 服务器配置（可选，用于 API 服务）
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = ""
    log_level: str = "INFO"
    
    # 其他服务配置（可选，忽略未使用的）
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""
    vite_api_base_url: str = ""
    amap_api_key: str = ""
    vite_amap_web_key: str = ""
    
    # 字数配置
    word_count_level_1: int = 600
    word_count_level_2: int = 400
    word_count_level_3: int = 200
    word_count_tolerance: float = 0.1
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略未定义的字段，避免验证错误


# 全局配置实例
_settings = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
        # 兼容处理：如果使用旧字段名，自动映射到新字段名
        if _settings.openai_api_key and not _settings.llm_api_key:
            _settings.llm_api_key = _settings.openai_api_key
        if _settings.openai_base_url and _settings.llm_base_url == "https://api.openai.com/v1":
            _settings.llm_base_url = _settings.openai_base_url
        if _settings.openai_model and _settings.llm_model_id == "gpt-5.6-sol":
            _settings.llm_model_id = _settings.openai_model
    return _settings


def get_word_count(level: int) -> int:
    """获取指定层级的目标字数"""
    settings = get_settings()
    word_counts = {
        1: settings.word_count_level_1,
        2: settings.word_count_level_2,
        3: settings.word_count_level_3
    }
    return word_counts.get(level, 400)

