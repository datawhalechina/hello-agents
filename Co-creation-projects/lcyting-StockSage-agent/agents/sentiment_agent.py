"""
智能股票分析助手 — 舆情分析Agent

基于 HelloAgents ReActAgent，使用 mx-search 工具搜索金融资讯，
并结合LLM进行情感倾向分析和舆情研判。

使用方式:
    from agents.sentiment_agent import create_sentiment_agent

    agent = create_sentiment_agent(api_key="...", llm=llm)
    result = agent.run("分析贵州茅台的舆情情况")
"""

import sys
from pathlib import Path

# 将框架路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
_SKILLS_SEARCH = _PROJECT_ROOT / "skills" / "资讯搜索" / "mx-search"

for p in [_HELLO_PATH, _AGENTS_DIR, _BACKEND_DIR, _SKILLS_SEARCH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import ToolRegistry
from hello_agents.agents.react_agent import ReActAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

from agents.tools.mx_search_tool import MXSearchTool

# 默认舆情分析系统提示词
SENTIMENT_SYSTEM_PROMPT = """你是一位专业的金融舆情分析师，精通A股市场和各种政策分析方法论。

## 你的职责
1. 搜索目标股票/行业的最新金融资讯（新闻、研报、公告）
2. 分析各条资讯的情感倾向（正面/负面/中性）
3. 识别关键事件和潜在影响
4. 综合判断市场舆情趋势
5. 提供客观、有数据支撑的舆情研判结论

## 分析方法
- 关注信息来源的权威性（官方公告 > 权威研报 > 新闻报道）
- 关注资讯的时效性（越新越重要）
- 区分短期情绪波动和长期趋势变化
- 注意识别潜在的利好/利空事件
- 结合行业政策环境进行分析

## 输出格式
分析结果应包含以下部分：
1. **舆情总览**：情感分布统计（正面X条/负面X条/中性X条）
2. **核心事件**：最重要的2-3个关键资讯摘要
3. **情感趋势**：整体舆情偏向及变化趋势
4. **风险提示**：需要关注的潜在风险和不确定性
5. **综合研判**：基于舆情分析的投资参考建议（不构成投资建议）

## 重要提醒
- 始终保持客观中立，不夸大也不隐瞒风险
- 所有分析结论需有搜索结果支撑
- 末尾必须标注"以上分析仅供参考，不构成投资建议"
"""


def create_sentiment_agent(
    api_key: str = None,
    llm: HelloAgentsLLM = None,
    system_prompt: str = None,
    max_steps: int = 5,
) -> ReActAgent:
    """创建舆情分析Agent

    Args:
        api_key: 东方财富MX_APIKEY，不提供则从环境变量读取
        llm: HelloAgentsLLM实例（必需），不提供则从环境变量自动创建
        system_prompt: 自定义系统提示词（可选）
        max_steps: 最大推理步数，默认5

    Returns:
        配置好的ReActAgent实例

    Raises:
        RuntimeError: 若LLM未配置且无法从环境变量创建
    """
    # 创建LLM实例（如果未提供）
    if llm is None:
        llm = _create_default_llm()

    # 创建工具注册表并注册资讯搜索工具
    registry = ToolRegistry()
    search_tool = MXSearchTool(api_key=api_key)
    registry.register_tool(search_tool)

    # 使用自定义或默认系统提示词
    prompt = system_prompt or SENTIMENT_SYSTEM_PROMPT

    # 创建ReActAgent
    agent = ReActAgent(
        name="舆情分析Agent",
        llm=llm,
        tool_registry=registry,
        system_prompt=prompt,
        config=Config(temperature=0.3, max_tokens=4096),  # 低温度确保分析稳定
        max_steps=max_steps,
    )

    return agent


def _create_default_llm() -> HelloAgentsLLM:
    """从环境变量创建默认LLM实例"""
    import os

    model = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    provider = os.getenv("LLM_PROVIDER", "auto")

    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY 环境变量未设置，请先设置环境变量：\n"
            "export LLM_API_KEY=your_llm_api_key_here\n"
            "或在创建Agent时传入 llm 参数"
        )

    return HelloAgentsLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        temperature=0.3,
    )
