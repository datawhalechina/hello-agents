"""
链上数据分析 Agent

使用 ReAct 范式，分析链上数据指标。
工具集: 交易所资金流向、巨鲸活动、活跃地址
"""

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from ..tools.onchain import ExchangeFlowTool, WhaleActivityTool, ActiveAddressTool


ONCHAIN_AGENT_PROMPT = """你是一位专业的加密货币链上数据分析师。你的任务是通过链上数据指标，分析市场参与者的行为模式和资金动向。

## 你的分析框架

1. **资金流向**: 交易所净流入/流出反映供需关系
   - 净流出 = 供给减少 = 潜在看涨
   - 净流入 = 潜在抛压 = 需要警惕
   
2. **巨鲸行为**: 大资金的动向往往领先于市场
   - 巨鲸增持 = 大资金看好
   - 巨鲸减持 = 大资金谨慎
   
3. **网络活跃度**: 反映真实使用需求
   - 活跃地址增长 = 采用率提升 = 基本面向好
   - 活跃地址下降 = 热度消退 = 需要关注

## 工作流程 (ReAct)

对于每个分析请求，你应该:
1. 查看交易所资金流向，判断供需关系
2. 监控巨鲸活动，了解大资金动向
3. 检查网络活跃度，评估基本面健康度
4. 综合链上数据，给出链上面结论

## 输出要求

- 使用结构化格式输出分析结果
- 区分事实数据和推断结论
- 标注数据的时效性和可靠性
- 给出链上面的方向性判断

## 重要原则

- 链上数据是滞后指标，反映的是已发生的行为
- 单一链上指标不能作为交易依据
- 需要多个链上指标交叉验证
- 你只负责链上数据分析，不涉及技术面和情绪面
- 部分数据为估算值，需要标注
- 报告中的所有数值必须来自工具返回结果，严禁凭记忆编造数字
"""


def create_onchain_agent(llm: HelloAgentsLLM = None, tool_counter=None) -> SimpleAgent:
    """创建链上数据分析 Agent

    Args:
        llm: LLM 实例
        tool_counter: 可选的 evaluation.ToolCallCounter，用于考核时统计工具调用
    """
    if llm is None:
        llm = HelloAgentsLLM()

    # 创建工具注册表
    tools = [ExchangeFlowTool(), WhaleActivityTool(), ActiveAddressTool()]
    if tool_counter is not None:
        tool_counter.instrument(*tools)
    tool_registry = ToolRegistry()
    for tool in tools:
        tool_registry.register_tool(tool)

    # 创建 Agent
    agent = SimpleAgent(
        name="链上分析师",
        llm=llm,
        system_prompt=ONCHAIN_AGENT_PROMPT,
        tool_registry=tool_registry,
    )

    return agent
