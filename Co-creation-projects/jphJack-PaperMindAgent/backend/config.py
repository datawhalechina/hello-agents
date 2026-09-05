"""全局配置：从 .env 读取"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)


class Settings:
    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Embedding：默认使用本地已下载的 bge-large-zh-v1.5
    # 如需使用其他模型，在 .env 中覆盖 EMBEDDING_MODEL
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")

    # 路径
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CHROMA_PATH: Path = Path(os.getenv("CHROMA_PATH", "./data/chroma"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "./data/cache"))
    REPORT_DIR: Path = Path(os.getenv("REPORT_DIR", "./data/reports"))
    UPLOADS_DIR: Path = Path(os.getenv("UPLOADS_DIR", "./data/uploads"))

    # 超时与重试
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
    PDF_PARSE_TIMEOUT: int = int(os.getenv("PDF_PARSE_TIMEOUT", "60"))
    TOOL_MAX_RETRIES: int = int(os.getenv("TOOL_MAX_RETRIES", "3"))

    # Reflexion
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    # 并发
    MAX_CONCURRENT_PAPERS: int = int(os.getenv("MAX_CONCURRENT_PAPERS", "5"))

    # 联网搜索
    WEB_SEARCH_BACKEND: str = os.getenv("WEB_SEARCH_BACKEND", "duckduckgo")

    def ensure_dirs(self):
        for d in (self.CHROMA_PATH, self.CACHE_DIR, self.REPORT_DIR, self.UPLOADS_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.CHROMA_PATH = settings.BASE_DIR / settings.CHROMA_PATH if not settings.CHROMA_PATH.is_absolute() else settings.CHROMA_PATH
settings.CACHE_DIR = settings.BASE_DIR / settings.CACHE_DIR if not settings.CACHE_DIR.is_absolute() else settings.CACHE_DIR
settings.REPORT_DIR = settings.BASE_DIR / settings.REPORT_DIR if not settings.REPORT_DIR.is_absolute() else settings.REPORT_DIR
settings.UPLOADS_DIR = settings.BASE_DIR / settings.UPLOADS_DIR if not settings.UPLOADS_DIR.is_absolute() else settings.UPLOADS_DIR
settings.ensure_dirs()
