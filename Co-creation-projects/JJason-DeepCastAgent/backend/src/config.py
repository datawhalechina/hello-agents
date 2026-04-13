import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Define backend root directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent

class SearchAPI(Enum):
    """搜索 API 提供商的枚举。

    兼容旧测试和示例：
    - TAVILY: 使用 Tavily 搜索后端
    - SERPAPI: 使用 SerpApi
    - DDG: DuckDuckGo (内置 ddgs)
    - HYBRID: 混合策略（Tavily + SerpApi），为默认值
    """
    TAVILY = "tavily"
    SERPAPI = "serpapi"
    DDG = "ddg"
    HYBRID = "hybrid"


class Configuration(BaseModel):
    """DeepCast Agent Configuration."""

    max_web_research_loops: int = Field(
        default=3,
        title="Research Depth",
        description="Number of research iterations",
    )
    llm_provider: str = Field(
        default="custom",
        title="LLM 提供商",
        description="提供商标识符 (custom)",
    )
    search_api: SearchAPI = Field(
        default=SearchAPI.HYBRID,
        title="搜索 API",
        description="使用混合搜索引擎 (Tavily + SerpApi)",
    )
    enable_notes: bool = Field(
        default=True,
        title="启用笔记",
        description="是否在 NoteTool 中存储任务进度",
    )
    notes_workspace: str = Field(
        default=str(BACKEND_ROOT / "output" / "notes"),
        title="笔记工作区",
        description="NoteTool 持久化任务笔记的目录",
    )
    fetch_full_page: bool = Field(
        default=True,
        title="获取完整页面",
        description="在搜索结果中包含完整页面内容",
    )
    strip_thinking_tokens: bool = Field(
        default=False,
        title="移除思考 Token",
        description="是否从模型响应中移除 <think> token",
    )
    use_tool_calling: bool = Field(
        default=False,
        title="使用工具调用",
        description="使用工具调用而非 JSON 模式进行结构化输出",
    )
    llm_api_key: str | None = Field(
        default=None,
        title="LLM API 密钥",
        description="使用自定义 OpenAI 兼容服务时的可选 API 密钥",
    )
    llm_base_url: str | None = Field(
        default=None,
        title="LLM 基础 URL",
        description="使用自定义 OpenAI 兼容服务时的可选基础 URL",
    )
    llm_model_id: str | None = Field(
        default=None,
        title="LLM 模型 ID",
        description="自定义 OpenAI 兼容服务的可选模型标识符",
    )
    smart_llm_model: str | None = Field(
        default="ecnu-reasoner",
        title="Smart LLM Model",
        description="复杂推理任务使用的模型 ID (e.g. Planning, Reporting)",
    )
    fast_llm_model: str | None = Field(
        default="ecnu-max",
        title="Fast LLM Model",
        description="快速响应任务使用的模型 ID (e.g. Web Research, Script Generation)",
    )
    tts_api_key: str | None = Field(
        default=None,
        title="TTS API 密钥",
        description="TTS 服务的 API 密钥",
    )
    tts_base_url: str = Field(
        default="https://chat.ecnu.edu.cn/open/api/v1/audio/speech",
        title="TTS 基础 URL",
        description="TTS API 的基础 URL",
    )
    tts_model: str = Field(
        default="ecnu-tts",
        title="TTS 模型",
        description="TTS 服务的模型标识符",
    )
    audio_output_dir: str = Field(
        default=str(BACKEND_ROOT / "output" / "audio"),
        title="音频输出目录",
        description="保存生成的音频文件的目录",
    )
    ffmpeg_path: str | None = Field(
        default=None,
        title="FFmpeg 路径",
        description="ffmpeg 可执行文件的路径",
    )
    tavily_api_key: str | None = Field(
        default=None,
        title="Tavily API 密钥",
        description="Tavily 搜索的 API 密钥",
    )
    serpapi_api_key: str | None = Field(
        default=None,
        title="SerpApi 密钥",
        description="SerpApi 的 API 密钥",
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:3000",
        title="CORS 允许的源",
        description="逗号分隔的允许跨域请求的源列表",
    )
    host: str = Field(
        default="0.0.0.0",
        title="服务器主机",
        description="FastAPI 服务器监听的主机地址",
    )
    port: int = Field(
        default=8000,
        title="服务器端口",
        description="FastAPI 服务器监听的端口",
    )
    log_level: str = Field(
        default="INFO",
        title="日志级别",
        description="日志记录级别 (DEBUG, INFO, WARNING, ERROR)",
    )
    llm_timeout: int = Field(
        default=60,
        title="LLM 超时",
        description="LLM 请求超时时间（秒）",
    )
    tts_timeout: int = Field(
        default=300,
        title="TTS 超时",
        description="TTS 请求超时时间（秒）",
    )

    @field_validator("notes_workspace", "audio_output_dir")
    @classmethod
    def resolve_path(cls, v: str) -> str:
        """确保路径是绝对路径，如果是相对路径则基于 BACKEND_ROOT 解析。"""
        if v is None:
            return v
        path = Path(v)
        if not path.is_absolute():
            return str(BACKEND_ROOT / path)
        return v

    @classmethod
    def from_env(cls, overrides: dict[str, Any] | None = None) -> "Configuration":
        """
        使用环境变量和覆盖项创建配置对象。
        
        Args:
            overrides: 可选的配置覆盖字典。
            
        Returns:
            初始化的配置对象。
        """
        raw_values: dict[str, Any] = {}

        # 基于字段名从环境变量加载值
        for field_name in cls.model_fields.keys():
            env_key = field_name.upper()
            if env_key in os.environ:
                raw_values[field_name] = os.environ[env_key]

        # 处理 NO_PROXY
        no_proxy = os.getenv("NO_PROXY")
        if no_proxy:
            os.environ["NO_PROXY"] = no_proxy
            # 同时设置为小写以兼容
            os.environ["no_proxy"] = no_proxy

        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    raw_values[key] = value

        return cls(**raw_values)

    def resolved_model(self) -> str | None:
        """尽力解析要使用的模型标识符。"""
        return self.llm_model_id
