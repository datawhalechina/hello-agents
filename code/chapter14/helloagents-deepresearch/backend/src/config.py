import os
from pathlib import Path
from enum import Enum
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()


class SearchAPI(Enum):
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    SEARXNG = "searxng"
    ADVANCED = "advanced"


class Configuration(BaseModel):
    """Configuration options for the deep research assistant."""

    max_web_research_loops: int = Field(
        default=3,
        title="Research Depth",
        description="Number of research iterations to perform",
    )
    local_llm: str = Field(
        default="llama3.2",
        title="Local Model Name",
        description="Name of the locally hosted LLM (Ollama/LMStudio)",
    )
    llm_provider: str = Field(
        default="ollama",
        title="LLM Provider",
        description="Provider identifier (ollama, lmstudio, or custom)",
    )
    search_api: SearchAPI = Field(
        default=SearchAPI.DUCKDUCKGO,
        title="Search API",
        description="Web search API to use",
    )
    enable_notes: bool = Field(
        default=True,
        title="Enable Notes",
        description="Whether to store task progress in NoteTool",
    )
    notes_workspace: str = Field(
        default="./notes",
        title="Notes Workspace",
        description="Directory for NoteTool to persist task notes",
    )
    fetch_full_page: bool = Field(
        default=False,
        title="Fetch Full Page",
        description="Include the full page content in the search results",
    )
    task_concurrency: int = Field(
        default=1,
        title="Task Concurrency",
        description="Maximum number of research tasks to execute concurrently",
    )
    cors_allow_origins: str = Field(
        default=(
            "http://localhost:5173,http://localhost:5174,"
            "http://127.0.0.1:5173,http://127.0.0.1:5174"
        ),
        title="CORS Allow Origins",
        description="Comma-separated list of allowed browser origins",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        title="Ollama Base URL",
        description="Base URL for Ollama API (without /v1 suffix)",
    )
    lmstudio_base_url: str = Field(
        default="http://localhost:1234/v1",
        title="LMStudio Base URL",
        description="Base URL for LMStudio OpenAI-compatible API",
    )
    strip_thinking_tokens: bool = Field(
        default=True,
        title="Strip Thinking Tokens",
        description="Whether to strip <think> tokens from model responses",
    )
    use_tool_calling: bool = Field(
        default=False,
        title="Use Tool Calling",
        description="Use tool calling instead of JSON mode for structured output",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        title="LLM API Key",
        description="Optional API key when using custom OpenAI-compatible services",
    )
    llm_base_url: Optional[str] = Field(
        default=None,
        title="LLM Base URL",
        description="Optional base URL when using custom OpenAI-compatible services",
    )
    llm_model_id: Optional[str] = Field(
        default=None,
        title="LLM Model ID",
        description="Optional model identifier for custom OpenAI-compatible services",
    )
    llm_timeout: int = Field(
        default=60,
        title="LLM Timeout",
        description="Timeout in seconds for LLM requests",
    )
    llm_retry_attempts: int = Field(
        default=2,
        title="LLM Retry Attempts",
        description="Number of retries for LLM rate limit errors",
    )
    llm_retry_base_delay: float = Field(
        default=5.0,
        title="LLM Retry Base Delay",
        description="Base retry delay in seconds for LLM rate limits",
    )
    llm_retry_max_delay: float = Field(
        default=20.0,
        title="LLM Retry Max Delay",
        description="Maximum retry delay in seconds for LLM rate limits",
    )
    llm_min_interval_seconds: float = Field(
        default=2.0,
        title="LLM Min Interval",
        description="Minimum interval between process-local LLM calls",
    )
    llm_mode: str = Field(
        default="real",
        title="LLM Mode",
        description="LLM execution mode: real or fake",
    )
    llm_cache_enabled: bool = Field(
        default=False,
        title="LLM Cache Enabled",
        description="Legacy switch that enables read-write LLM caching",
    )
    llm_cache_mode: Literal["off", "read_only", "read_write"] = Field(
        default="off",
        title="LLM Cache Mode",
        description="LLM response cache mode: off, read_only, or read_write",
    )
    llm_cache_dir: str = Field(
        default=".llm_cache",
        title="LLM Cache Directory",
        description="Directory for local LLM response cache JSON files",
    )
    max_agent_steps: int = Field(
        default=3,
        title="Max Agent Steps",
        description="Maximum number of research tasks to execute; 0 disables the limit",
    )
    dry_run_skip_search: bool = Field(
        default=True,
        title="Dry Run Skip Search",
        description="Whether dry-run mode should avoid real search backends",
    )
    llm_run_log_dir: str = Field(
        default="logs",
        title="LLM Run Log Directory",
        description="Directory for per-run JSON traces",
    )
    llm_run_log_level: Literal["metadata", "full", "off"] = Field(
        default="metadata",
        title="LLM Run Log Level",
        description="Run log detail level: metadata, full, or off",
    )
    llm_replay_log: Optional[str] = Field(
        default=None,
        title="LLM Replay Log",
        description="Run log JSON to replay when LLM_MODE=replay",
    )
    llm_replay_strict: bool = Field(
        default=True,
        title="LLM Replay Strict",
        description="Whether replay mode should enforce request hash matching",
    )

    @classmethod
    def from_env(cls, overrides: Optional[dict[str, Any]] = None) -> "Configuration":
        """Create a configuration object using environment variables and overrides."""

        raw_values: dict[str, Any] = {}

        # Load values from environment variables based on field names
        for field_name in cls.model_fields.keys():
            env_key = field_name.upper()
            if env_key in os.environ:
                raw_values[field_name] = os.environ[env_key]

        # Additional mappings for explicit env names
        env_aliases = {
            "local_llm": os.getenv("LOCAL_LLM"),
            "llm_provider": os.getenv("LLM_PROVIDER"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
            "llm_model_id": os.getenv("LLM_MODEL_ID"),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_timeout": os.getenv("LLM_TIMEOUT"),
            "llm_retry_attempts": os.getenv("LLM_RETRY_ATTEMPTS"),
            "llm_retry_base_delay": os.getenv("LLM_RETRY_BASE_DELAY"),
            "llm_retry_max_delay": os.getenv("LLM_RETRY_MAX_DELAY"),
            "llm_min_interval_seconds": os.getenv("LLM_MIN_INTERVAL_SECONDS"),
            "llm_mode": os.getenv("LLM_MODE"),
            "llm_cache_enabled": os.getenv("LLM_CACHE_ENABLED"),
            "llm_cache_mode": os.getenv("LLM_CACHE_MODE"),
            "llm_cache_dir": os.getenv("LLM_CACHE_DIR"),
            "max_agent_steps": os.getenv("MAX_AGENT_STEPS"),
            "dry_run_skip_search": os.getenv("DRY_RUN_SKIP_SEARCH"),
            "llm_run_log_dir": os.getenv("LLM_RUN_LOG_DIR"),
            "llm_run_log_level": os.getenv("LLM_RUN_LOG_LEVEL"),
            "llm_replay_log": os.getenv("LLM_REPLAY_LOG"),
            "llm_replay_strict": os.getenv("LLM_REPLAY_STRICT"),
            "lmstudio_base_url": os.getenv("LMSTUDIO_BASE_URL"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL"),
            "max_web_research_loops": os.getenv("MAX_WEB_RESEARCH_LOOPS"),
            "fetch_full_page": os.getenv("FETCH_FULL_PAGE"),
            "task_concurrency": os.getenv("TASK_CONCURRENCY"),
            "cors_allow_origins": os.getenv("CORS_ALLOW_ORIGINS"),
            "strip_thinking_tokens": os.getenv("STRIP_THINKING_TOKENS"),
            "use_tool_calling": os.getenv("USE_TOOL_CALLING"),
            "search_api": os.getenv("SEARCH_API"),
            "enable_notes": os.getenv("ENABLE_NOTES"),
            "notes_workspace": os.getenv("NOTES_WORKSPACE"),
        }

        for key, value in env_aliases.items():
            if value is not None:
                raw_values.setdefault(key, value)

        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    raw_values[key] = value

        return cls(**raw_values)

    def resolved_llm_cache_mode(self) -> Literal["off", "read_only", "read_write"]:
        """Resolve the new cache mode while preserving the legacy boolean switch."""

        if "llm_cache_mode" in self.model_fields_set:
            return self.llm_cache_mode
        if self.llm_cache_enabled:
            return "read_write"
        return self.llm_cache_mode

    def sanitized_ollama_url(self) -> str:
        """Ensure Ollama base URL includes the /v1 suffix required by OpenAI clients."""

        base = self.ollama_base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return base

    def resolved_model(self) -> Optional[str]:
        """Best-effort resolution of the model identifier to use."""

        return self.llm_model_id or self.local_llm

    def resolved_cors_origins(self) -> list[str]:
        """Return the configured CORS origins as a clean list."""

        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

