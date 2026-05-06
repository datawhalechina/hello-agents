"""
智能股票分析助手 — 智能体层骨架

基于 HelloAgents Optimized 框架，定义：
1. Agent角色配置
2. 工具注册模板
3. 智能体编排入口
"""

import sys
from pathlib import Path

# 将HelloAgents框架路径加入sys.path
_HELLO_AGENTS_PATH = Path(__file__).parent.parent / "HelloAgents Optimized"
if str(_HELLO_AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(_HELLO_AGENTS_PATH))

# 将外部Skills路径加入sys.path（如需要直接导入mx_*.py脚本）
_SKILLS_PATH = Path(__file__).parent.parent / "skills"
if str(_SKILLS_PATH) not in sys.path:
    sys.path.insert(0, str(_SKILLS_PATH))

# 将后端配置路径加入sys.path（Agent需要读取配置）
_BACKEND_PATH = Path(__file__).parent.parent / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))

# =========================================================================
# 智能体编排入口（后续模块填充具体Agent）
# =========================================================================


def create_agent_system():
    """创建智能体系统（占位，后续由各Agent模块实现）"""
    from app.config import settings

    if not settings.is_agent_ready():
        raise RuntimeError("LLM_API_KEY 未配置，无法初始化智能体系统")

    # 后续实现:
    # 1. 创建 HelloAgentsLLM 实例
    # 2. 注册各专业Agent
    # 3. 注册工具
    # 4. 创建协调者Agent
    pass
