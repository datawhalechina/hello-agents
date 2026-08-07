from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"
if load_dotenv and ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)


for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    proxy_value = os.getenv(proxy_key, "")
    if proxy_value in {"http://127.0.0.1:9", "https://127.0.0.1:9"}:
        os.environ.pop(proxy_key, None)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def _path_env(name: str, default: Path) -> str:
    value = os.getenv(name)
    path = Path(value) if value else default
    if not path.is_absolute():
        path = ROOT_DIR / path
    return str(path.resolve())


def _chapter14_backend_default() -> Path:
    chapter14_root = ROOT_DIR.parents[1] / "chapter14"
    candidates = [
        ROOT_DIR / "agents" / "deep_research" / "src",
        chapter14_root / "helloagents-deepresearch" / "backend" / "src",
        chapter14_root / "helloagents-deepresearch-fixed" / "backend" / "src",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Agent Platform Base")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8016"))
    chapter14_backend_path: str = _path_env("CHAPTER14_BACKEND_PATH", _chapter14_backend_default())

    llm_provider: str | None = os.getenv("LLM_PROVIDER") or None
    llm_model_id: str | None = os.getenv("LLM_MODEL_ID") or None
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None
    llm_timeout: str | None = os.getenv("LLM_TIMEOUT") or None

    search_api: str | None = os.getenv("SEARCH_API") or None
    max_web_research_loops: str | None = os.getenv("MAX_WEB_RESEARCH_LOOPS") or None
    fetch_full_page: str | None = os.getenv("FETCH_FULL_PAGE") or None
    enable_notes: str | None = os.getenv("ENABLE_NOTES") or None
    persist_runs: str | None = os.getenv("PERSIST_RUNS") or None
    cleanup_intermediate_files: str | None = os.getenv("CLEANUP_INTERMEDIATE_FILES") or None
    notes_workspace: str = os.getenv(
        "NOTES_WORKSPACE",
        str((ROOT_DIR / "data" / "deep_research" / "notes").resolve()),
    )
    run_workspace: str = os.getenv(
        "RUN_WORKSPACE",
        str((ROOT_DIR / "data" / "deep_research" / "runs").resolve()),
    )
    rss_digest_root: str = os.getenv(
        "RSS_DIGEST_ROOT",
        str((ROOT_DIR / "agents" / "rss_digest").resolve()),
    )
    rss_digest_data_root: str = os.getenv(
        "RSS_DIGEST_DATA_ROOT",
        str((ROOT_DIR / "data" / "rss_digest").resolve()),
    )
    maintenance_cleanup_enabled: bool = _bool_env("MAINTENANCE_CLEANUP_ENABLED", True)
    maintenance_cleanup_interval_hours: int = _int_env("MAINTENANCE_CLEANUP_INTERVAL_HOURS", 6)
    research_run_retention_days: int = _int_env("RESEARCH_RUN_RETENTION_DAYS", 7)
    rss_digest_retention_days: int = _int_env("RSS_DIGEST_RETENTION_DAYS", 7)
    rss_cache_retention_days: int = _int_env("RSS_CACHE_RETENTION_DAYS", 7)


settings = Settings()
