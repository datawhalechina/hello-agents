"""应用配置。

配置来源优先级：**进程环境变量 > 项目根目录 `.env` 文件 > 代码默认值**。
所有配置集中在本模块，业务代码通过 :func:`get_settings` 获取单例配置。

设计说明：
    - 缺少 API Key 时 *不* 在导入阶段抛错，保证离线单测与前端静态页可用；
    - 真正需要调用模型时由 :meth:`Settings.require_llm_config` 显式校验。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .errors import LLMNotConfiguredError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

_PLACEHOLDER_KEYS = {"your-api-key-here", "sk-***", "changeme", "none"}


def _env_bool(name: str, default: bool) -> bool:
    """读取布尔型环境变量，非法值回退到默认值。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """读取整型环境变量，非法值回退到默认值。"""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """读取浮点型环境变量，非法值回退到默认值。"""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_path(name: str, default: Path) -> Path:
    """读取路径型环境变量，相对路径按项目根目录解析。"""
    raw = os.getenv(name)
    path = Path(raw).expanduser() if raw else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


class Settings(BaseModel):
    """运行期配置。

    Attributes:
        llm_model_id: 模型名称，例如 ``deepseek-chat``。
        llm_api_key: API 密钥，仅从环境变量读取，不写入日志。
        llm_base_url: OpenAI 兼容端点。
        llm_timeout: 单次 LLM 调用超时（秒）。
        writer_temperature: 写作温度。
        reviewer_temperature: 审稿温度，默认 0 以保证评分稳定。
        approve_score: 通过分数线。
        min_relevance_score: 相关性维度的最低通过分。
        max_rounds_default: 默认最大修订轮次。
        output_dir: 运行结果落盘目录。
        frontend_dir: 前端单页所在目录。
        data_dir: 示例数据目录。
        host: Web 服务监听地址。
        port: Web 服务端口。
        cors_origins: 允许跨域的前端来源。
        cleanup_keep_runs: 保留的最近运行数量。
        log_level: 日志级别。
    """

    llm_model_id: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout: int = Field(default=180, ge=10, le=600)
    writer_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    reviewer_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    approve_score: int = Field(default=80, ge=0, le=100)
    min_relevance_score: int = Field(default=80, ge=0, le=100)
    max_rounds_default: int = Field(default=2, ge=0, le=3)
    output_dir: Path = PROJECT_ROOT / "outputs"
    frontend_dir: Path = PROJECT_ROOT / "frontend"
    data_dir: Path = PROJECT_ROOT / "data"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    cleanup_keep_runs: int = Field(default=50, ge=1, le=10000)
    trace_enabled: bool = True
    log_level: str = "INFO"

    @property
    def llm_configured(self) -> bool:
        """是否已配置完整的 LLM 连接信息。"""
        key = (self.llm_api_key or "").strip()
        return bool(
            (self.llm_model_id or "").strip()
            and key
            and key.lower() not in _PLACEHOLDER_KEYS
            and (self.llm_base_url or "").strip()
        )

    def require_llm_config(self) -> None:
        """校验 LLM 配置，缺失时抛出可读异常。

        Raises:
            LLMNotConfiguredError: 模型名、API Key 或 Base URL 任一缺失。
        """
        if self.llm_configured:
            return
        missing = []
        if not (self.llm_model_id or "").strip():
            missing.append("LLM_MODEL_ID")
        if not (self.llm_api_key or "").strip() or self.llm_api_key.lower() in _PLACEHOLDER_KEYS:
            missing.append("LLM_API_KEY")
        if not (self.llm_base_url or "").strip():
            missing.append("LLM_BASE_URL")
        raise LLMNotConfiguredError(
            "尚未配置 LLM，请在 .env 中填写：" + "、".join(missing)
        )

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构造配置对象。"""
        cors_raw = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
        cors_origins = [item.strip() for item in cors_raw.split(",") if item.strip()]
        return cls(
            llm_model_id=os.getenv("LLM_MODEL_ID", "").strip(),
            llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
            llm_base_url=os.getenv("LLM_BASE_URL", "").strip(),
            llm_timeout=_env_int("LLM_TIMEOUT", 180),
            writer_temperature=_env_float("LLM_TEMPERATURE_WRITER", 0.8),
            reviewer_temperature=_env_float("LLM_TEMPERATURE_REVIEWER", 0.0),
            approve_score=_env_int("APPROVE_SCORE", 80),
            min_relevance_score=_env_int("MIN_RELEVANCE_SCORE", 80),
            max_rounds_default=_env_int("MAX_ROUNDS_DEFAULT", 2),
            output_dir=_env_path("OUTPUT_DIR", PROJECT_ROOT / "outputs"),
            frontend_dir=_env_path("FRONTEND_DIR", PROJECT_ROOT / "frontend"),
            data_dir=_env_path("DATA_DIR", PROJECT_ROOT / "data"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=_env_int("PORT", 8000),
            cors_origins=cors_origins or ["http://localhost:5173"],
            cleanup_keep_runs=_env_int("CLEANUP_KEEP_RUNS", 50),
            trace_enabled=_env_bool("TRACE_ENABLED", True),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取进程内缓存的配置单例。"""
    return Settings.from_env()


def reset_settings_cache() -> None:
    """清空配置缓存（测试或运行期修改环境变量后调用）。"""
    get_settings.cache_clear()
