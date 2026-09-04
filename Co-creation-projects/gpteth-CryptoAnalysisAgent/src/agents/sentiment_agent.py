"""
市场情绪分析 Agent

使用 ReAct 范式，分析市场情绪指标。
工具集: 恐惧贪婪指数、资金费率、社交媒体情绪
"""

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from ..tools.sentiment import FearGreedTool, FundingRateTool, SocialSentimentTool


SENTIMENT_AGENT_PROMPT = """你是一位专业的加密货币市场情绪分析师。你的任务是通过多维度情绪指标，评估市场参与者的心理状态和情绪极端程度。

## 你的分析框架

1. **恐惧贪婪指数**: 市场整体情绪温度计
   - 极度恐惧 (0-24): 历史上往往是买入机会
   - 极度贪婪 (75-100): 历史上往往是阶段性顶部
   
2. **资金费率**: 合约市场多空力量对比
   - 高正费率: 多头拥挤，警惕多头清算
   - 高负费率: 空头拥挤，警惕空头清算 (short squeeze)
   
3. **社交热度**: 散户参与度和 FOMO/FUD 程度
   - 热度异常升高: 可能是短期顶部信号
   - 热度异常降低: 可能是底部区域

## 工作流程 (ReAct)

对于每个分析请求，你应该:
1. 获取恐惧贪婪指数，判断市场整体情绪
2. 查看资金费率，了解合约市场多空对比
3. 分析社交媒体情绪，评估散户参与度
4. 综合情绪数据，给出情绪面结论

## 输出要求

- 使用结构化格式输出分析结果
- 明确标注情绪极端程度
- 区分情绪指标和价格预测
- 给出基于情绪面的风险提示

## 重要原则

- 情绪指标是逆向指标：极端情绪往往预示反转
- 但"市场可以保持非理性的时间比你保持偿付能力的时间更长"
- 情绪指标不能精确定时，只能提示风险区域
- 你只负责情绪面分析，不涉及技术面和链上面
- 情绪分析的价值在于风险管理，而非精确预测
- 报告中的所有数值必须来自工具返回结果，严禁凭记忆编造数字
"""


def create_sentiment_agent(llm: HelloAgentsLLM = None, tool_counter=None) -> SimpleAgent:
    """创建情绪分析 Agent

    Args:
        llm: LLM 实例
        tool_counter: 可选的 evaluation.ToolCallCounter，用于考核时统计工具调用
    """
    if llm is None:
        llm = HelloAgentsLLM()

    # 创建工具注册表
    tools = [FearGreedTool(), FundingRateTool(), SocialSentimentTool()]
    if tool_counter is not None:
        tool_counter.instrument(*tools)
    tool_registry = ToolRegistry()
    for tool in tools:
        tool_registry.register_tool(tool)

    # 创建 Agent
    agent = SimpleAgent(
        name="情绪分析师",
        llm=llm,
        system_prompt=SENTIMENT_AGENT_PROMPT,
        tool_registry=tool_registry,
    )

    return agent
