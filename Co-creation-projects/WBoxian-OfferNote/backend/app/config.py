"""本地模型配置：原子写入 .env，密钥只在服务端使用。"""

import os
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, Field, SecretStr, field_validator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_LOCK = threading.RLock()


class ModelConfigInput(BaseModel):
    base_url: str = Field(min_length=1, max_length=1000)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = None
    max_tokens: int = Field(default=12000, ge=1024, le=64000)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "请填写完整的 http/https API 基础地址，不包含密钥、查询参数或片段。"
            )
        if parsed.path.endswith(("/chat/completions", "/responses")):
            raise ValueError(
                "请填写 API 基础地址，不要附加 /chat/completions 或 /responses。"
            )
        return value

    @field_validator("model")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or any(c in value for c in "\r\n\x00"):
            raise ValueError("请填写有效模型 ID。")
        return value.strip()


def config_values():
    with CONFIG_LOCK:
        return {
            name: os.getenv("OFFERNOTE_" + name, "")
            for name in ("API_KEY", "BASE_URL", "MODEL", "MAX_TOKENS")
        }


def public_settings():
    values = config_values()
    return {
        "configured": all(values[k] for k in ("API_KEY", "BASE_URL", "MODEL")),
        "api_key_configured": bool(values["API_KEY"]),
        "base_url": values["BASE_URL"],
        "model": values["MODEL"],
        "max_tokens": int(values["MAX_TOKENS"] or 12000),
        "protocol": "OpenAI-compatible Chat Completions",
        "adapter": "HelloAgents 0.2.9 / FunctionCallAgent",
        "default_mode": "live",
    }


def save_config(body: ModelConfigInput, env_path: Path):
    with CONFIG_LOCK:
        values = config_values()
        key = body.api_key.get_secret_value().strip() if body.api_key else ""
        key = key or values["API_KEY"]
        if not key or any(c in key for c in "\r\n\x00"):
            raise ValueError("首次配置请填写有效 API Key。")
        updates = {
            "OFFERNOTE_API_KEY": key,
            "OFFERNOTE_BASE_URL": body.base_url,
            "OFFERNOTE_MODEL": body.model,
            "OFFERNOTE_MAX_TOKENS": str(body.max_tokens),
        }
        original = (
            env_path.read_text(encoding="utf-8-sig")
            if env_path.exists()
            else "# OpenAI 兼容 Chat Completions，模型需支持 tools / tool_calls。\n"
        )
        # 保留其他配置与注释；只替换指定模型字段。
        lines = []
        for line in original.splitlines():
            name = line.split("=", 1)[0].strip().removeprefix("export ").strip()
            if name not in updates:
                lines.append(line)

        def quote(value):
            return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

        text = (
            "\n".join(lines)
            + "\n"
            + "\n".join(f"{k}={quote(v)}" for k, v in updates.items())
            + "\n"
        )
        pending = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=env_path.parent,
                prefix=".env-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                pending = Path(handle.name)
                handle.write(text)
            # dotenv 插值关闭，密钥中的 ${...} 也应保留原值。
            parsed = dotenv_values(pending, interpolate=False)
            if any(parsed[k] != v for k, v in updates.items()):
                raise ValueError("配置写入校验失败。")
            pending.replace(env_path)
            os.environ.update(updates)
        finally:
            if pending is not None:
                pending.unlink(missing_ok=True)
        return public_settings()
