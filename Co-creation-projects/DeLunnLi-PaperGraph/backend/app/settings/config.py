
import logging
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = str(_BACKEND_ROOT / "data")
_DEFAULT_DOWNLOADS_DIR = str(_BACKEND_ROOT / "downloads" / "papers")

_DEFAULT_DAILY_ARXIV_CS_CATEGORIES: tuple[str, ...] = (
    "cs.AI",
    "cs.LG",
    "cs.CV",
    "cs.CL",
    "cs.NE",
    "cs.RO",
    "cs.IR",
    "cs.HC",
)
class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "PaperGraph"
    app_version: str = "0.1.0"
    description: str = "学术文献管理系统"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    ncbi_email: str = ""
    ncbi_api_key: str = ""

    openalex_mailto: str = Field(default="", description="OpenAlex mailto 邮箱（推荐真实邮箱）")

    papergraph_httpx_trust_env: bool = Field(
        default=True,
        description="httpx 是否信任 HTTP_PROXY/HTTPS_PROXY 环境变量（需代理时设为 True）",
    )

    tavily_api_key: str = Field(default="", description="Tavily API key")
    tavily_presearch_enabled: bool = Field(default=True, description="Tavily 预搜索开关")

    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"

    openai_model: str = Field(
        default="deepseek-v4-flash",
        description="兼容 OpenAI 的 chat 模型 ID",
    )

    data_dir: str = _DEFAULT_DATA_DIR
    downloads_dir: str = Field(
        default=_DEFAULT_DOWNLOADS_DIR,
        description="PDF 等文件落盘目录，默认 backend/downloads/papers",
    )

    log_level: str = "INFO"

    daily_arxiv_cs_categories: str = Field(
        default="",
        description="arXiv 类目前缀，逗号分隔（如 cs.CV,cs.LG）；留空使用内置默认",
    )

    agent_runtime_default_timeout_sec: float = Field(
        default=20.0,
        ge=1.0,
        le=300.0,
        description="run_agent_task 默认超时（秒）",
    )
    agent_runtime_default_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        description="默认重试次数（不含首轮）",
    )

    papergraph_intent_parse_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="意图 JSON 解析或校验失败后，让模型重新生成的次数（不含首次）",
    )
    papergraph_search_recall_wall_sec: float = Field(
        default=25.0,
        ge=10.0,
        le=180.0,
        description="多源搜索 anyio 总墙时间（秒）",
    )
    papergraph_search_arxiv_fallback_wall_sec: float = Field(
        default=15.0,
        ge=3.0,
        le=90.0,
        description="arXiv 兜底搜索墙时间（秒）",
    )
    papergraph_search_recall_http_timeout_sec: float = Field(
        default=18.0,
        ge=2.0,
        le=60.0,
        description="多源召回阶段 per-request HTTP 超时（秒）",
    )
    papergraph_proceedings_supplement_enabled: bool = Field(
        default=True,
        description="DBLP/OpenAlex 主会钉年召回不足时，用会议官网 proceedings 域补召回",
    )
    papergraph_proceedings_supplement_min_candidates: int = Field(
        default=8,
        ge=1,
        le=40,
        description="候选数低于该阈值时触发 proceedings 官网补召回",
    )
    papergraph_proceedings_auto_discover: bool = Field(
        default=True,
        description="无 JSON 域名映射时，用 Tavily 按会议名+年份自动发现 proceedings 官网再检索",
    )
    papergraph_fine_rank_pipeline_wall_sec: float = Field(
        default=25.0,
        ge=10.0,
        le=120.0,
        description="检索流水线内 LLM 精排线程墙钟上限（秒）",
    )

    papergraph_recall_max_candidates: int = Field(
        default=24,
        ge=8,
        le=60,
        description="进入精排前的最大候选篇数（多源召回上限）",
    )
    papergraph_fine_rank_candidates: int = Field(default=15, ge=5, le=40)
    papergraph_search_http_max_attempts: int = Field(default=2, ge=1, le=5)
    papergraph_pipeline_parallel_presearch: bool = Field(default=True)
    papergraph_venue_hydrate_wall_sec: float = Field(
        default=3.0,
        ge=1.0,
        le=12.0,
        description="原文→OpenAlex 会场探测墙钟上限（秒）",
    )

    papergraph_daily_auto_refresh: bool = Field(default=True)
    papergraph_daily_auto_refresh_idle_sec: int = Field(default=90, ge=15, le=3600)
    papergraph_daily_auto_refresh_poll_sec: int = Field(default=180, ge=30, le=3600)
    papergraph_daily_auto_refresh_startup_grace_sec: int = Field(default=120, ge=10, le=3600)

    papergraph_daily_arxiv_http_timeout_sec: float = Field(
        default=45.0,
        ge=15.0,
        le=300.0,
        description="arXiv 请求读超时（秒）；跨境较慢时可调高",
    )
    papergraph_daily_arxiv_http_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="arXiv 请求失败重试上限",
    )

    dblp_author_pid_min_score: float = Field(
        default=3.0,
        ge=0.0,
        le=10.0,
        description="DBLP author PID 匹配最低分数；低于此值退化为全文搜索",
    )
    openalex_author_match_min_score: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="OpenAlex author ID 匹配最低分数",
    )
    dblp_author_name_fallback_search: bool = Field(
        default=False,
        description="DBLP PID 失败后允许按 author 名回退全文搜索（通常匹配到引用者而非作者本人）",
    )

    arxiv_or_retry_on_empty: bool = Field(
        default=True,
        description="arXiv AND 查询 0 结果时自动用 OR 重试以提高经典论文召回",
    )

    # venue_topic_mismatch_keep_ratio and dblp_venue_aliases_json_path removed — LLM handles both

    llm_disable_proxy: bool = Field(default=False)

    def get_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',')]

    def get_daily_arxiv_cs_categories(self) -> list[str]:
        raw = (self.daily_arxiv_cs_categories or "").strip()
        if raw:
            return [x.strip() for x in raw.split(",") if x.strip()]
        return list(_DEFAULT_DAILY_ARXIV_CS_CATEGORIES)

settings = Settings()

def get_settings() -> Settings:
    return settings

def validate_config():
    errors = []
    warnings = []

    try:
        os.makedirs(settings.data_dir, exist_ok=True)
    except Exception as e:
        errors.append(f"无法创建数据目录: {e}")

    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    if not llm_api_key:
        warnings.append("LLM_API_KEY未配置，AI分析功能将无法使用")

    if (settings.openalex_mailto or "").strip().lower() == "user@example.com":
        warnings.append("OPENALEX_MAILTO 配置为占位符 user@example.com，可能导致 OpenAlex 400/更严格限流（建议改为真实邮箱或留空）")

    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    if warnings:
        logger.warning("⚠️  配置警告:")
        for w in warnings:
            logger.warning("  - %s", w)

    return True

def print_config():
    logger.info("应用名称: %s", settings.app_name)
    logger.info("版本: %s", settings.app_version)
    logger.info("服务器: %s:%s", settings.host, settings.port)
    logger.info("调试模式: %s", ("开启" if settings.debug else "关闭"))

    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
    llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model

    logger.info("LLM API Key: %s", ("已配置" if llm_api_key else "未配置"))
    logger.info("LLM Base URL: %s", llm_base_url)
    logger.info("LLM Model: %s", llm_model)
    logger.info("数据目录: %s", settings.data_dir)
    logger.info("日志级别: %s", settings.log_level)
