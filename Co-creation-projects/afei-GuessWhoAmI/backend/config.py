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
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "qwen-flash")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))

    # Tavily search API
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY", "")

    # ── Game config (code-level defaults, NOT stored in .env) ────────────────
    MAX_QUESTIONS: int = 10   # max questions per game
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