"""
技术分析 Agent

使用 ReAct 范式，通过观察-思考-行动循环完成技术分析任务。
工具集: K线数据获取、技术指标计算、支撑阻力位识别
"""

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from ..tools.technical import KlineFetchTool, TechnicalIndicatorTool, SupportResistanceTool


TECHNICAL_AGENT_PROMPT = """你是一位专业的加密货币技术分析师。你的任务是基于价格数据和技术指标，对指定的加密货币进行技术面分析。

## 你的分析框架

1. **趋势判断**: 通过 EMA 排列和价格位置判断当前趋势方向
2. **动量分析**: 通过 RSI 和 MACD 判断趋势强度和潜在反转
3. **波动率**: 通过布林带和 ATR 评估当前波动水平
4. **关键价位**: 识别支撑位和阻力位，评估风险收益比

## 工作流程 (ReAct)

对于每个分析请求，你应该:
1. 先获取 K 线数据，了解价格走势
2. 计算技术指标，量化市场状态
3. 识别支撑阻力位，确定关键价位
4. 综合所有信息，给出技术面结论

## 输出要求

- 使用结构化格式输出分析结果
- 明确标注趋势方向、关键价位、指标状态
- 给出条件化的技术面建议（不是绝对预测）
- 标注分析的时间周期和局限性

## 重要原则

- 技术分析有其局限性，不能预测黑天鹅事件
- 不同时间周期可能给出矛盾信号，需要说明
- 所有结论都应该是条件化的，而非绝对的
- 你只负责技术面分析，不涉及基本面和情绪面
- 报告中的所有价格和指标数值必须来自工具返回结果，严禁凭记忆编造数字
"""


def create_technical_agent(llm: HelloAgentsLLM = None, tool_counter=None) -> SimpleAgent:
    """创建技术分析 Agent

    Args:
        llm: LLM 实例
        tool_counter: 可选的 evaluation.ToolCallCounter，用于考核时统计工具调用
    """
    if llm is None:
        llm = HelloAgentsLLM()

    # 创建工具注册表
    tools = [KlineFetchTool(), TechnicalIndicatorTool(), SupportResistanceTool()]
    if tool_counter is not None:
        tool_counter.instrument(*tools)
    tool_registry = ToolRegistry()
    for tool in tools:
        tool_registry.register_tool(tool)

    # 创建 Agent
    agent = SimpleAgent(
        name="技术分析师",
        llm=llm,
        system_prompt=TECHNICAL_AGENT_PROMPT,
        tool_registry=tool_registry,
    )

    return agent
