"""配置管理"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    app_name: str = "Way_to_Engineer"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 12000
    
    # CORS配置
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_model_id: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    
    # 日志配置
    log_level: str = "INFO"
    
    # LLM配置
    llm_timeout: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"
        
    def get_cors_origins_list(self) -> list[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
# 创建全局配置实例
settings = Settings()

# 获取全局配置实例
def get_settings() -> Settings:
    return settings

def validate_config():
    """验证配置"""
    warnings = []
    
    llm_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not llm_api_key:
        warnings.append("LLM API Key未设置，将无法使用LLM功能")
        
    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")
    
    return True

def print_config():
    """打印配置"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"服务器: {settings.host}:{settings.port}")

    # 检查LLM配置
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or settings.deepseek_base_url
    llm_model = os.getenv("LLM_MODEL_ID") or os.getenv("DEEPSEEK_MODEL_ID")

    print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    print(f"LLM Base URL: {llm_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"日志级别: {settings.log_level}")
    
if __name__ == "__main__":
    print_config()
