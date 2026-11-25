"""Local configuration. Secrets stay server-side and are never returned to the UI."""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent


class AppError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def load_env(path: Path) -> None:
    """Read simple KEY=value entries; existing process variables take priority."""
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass
class Settings:
    model: str = ""
    base_url: str = "https://api.openai.com/v1"
    api_key: str = field(default="", repr=False)
    search_key: str = field(default="", repr=False)
    timeout: int = 90

    @classmethod
    def from_env(cls) -> "Settings":
        load_env(ROOT / ".env")
        try:
            timeout = int(os.getenv("LLM_TIMEOUT", "90"))
        except ValueError:
            timeout = 90
        return cls(os.getenv("LLM_MODEL_ID", ""), os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                   os.getenv("LLM_API_KEY", ""), os.getenv("TAVILY_API_KEY", ""), max(10, min(timeout, 180)))

    def validate(self) -> None:
        if not self.model.strip() or not self.api_key.strip():
            raise AppError("请先在连接设置中填写模型名称和 API Key。", 503)
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            raise AppError("模型地址需要是有效的 HTTP / HTTPS 地址，且不能在地址里包含密码。")

    def public(self) -> dict:
        installed = importlib.util.find_spec("hello_agents") is not None
        return {"model": self.model, "base_url": self.base_url,
                "llm_configured": bool(self.model and self.api_key), "search_configured": bool(self.search_key),
                "framework_installed": installed, "ready": bool(installed and self.model and self.api_key)}
