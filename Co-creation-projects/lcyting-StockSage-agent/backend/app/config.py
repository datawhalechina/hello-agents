"""
智能股票分析助手 — 配置管理模块

集中管理所有配置项，支持从环境变量（.env）加载。
参考 HelloAgents 框架的配置模式，参数优先级：构造函数参数 > 环境变量 > 默认值
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 检测是否为 PyInstaller 打包的 exe 运行环境
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # exe 内部资源目录（PyInstaller 临时解压目录）
    _BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    # exe 外部目录（用户配置和数据文件放在 exe 旁边）
    _EXTERNAL_DIR = Path(sys.executable).parent
else:
    # 开发模式：config.py -> app/ -> backend/ -> (项目根目录)
    _BUNDLE_DIR = Path(__file__).parent.parent.parent
    _EXTERNAL_DIR = _BUNDLE_DIR

_PROJECT_ROOT = _BUNDLE_DIR

# 加载 .env（优先从 exe 外部目录加载，开发模式从项目根加载）
# exe 模式下必须用 override=True：否则系统/父进程里已存在的 MX_APIKEY（含空字符串）会阻止读取 exe 旁 .env，表现为「已换 Key 仍提示额度用尽且无缓存」
_env_path = _EXTERNAL_DIR / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=IS_FROZEN)
else:
    load_dotenv(_PROJECT_ROOT / ".env", override=False)

# exe 默认与自动打开的浏览器地址一致（127.0.0.1:5174/dashboard）；开发模式仍为 8000
_DEFAULT_BACKEND_PORT = "5174" if IS_FROZEN else "8000"


class Settings:
    """全局配置单例"""

    # =========================================================================
    # LLM 大模型配置
    # =========================================================================
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "deepseek-chat")
    LLM_API_KEY: str = (os.getenv("LLM_API_KEY") or "").strip()
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # =========================================================================
    # 东方财富妙想API配置
    # =========================================================================
    MX_APIKEY: str = (os.getenv("MX_APIKEY") or "").strip()
    MX_API_URL: str = os.getenv("MX_API_URL", "https://mkapi2.dfcfs.com/finskillshub")
    # 妙想查询缓存 TTL（秒）：行情/指数/资讯/自选股列表等在 TTL 内不走远端妙想；≤0 表示不读缓存但仍写入供额度用尽降级
    # 前端仪表盘 localStorage 默认按 600s（10 分钟）对齐；若改大 TTL，宜同步设置 VITE_DASHBOARD_CACHE_MS（毫秒）
    MX_CACHE_TTL_SECONDS: float = float(os.getenv("MX_CACHE_TTL_SECONDS", "600"))
    # 为 True 时：若 backend/fixtures/mx_raw 下存在对应 query 的原始 JSON，则不调妙想 HTTP（省额度，便于本地修 bug）
    MX_REPLAY_FIXTURES: bool = os.getenv("MX_REPLAY_FIXTURES", "").lower() in ("1", "true", "yes")
    _mx_fix = os.getenv("MX_FIXTURE_DIR")
    MX_FIXTURE_DIR: Path = (
        Path(_mx_fix).expanduser().resolve()
        if _mx_fix
        else (_PROJECT_ROOT / "backend" / "fixtures" / "mx_raw")
    )

    # =========================================================================
    # 项目服务配置
    # =========================================================================
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", _DEFAULT_BACKEND_PORT))
    BACKEND_DEBUG: bool = os.getenv("BACKEND_DEBUG", "true").lower() == "true"
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))

    # =========================================================================
    # 数据库配置
    # =========================================================================
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/stock_analyzer.db")
    @property
    def DATA_DIR(self) -> Path:
        """数据目录（exe 模式下在 exe 旁边）"""
        _dd = os.getenv("DATA_DIR")
        if _dd:
            return Path(_dd)
        return _EXTERNAL_DIR / "data"

    # =========================================================================
    # Redis 配置
    # =========================================================================
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)

    # =========================================================================
    # JWT 配置
    # =========================================================================
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # =========================================================================
    # 项目路径（自动计算）
    # =========================================================================
    @property
    def PROJECT_ROOT(self) -> Path:
        return _PROJECT_ROOT

    @property
    def EXTERNAL_DIR(self) -> Path:
        """exe 外部目录（用户数据、配置存放位置）"""
        return _EXTERNAL_DIR

    @property
    def BUNDLE_DIR(self) -> Path:
        """打包内部资源目录（exe 内嵌文件所在）"""
        return _BUNDLE_DIR

    @property
    def FRONTEND_DIR(self) -> Path:
        """前端静态文件目录"""
        # 优先从环境变量指定（开发模式 vite proxy 之外的其他场景）
        _fd = os.getenv("FRONTEND_DIR")
        if _fd:
            return Path(_fd)
        # exe 模式：前端 dist 内嵌在 bundle 中
        if IS_FROZEN:
            return _BUNDLE_DIR / "frontend" / "dist"
        # 开发模式：从项目根找 frontend/dist
        dist = _PROJECT_ROOT / "frontend" / "dist"
        if dist.exists():
            return dist
        return _PROJECT_ROOT / "frontend" / "dist"

    @property
    def BACKEND_DIR(self) -> Path:
        return _PROJECT_ROOT / "backend"

    @property
    def AGENTS_DIR(self) -> Path:
        return _PROJECT_ROOT / "agents"

    @property
    def SKILLS_DIR(self) -> Path:
        return _PROJECT_ROOT / "skills"

    @property
    def HELLO_AGENTS_DIR(self) -> Path:
        return _PROJECT_ROOT / "HelloAgents Optimized"

    # =========================================================================
    # 验证方法
    # =========================================================================
    def validate(self) -> list[str]:
        """验证关键配置项，返回缺失配置列表"""
        warnings = []
        if not self.LLM_API_KEY or self.LLM_API_KEY == "your-api-key-here":
            warnings.append("LLM_API_KEY 未配置，智能体功能将不可用")
        if not self.MX_APIKEY or self.MX_APIKEY == "your-mx-apikey-here":
            warnings.append("MX_APIKEY 未配置，外部金融数据服务将不可用")
        return warnings

    def is_agent_ready(self) -> bool:
        """检查智能体层是否就绪"""
        return bool(self.LLM_API_KEY and self.LLM_API_KEY != "your-api-key-here")

    def is_skills_ready(self) -> bool:
        """检查外部服务层是否就绪"""
        return bool(self.MX_APIKEY and self.MX_APIKEY != "your-mx-apikey-here")


# 全局配置单例
settings = Settings()
