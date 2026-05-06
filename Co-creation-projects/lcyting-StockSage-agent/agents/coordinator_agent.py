"""
智能股票分析助手 — 协调者Agent

基于 HelloAgents PlanAndSolveAgent，负责将用户的股票分析请求
分解为多个子任务，分发给各专业Agent执行，并整合结果。

使用方式:
    from agents.coordinator_agent import create_coordinator_agent

    agent = create_coordinator_agent(llm=llm)
    result = agent.run("分析贵州茅台的投资价值")
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
for p in [_HELLO_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.agents.plan_solve_agent import PlanAndSolveAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

# 协调者Agent规划器提示词
COORDINATOR_PLANNER_PROMPT = """
你是一个顶级的金融分析协调专家。你的任务是将用户的股票分析请求分解成一个由多个简单步骤组成的执行计划。

每个步骤应该是一个独立可执行的分析任务，包括但不限于：
1. 基本面分析（财务指标、估值水平、盈利能力）
2. 技术面分析（行情走势、涨跌幅、成交量）
3. 公司概况（主营业务、行业地位、高管信息）
4. 舆情分析（新闻、研报、公告的正面/负面评价）
5. 风险评估（行业风险、政策风险、市场风险）
6. 投资建议（综合以上维度给出参考意见）

请确保计划步骤按照逻辑顺序排列（先数据收集，再分析评估，最后综合建议）。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

# 协调者Agent执行器提示词
COORDINATOR_EXECUTOR_PROMPT = """
你是一位顶级的金融分析执行专家。你的任务是严格按照给定的计划，一步步完成股票分析任务。

请针对当前步骤，结合已有的历史分析结果，给出该步骤的专业分析结论。

注意：
- 每个步骤的分析应基于数据和逻辑推理
- 保持客观中立，不夸大也不隐瞒风险
- 使用专业但易于理解的金融语言

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的专业分析结论:
"""


def create_coordinator_agent(
    llm: HelloAgentsLLM = None,
    planner_prompt: str = None,
    executor_prompt: str = None,
) -> PlanAndSolveAgent:
    """创建协调者Agent

    Args:
        llm: HelloAgentsLLM实例（必需）
        planner_prompt: 自定义规划器提示词（可选）
        executor_prompt: 自定义执行器提示词（可选）

    Returns:
        配置好的PlanAndSolveAgent实例

    Raises:
        RuntimeError: 若LLM未配置且无法从环境变量创建
    """
    if llm is None:
        llm = _create_default_llm()

    agent = PlanAndSolveAgent(
        name="协调者Agent",
        llm=llm,
        system_prompt="你是一个精通A股市场的金融分析协调专家，负责分解复杂分析任务并整合分析结果。",
        config=Config(temperature=0.3, max_tokens=4096),
        planner_prompt=planner_prompt or COORDINATOR_PLANNER_PROMPT,
        executor_prompt=executor_prompt or COORDINATOR_EXECUTOR_PROMPT,
        max_steps=6,
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
