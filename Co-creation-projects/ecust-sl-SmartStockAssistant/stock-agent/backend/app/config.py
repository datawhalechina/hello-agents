# backend/app/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    modelscope_api_key: str = ""
    modelscope_base_url: str = "https://api-inference.modelscope.cn/v1"
    qwen_model: str = "Qwen/Qwen3.5-35B-A3B"
    qwen_sentiment_model: str = "Qwen/Qwen3-235B-A22B"  # 情感分析：MoE 模型，实测 ~1.7s/次
    use_mock_data: bool = False
    tushare_token: str = ""
    polygon_api_key: str = ""
    news_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env", Path(".env")),
        extra="ignore",
    )


settings = Settings()
