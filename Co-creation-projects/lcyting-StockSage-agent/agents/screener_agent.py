"""
智能股票分析助手 — 选股Agent

基于 HelloAgents FunctionCallAgent，使用 mx_xuangu 工具进行智能选股。
支持将用户偏好注入选股条件，实现个性化推荐。

使用方式:
    from agents.screener_agent import create_screener_agent

    agent = create_screener_agent(api_key="...", llm=llm)
    result = agent.run("筛选市盈率小于20且ROE大于15%的消费股")
"""

import sys
from pathlib import Path

# 将框架路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
_SKILLS_XUANGU = _PROJECT_ROOT / "skills" / "智能选股" / "mx-xuangu"

for p in [_HELLO_PATH, _AGENTS_DIR, _BACKEND_DIR, _SKILLS_XUANGU]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import ToolRegistry
from hello_agents.agents.function_call_agent import FunctionCallAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

from agents.tools.mx_xuangu_tool import MXXuanguTool

# 默认选股Agent系统提示词
SCREENER_SYSTEM_PROMPT = """你是一位专业的选股策略分析师，精通A股市场的多维度选股方法论。

## 你的职责
1. 理解用户的选股需求和投资偏好
2. 将需求转化为结构化的选股条件（行情+财务+行业组合）
3. 调用智能选股工具获取符合条件的股票列表
4. 分析选股结果，提供专业的策略解读和排序建议

## 选股维度
你可以从以下维度构建选股策略：
- **行情指标**：价格、涨跌幅、成交量、换手率、量比等
- **估值指标**：市盈率(PE)、市净率(PB)、市销率(PS)等
- **财务指标**：ROE、ROA、毛利率、净利率、营收增长率、利润增长率
- **分红指标**：股息率、分红率
- **行业板块**：限定特定行业（如新能源、半导体、消费、医药）
- **指数成分**：沪深300、上证50、创业板等指数成分股

## 输出格式
选股分析结果应包含以下部分：
1. **选股条件解读**：说明你理解的筛选策略
2. **结果概览**：符合条件的股票数量
3. **重点标的**：按关键指标排序，推荐前5-10只
4. **风险提示**：选股策略的局限性说明
5. **免责声明**：以上分析仅供参考，不构成投资建议

## 重要提醒
- 调用工具前先用自然语言清晰组织选股条件
- 如果结果太多，建议用户缩小范围或细分行业
- 如果结果太少，建议用户适当放宽条件
- 始终保持客观，末尾标注免责声明
"""


def create_screener_agent(
    api_key: str = None,
    llm: HelloAgentsLLM = None,
    system_prompt: str = None,
    max_tool_iterations: int = 3,
) -> FunctionCallAgent:
    """创建选股Agent

    Args:
        api_key: 东方财富MX_APIKEY，不提供则从环境变量读取
        llm: HelloAgentsLLM实例（必需），不提供则从环境变量自动创建
        system_prompt: 自定义系统提示词（可选）
        max_tool_iterations: 最大工具调用迭代次数，默认3

    Returns:
        配置好的FunctionCallAgent实例

    Raises:
        RuntimeError: 若LLM未配置且无法从环境变量创建
    """
    # 创建LLM实例（如果未提供）
    if llm is None:
        llm = _create_default_llm()

    # 创建工具注册表并注册选股工具
    registry = ToolRegistry()
    xuangu_tool = MXXuanguTool(api_key=api_key)
    registry.register_tool(xuangu_tool)

    # 使用自定义或默认系统提示词
    prompt = system_prompt or SCREENER_SYSTEM_PROMPT

    # 创建FunctionCallAgent
    agent = FunctionCallAgent(
        name="选股Agent",
        llm=llm,
        system_prompt=prompt,
        tool_registry=registry,
        config=Config(temperature=0.3, max_tokens=4096),
        enable_tool_calling=True,
        default_tool_choice="auto",
        max_tool_iterations=max_tool_iterations,
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
