from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os


@dataclass(slots=True)
class AppConfig:
    root_dir: Path
    sources_file: Path
    raw_dir: Path
    extracted_dir: Path
    translated_dir: Path
    digests_dir: Path
    state_dir: Path
    db_path: Path
    model_name: str
    translation_model_name: str
    api_key: str
    base_url: str
    fetch_full_translation: bool
    max_articles_per_run: int
    rss_fetch_concurrency: int
    rss_source_limit: int
    rss_entries_per_source: int
    rss_ai_batch_size: int
    rss_ai_max_concurrency: int
    rss_relevance_threshold: int
    rss_max_summary_articles_per_run: int
    rss_max_digest_articles: int
    request_timeout_seconds: int
    llm_timeout_seconds: int
    resummarize_existing: bool


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    loaded_values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        loaded_values[key.strip()] = value.strip()

    for key, value in loaded_values.items():
        os.environ[key] = value

    _apply_proxy_env(loaded_values)


def _apply_proxy_env(loaded_values: dict[str, str]) -> None:
    proxy_keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]
    proxy_url = loaded_values.get("PROXY_URL", "").strip()
    disable_system_proxy = loaded_values.get("DISABLE_SYSTEM_PROXY", "true").strip().lower() == "true"

    if proxy_url:
        for key in proxy_keys:
            os.environ[key] = proxy_url
        return

    explicit_proxy_in_env = any(loaded_values.get(key, "").strip() for key in proxy_keys)
    if explicit_proxy_in_env:
        return

    if disable_system_proxy:
        for key in proxy_keys:
            os.environ.pop(key, None)


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def build_config(root_dir: Path, data_root: Path | None = None) -> AppConfig:
    env_path = root_dir / ".env"
    load_env_file(env_path)

    if data_root is None:
        data_root = root_dir / "data"

    runs_dir = data_root / "runs"
    raw_dir = runs_dir / "raw"
    extracted_dir = runs_dir / "extracted"
    translated_dir = runs_dir / "translated"
    digests_dir = runs_dir / "digests"
    state_dir = data_root / "state"

    ensure_dirs([raw_dir, extracted_dir, translated_dir, digests_dir, state_dir])

    model_name = os.getenv("LLM_MODEL_ID", "").strip()
    translation_model_name = os.getenv("TRANSLATION_MODEL_ID", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1").strip().rstrip("/")
    fetch_full_translation = os.getenv("FETCH_FULL_TRANSLATION", "false").strip().lower() == "true"
    max_articles_per_run = int(os.getenv("RSS_MAX_NEW_ARTICLES_PER_RUN", os.getenv("MAX_ARTICLES_PER_RUN", "50")))
    request_timeout_seconds = int(os.getenv("RSS_FETCH_TIMEOUT_SECONDS", os.getenv("REQUEST_TIMEOUT_SECONDS", "15")))
    llm_timeout_seconds = int(os.getenv("LLM_TIMEOUT", "120"))
    rss_fetch_concurrency = int(os.getenv("RSS_FETCH_CONCURRENCY", "10"))
    rss_source_limit = int(os.getenv("RSS_SOURCE_LIMIT", "10"))
    rss_entries_per_source = int(os.getenv("RSS_ENTRIES_PER_SOURCE", "5"))
    rss_ai_batch_size = int(os.getenv("RSS_AI_BATCH_SIZE", "10"))
    rss_ai_max_concurrency = int(os.getenv("RSS_AI_MAX_CONCURRENCY", "2"))
    rss_relevance_threshold = int(os.getenv("RSS_RELEVANCE_THRESHOLD", "65"))
    rss_max_summary_articles_per_run = int(os.getenv("RSS_MAX_SUMMARY_ARTICLES_PER_RUN", "20"))
    rss_max_digest_articles = int(os.getenv("RSS_MAX_DIGEST_ARTICLES", "12"))
    resummarize_existing = os.getenv("RESUMMARIZE_EXISTING", "false").strip().lower() == "true"

    return AppConfig(
        root_dir=root_dir,
        sources_file=root_dir / "config" / "sources.json",
        raw_dir=raw_dir,
        extracted_dir=extracted_dir,
        translated_dir=translated_dir,
        digests_dir=digests_dir,
        state_dir=state_dir,
        db_path=state_dir / "articles.json",
        model_name=model_name,
        translation_model_name=translation_model_name,
        api_key=api_key,
        base_url=base_url,
        fetch_full_translation=fetch_full_translation,
        max_articles_per_run=max_articles_per_run,
        rss_fetch_concurrency=max(1, rss_fetch_concurrency),
        rss_source_limit=max(1, rss_source_limit),
        rss_entries_per_source=max(1, rss_entries_per_source),
        rss_ai_batch_size=max(1, rss_ai_batch_size),
        rss_ai_max_concurrency=max(1, rss_ai_max_concurrency),
        rss_relevance_threshold=max(0, min(100, rss_relevance_threshold)),
        rss_max_summary_articles_per_run=max(1, rss_max_summary_articles_per_run),
        rss_max_digest_articles=max(1, rss_max_digest_articles),
        request_timeout_seconds=request_timeout_seconds,
        llm_timeout_seconds=max(1, llm_timeout_seconds),
        resummarize_existing=resummarize_existing,
    )


def load_sources(sources_file: Path) -> list[dict[str, str]]:
    payload = json.loads(sources_file.read_text(encoding="utf-8"))
    return payload.get("sources", [])
