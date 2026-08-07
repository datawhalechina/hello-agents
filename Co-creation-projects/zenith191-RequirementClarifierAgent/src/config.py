"""LLM 配置读取与校验。"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """配置缺失或配置值无效。"""


def _read_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} 必须是数字") from exc


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} 必须是整数") from exc


@dataclass(frozen=True)
class LLMSettings:
    """创建 HelloAgentsLLM 所需的显式配置。"""

    model: str
    api_key: str
    base_url: str
    temperature: float = 0.2
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "LLMSettings":
        """从 HelloAgents 官方环境变量读取配置并完成校验。"""

        settings = cls(
            model=os.getenv("LLM_MODEL_ID", "").strip(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            base_url=os.getenv("LLM_BASE_URL", "").strip(),
            temperature=_read_float("LLM_TEMPERATURE", 0.2),
            timeout=_read_int("LLM_TIMEOUT", 120),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """拒绝缺失、占位符或越界配置。"""

        missing = [
            name
            for name, value in (
                ("LLM_MODEL_ID", self.model),
                ("LLM_API_KEY", self.api_key),
                ("LLM_BASE_URL", self.base_url),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "缺少 LLM 配置：" + ", ".join(missing) + "。请先复制并填写 .env。"
            )

        lowered_key = self.api_key.casefold()
        if lowered_key.startswith("your_") or lowered_key in {"changeme", "replace_me"}:
            raise ConfigurationError("LLM_API_KEY 仍是占位符，请在 .env 中填写真实密钥")
        if not 0 <= self.temperature <= 2:
            raise ConfigurationError("LLM_TEMPERATURE 必须位于 0 到 2 之间")
        if self.timeout <= 0:
            raise ConfigurationError("LLM_TIMEOUT 必须大于 0")
