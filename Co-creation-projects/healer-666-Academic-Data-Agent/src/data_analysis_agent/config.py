"""Runtime configuration and tokenizer compatibility helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tiktoken
from dotenv import load_dotenv


_TOKEN_PATCH_APPLIED = False
_SAFE_TIKTOKEN_MODEL_PREFIXES = (
    "gpt-3.5",
    "gpt-4",
    "text-embedding-3",
    "text-embedding-ada",
)


@dataclass(frozen=True)
class RuntimeConfig:
    model_id: str
    api_key: str
    base_url: str
    timeout: int = 120
    tavily_api_key: Optional[str] = None
    vision_model_id: Optional[str] = None
    vision_api_key: Optional[str] = None
    vision_base_url: Optional[str] = None
    vision_timeout: int = 120

    @property
    def vision_configured(self) -> bool:
        return bool(self.vision_model_id and self.vision_api_key and self.vision_base_url)


def _patched_get_encoding(self):
    model_name = str(getattr(self, "model", "") or "").strip().lower()

    try:
        if model_name and any(model_name.startswith(prefix) for prefix in _SAFE_TIKTOKEN_MODEL_PREFIXES):
            return tiktoken.encoding_for_model(model_name)
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def apply_token_counter_patch():
    """Apply a generic OpenAI-compatible tokenizer fallback patch once."""

    global _TOKEN_PATCH_APPLIED
    if _TOKEN_PATCH_APPLIED:
        return _patched_get_encoding

    try:
        import hello_agents.context.token_counter
    except ModuleNotFoundError:
        _TOKEN_PATCH_APPLIED = True
        return _patched_get_encoding

    hello_agents.context.token_counter.TokenCounter._get_encoding = _patched_get_encoding
    _TOKEN_PATCH_APPLIED = True
    return _patched_get_encoding


def load_runtime_config(env_file: Optional[str | Path] = None) -> RuntimeConfig:
    """Load and validate runtime configuration from the environment."""

    if env_file is not None:
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)

    required_env_vars = ("LLM_MODEL_ID", "LLM_BASE_URL", "LLM_API_KEY")
    missing_env_vars = [name for name in required_env_vars if not os.getenv(name)]
    if missing_env_vars:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing_env_vars)
            + ". Create a .env file from .env.example or export them before running the project."
        )

    timeout = int(os.getenv("LLM_TIMEOUT", "120"))
    vision_timeout = int(os.getenv("VISION_LLM_TIMEOUT", str(timeout)))
    config = RuntimeConfig(
        model_id=os.environ["LLM_MODEL_ID"],
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ["LLM_BASE_URL"],
        timeout=timeout,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        vision_model_id=os.getenv("VISION_LLM_MODEL_ID"),
        vision_api_key=os.getenv("VISION_LLM_API_KEY"),
        vision_base_url=os.getenv("VISION_LLM_BASE_URL"),
        vision_timeout=vision_timeout,
    )

    os.environ.setdefault("LLM_TIMEOUT", str(config.timeout))
    apply_token_counter_patch()
    return config
