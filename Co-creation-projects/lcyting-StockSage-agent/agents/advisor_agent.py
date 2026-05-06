"""
智能股票分析助手 — 投资顾问Agent

基于 HelloAgents ReflectionAgent（反思范式），综合多源分析结果，
结合巴菲特价值投资思维，生成投资建议。

使用方式:
    from agents.advisor_agent import create_advisor_agent

    agent = create_advisor_agent(llm=llm)
    result = agent.run("根据以下分析数据，给出贵州茅台的投资建议...")
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
for p in [_HELLO_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.agents.reflection_agent import ReflectionAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

# 投资顾问Agent初始生成提示词
ADVISOR_INITIAL_PROMPT = """
你是一位资深投资顾问，深谙巴菲特价值投资理念。请根据以下分析数据，给出专业的投资分析和建议。

## 分析数据:
{task}

## 评估维度（巴菲特价值投资框架）:
1. **护城河分析**: 公司是否有持久的竞争优势？（品牌、技术、规模、网络效应等）
2. **管理层评估**: 管理层是否诚信、有能力？（可比公司对比、历史决策回顾）
3. **安全边际**: 当前股价是否低于内在价值？（PE vs 行业均值、PB vs 历史分位）
4. **长期前景**: 公司未来5-10年是否能持续增长？（行业趋势、市场份额）
5. **财务健康**: 资产负债表是否稳健？（负债率、现金流、ROE稳定性）

请提供一个完整、专业的投资分析：
"""

# 反思提示词
ADVISOR_REFLECT_PROMPT = """
请以严格的投资委员会视角，审查以下投资分析报告的准确性和完整性：

# 原始分析数据:
{task}

# 当前分析报告:
{content}

请检查以下方面并提供改进建议：
1. 数据引用是否准确？有无断章取义？
2. 结论是否有充分的数据支撑？
3. 是否遗漏了重要的风险因素？
4. 估值逻辑是否自洽？
5. 建议是否过于乐观或悲观？

如果你的回答已经全面、客观、准确，请回复"无需改进"。
"""

# 优化提示词
ADVISOR_REFINE_PROMPT = """
请根据投资委员会的反馈意见，改进你的投资分析报告：

# 原始分析数据:
{task}

# 上一轮分析报告:
{last_attempt}

# 委员会反馈:
{feedback}

请提供一个改进后的、更加严谨和完整的投资分析报告。

末尾必须标注：⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""


def create_advisor_agent(
    llm: HelloAgentsLLM = None,
    custom_prompts: dict = None,
    max_reflections: int = 2,
) -> ReflectionAgent:
    """创建投资顾问Agent

    使用ReflectionAgent实现自我反思优化：
    1. 初始生成：基于数据给出投资分析
    2. 反思审查：自我审查分析的准确性和完整性
    3. 迭代优化：根据审查结果改进分析

    Args:
        llm: HelloAgentsLLM实例（必需）
        custom_prompts: 自定义三阶段提示词（可选）
        max_reflections: 最大反思迭代次数，默认2

    Returns:
        配置好的ReflectionAgent实例
    """
    if llm is None:
        llm = _create_default_llm()

    prompts = custom_prompts or {
        "initial": ADVISOR_INITIAL_PROMPT,
        "reflect": ADVISOR_REFLECT_PROMPT,
        "refine": ADVISOR_REFINE_PROMPT,
    }

    agent = ReflectionAgent(
        name="投资顾问Agent",
        llm=llm,
        system_prompt="你是一位精通巴菲特价值投资理念的资深投资顾问，擅长护城河分析和安全边际评估。",
        config=Config(temperature=0.4, max_tokens=4096),  # 稍高温度允许更多思考
        max_iterations=max_reflections,
        custom_prompts=prompts,
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
        temperature=0.4,
    )
