"""配置管理 - Code Agent CLI 统一配置"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field


# ==================== 模型定义 ====================
# 预定义的模型配置
# - multimodal: 是否支持多模态
# - base_url: API 地址
# - api_key_env: 对应的 API Key 环境变量名（切换模型时自动读取）
# - description: 模型描述
AVAILABLE_MODELS: Dict[str, Dict[str, Any]] = {
    "glm-4.7": {
        "multimodal": False,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": ["ZHIPU_API_KEY", "GLM_API_KEY"],
        "description": "智谱 GLM-4.7 文本模型（默认）",
    },
    "glm-4.6v-flash": {
        "multimodal": True,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": ["ZHIPU_API_KEY", "GLM_API_KEY"],
        "description": "智谱 GLM-4.6V-Flash 多模态模型（支持图片理解）",
    },
    "deepseek-chat": {
        "multimodal": False,
        "base_url": "https://api.deepseek.com",
        "api_key_env": ["DEEPSEEK_API_KEY"],
        "description": "DeepSeek Chat 文本模型",
    },
    "qwen-plus": {
        "multimodal": False,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
        "description": "通义千问 Plus 文本模型",
    },
    "qwen-vl-plus": {
        "multimodal": True,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
        "description": "通义千问 VL Plus 多模态模型",
    },
}

def is_multimodal_model(model_name: str) -> bool:
    """判断模型是否支持多模态"""
    if model_name in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model_name].get("multimodal", False)
    # 启发式判断：模型名包含 v, vl, vision 等关键词
    lower = model_name.lower()
    return any(kw in lower for kw in ["vision", "-vl", "-v-", "4v", "4.6v", "4o"])


class Config(BaseModel):
    """Code Agent CLI 统一配置类
    
    集中管理所有配置项，支持：
    - 环境变量加载
    - 默认值设置
    - 类型验证
    """
    
    # ==================== 基础配置 ====================
    project_name: str = Field(default="code_agent", description="项目名称")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    
    # ==================== LLM 配置 ====================
    default_model: str = Field(default="glm-4.7", description="默认模型")
    default_provider: str = Field(default="zhipu", description="默认提供商")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大 token 数")
    llm_timeout: int = Field(default=60, gt=0, description="LLM 请求超时（秒）")
    
    
    # ==================== Agent 配置 ====================
    max_react_steps: int = Field(default=20, gt=0, le=50, description="ReAct 最大步数")
    max_history_turns: int = Field(default=50, gt=0, description="最大历史对话轮数")
    observation_summary_threshold: int = Field(default=2000, gt=0, description="工具输出摘要阈值")
    
    # ==================== 上下文配置 ====================
    context_max_tokens: int = Field(default=8000, gt=0, description="上下文最大 token 数")
    context_reserve_ratio: float = Field(default=0.15, ge=0.0, le=0.5, description="生成预留比例")
    context_enable_compression: bool = Field(default=True, description="启用上下文压缩")
    context_lazy_fetch: bool = Field(default=True, description="按需获取上下文")
    
    # ==================== 工具配置 ====================
    terminal_timeout: int = Field(default=60, gt=0, description="终端命令超时（秒）")
    terminal_max_output_size: int = Field(default=10 * 1024 * 1024, gt=0, description="终端输出最大大小")
    terminal_confirm_dangerous: bool = Field(default=True, description="危险命令需要确认")
    terminal_allow_shell_mode: bool = Field(default=True, description="允许 Shell 模式")
    context_fetch_max_tokens: int = Field(default=800, gt=0, description="单个数据源最大 token")
    context_fetch_context_lines: int = Field(default=5, ge=0, description="代码上下文行数")
    
    # ==================== 补丁执行器配置 ====================
    patch_max_files: int = Field(default=10, gt=0, description="单个补丁最大文件数")
    patch_max_total_lines: int = Field(default=800, gt=0, description="单个补丁最大总行数")
    patch_allowed_suffixes: List[str] = Field(
        default=[".py", ".md", ".toml", ".json", ".yml", ".yaml", ".txt", ".html", ".css", ".js", ".ts"],
        description="允许修改的文件后缀"
    )
    
    # ==================== 存储配置 ====================
    helloagents_dir: str = Field(default=".helloagents", description="状态存储目录")
    
    # ==================== 安全配置 ====================
    confirm_delete_files: bool = Field(default=True, description="删除文件需要确认")
    confirm_large_changes: bool = Field(default=True, description="大规模变更需要确认")
    large_change_threshold_files: int = Field(default=6, gt=0, description="大规模变更文件数阈值")
    large_change_threshold_lines: int = Field(default=400, gt=0, description="大规模变更行数阈值")
    
    @classmethod
    def from_env(cls, **overrides) -> "Config":
        """从环境变量创建配置
        
        环境变量命名规则：
        - CODE_AGENT_<配置项大写> 或传统命名
        
        Args:
            **overrides: 手动覆盖的配置项
        """
        env_config = {
            "debug": os.getenv("DEBUG", "false").lower() == "true" or os.getenv("CODE_AGENT_DEBUG", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "temperature": float(os.getenv("TEMPERATURE", "0.7")),
            "helloagents_dir": os.getenv("HELLOAGENTS_DIR", os.getenv("CODE_AGENT_STATE_DIR", ".helloagents")),
            "max_react_steps": int(os.getenv("CODE_AGENT_MAX_REACT_STEPS", os.getenv("CODE_AGENT_MAX_STEPS", "20"))),
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "60")),
            "terminal_timeout": int(os.getenv("CODE_AGENT_TERMINAL_TIMEOUT", "60")),
            "patch_max_files": int(os.getenv("CODE_AGENT_PATCH_MAX_FILES", "10")),
            "patch_max_total_lines": int(os.getenv("CODE_AGENT_PATCH_MAX_LINES", "800")),
        }
        
        if os.getenv("MAX_TOKENS"):
            env_config["max_tokens"] = int(os.getenv("MAX_TOKENS"))
        
        # 合并覆盖配置
        env_config.update(overrides)
        
        return cls(**env_config)
    
    def get_state_dir(self, repo_root: Path) -> Path:
        """获取状态存储目录的绝对路径"""
        state_path = Path(self.helloagents_dir)
        if state_path.is_absolute():
            return state_path
        return repo_root / state_path
    
    def get_notes_dir(self, repo_root: Path) -> Path:
        """获取笔记目录"""
        return self.get_state_dir(repo_root) / "notes"
    
    def get_sessions_dir(self, repo_root: Path) -> Path:
        """获取会话目录"""
        return self.get_state_dir(repo_root) / "sessions"
    
    def get_backups_dir(self, repo_root: Path) -> Path:
        """获取备份目录"""
        return self.get_state_dir(repo_root) / "backups"
    
    def get_todos_dir(self, repo_root: Path) -> Path:
        """获取待办目录"""
        return self.get_state_dir(repo_root) / "todos"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def print_summary(self):
        """打印配置摘要"""
        print("=" * 50)
        print("Code Agent CLI 配置")
        print("=" * 50)
        print(f"调试模式: {self.debug}")
        print(f"ReAct 步数: {self.max_react_steps}")
        print(f"历史轮数: {self.max_history_turns}")
        print(f"终端超时: {self.terminal_timeout}s")
        print(f"补丁限制: {self.patch_max_files} 文件, {self.patch_max_total_lines} 行")
        print(f"状态目录: {self.helloagents_dir}")
        print("=" * 50)
