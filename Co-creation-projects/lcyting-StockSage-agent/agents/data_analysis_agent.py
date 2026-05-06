"""
智能股票分析助手 — 数据分析Agent

基于 HelloAgents ReActAgent，使用 mx_data 工具查询行情和财务数据，
执行基本面和技术面的深度分析。

使用方式:
    from agents.data_analysis_agent import create_data_analysis_agent

    agent = create_data_analysis_agent(api_key="...", llm=llm)
    result = agent.run("分析贵州茅台的财务指标和估值水平")
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
_SKILLS_DATA = _PROJECT_ROOT / "skills" / "金融数据" / "mx-data"

for p in [_HELLO_PATH, _AGENTS_DIR, _BACKEND_DIR, _SKILLS_DATA]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import ToolRegistry
from hello_agents.agents.react_agent import ReActAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

from agents.tools.mx_data_tool import MXDataTool

# 数据分析Agent系统提示词
DATA_ANALYSIS_PROMPT = """你是一位专业的A股数据分析师，精通基本面分析和技术面分析。

## 你的职责
1. 查询目标股票的实时行情数据（价格、涨跌幅、成交量、换手率等）
2. 分析核心财务指标（ROE、净利润、营收增长率、毛利率等）
3. 评估估值水平（市盈率、市净率、股息率等）
4. 查看公司基本概况（主营业务、行业地位、高管等）
5. 结合多维数据给出基本面和技术面的综合评估

## 分析框架
- **盈利能力**: ROE、净利润率、毛利率、营收增长率
- **估值水平**: PE、PB、PS、PEG
- **成长性**: 近3年营收/利润复合增长率
- **现金流**: 经营现金流/净利润比率
- **分红**: 股息率、分红率、分红稳定性

## 输出格式
分析结果应包含：
1. **行情快照**：最新价格、涨跌幅、成交情况
2. **财务健康度**：核心指标雷达图式评估
3. **估值分位**：当前估值在历史区间的位置
4. **亮点与风险**：2-3个关键发现

## 重要提醒
- 数据优先，所有结论需有查询数据支撑
- 历史对比时标明时间区间
- 末尾标注免责声明
"""


def create_data_analysis_agent(
    api_key: str = None,
    llm: HelloAgentsLLM = None,
    system_prompt: str = None,
    max_steps: int = 8,
) -> ReActAgent:
    """创建数据分析Agent

    Args:
        api_key: 东方财富MX_APIKEY
        llm: HelloAgentsLLM实例（必需）
        system_prompt: 自定义系统提示词（可选）
        max_steps: 最大推理步数，默认8（数据分析需要多步查询）

    Returns:
        配置好的ReActAgent实例
    """
    if llm is None:
        llm = _create_default_llm()

    registry = ToolRegistry()
    data_tool = MXDataTool(api_key=api_key)
    registry.register_tool(data_tool)

    prompt = system_prompt or DATA_ANALYSIS_PROMPT

    agent = ReActAgent(
        name="数据分析Agent",
        llm=llm,
        tool_registry=registry,
        system_prompt=prompt,
        config=Config(temperature=0.2, max_tokens=4096),
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
        temperature=0.2,
    )
