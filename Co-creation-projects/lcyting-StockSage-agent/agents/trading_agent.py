"""
智能股票分析助手 — 交易执行Agent

基于 HelloAgents FunctionCallAgent，负责执行模拟交易操作，
包括持仓查询、资金查询、委托下单、撤单等。

使用方式:
    from agents.trading_agent import create_trading_agent

    agent = create_trading_agent(llm=llm, api_key="...")
    result = agent.run("帮我买入100股贵州茅台")
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
for p in [_HELLO_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.agents.function_call_agent import FunctionCallAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config


# 交易执行Agent系统提示词
TRADING_AGENT_PROMPT = """
你是一位专业的模拟交易执行助手。你可以帮助用户执行以下操作：

## 支持的操作:
1. **查询持仓**: 查看当前模拟账户持仓的股票及其盈亏情况
2. **查询资金**: 查看模拟账户的总资产、可用资金、持仓市值等信息
3. **查询委托**: 查看历史委托订单记录（包括已成交、未成交、已撤销等）
4. **买入股票**: 模拟买入指定股票，需要提供股票代码和数量
5. **卖出股票**: 模拟卖出指定股票，需要提供股票代码和数量
6. **撤销委托**: 撤销指定的未成交委托订单
7. **一键撤单**: 撤销所有未成交的委托订单

## 交易规则:
- A股交易数量必须是100股的整数倍
- 买入/卖出使用工具提供的 mx_moni 工具执行
- 下单前请确认用户的意图明确（股票代码、数量、价格）
- 如果不确定参数，请主动向用户询问确认

## 输出格式:
- 操作成功后，清晰说明操作结果
- 操作失败时，说明失败原因并给出建议
- 对于查询类操作，以易读的表格或列表形式展示数据
- 总是提醒用户：此为模拟交易，非真实资金操作
"""


def create_trading_agent(
    llm: HelloAgentsLLM = None,
    api_key: str = None,
) -> FunctionCallAgent:
    """创建交易执行Agent

    使用FunctionCallAgent范式，注册 mx_moni 工具，
    支持自然语言驱动的模拟交易操作。

    Args:
        llm: HelloAgentsLLM实例（必需）
        api_key: MX_APIKEY（用于工具API调用）

    Returns:
        配置好的FunctionCallAgent实例

    Raises:
        RuntimeError: 若LLM未配置且无法从环境变量创建
    """
    if llm is None:
        llm = _create_default_llm()

    # 创建并注册 mx_moni 工具
    from agents.tools.mx_moni_tool import MXMoniTool
    moni_tool = MXMoniTool(api_key=api_key)

    agent = FunctionCallAgent(
        name="交易执行Agent",
        llm=llm,
        system_prompt=TRADING_AGENT_PROMPT,
        config=Config(temperature=0.3, max_tokens=4096),
    )

    # 注册交易工具
    agent.register_tool(moni_tool)

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
