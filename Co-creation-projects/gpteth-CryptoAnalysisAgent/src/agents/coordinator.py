"""
综合分析协调 Agent (Coordinator)

使用 Plan-and-Solve 范式，协调多个专业 Agent 完成综合分析。
负责任务分发、结果汇总、矛盾信号识别、最终建议生成。
"""

import os
from concurrent.futures import ThreadPoolExecutor

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import Tool, ToolParameter
from typing import Dict, Any, List


COORDINATOR_PROMPT = """你是一位资深的加密货币投资顾问，负责协调技术分析师、链上分析师和情绪分析师的工作，并汇总他们的分析结果，生成综合分析报告。

## 你的角色

你不直接分析市场数据，而是:
1. 将用户的分析需求分解为子任务
2. 分发给对应的专业分析师
3. 收集各维度的分析结果
4. 识别信号一致性和矛盾点
5. 生成综合分析报告和条件化建议

## 工作流程 (Plan-and-Solve)

Step 1: 理解用户需求，确定分析标的和关注点
Step 2: 获取各维度分析
   - 需要完整的多维度分析时，优先调用 run_full_analysis 工具，
     它会并行调用技术、链上、情绪三位分析师，一次返回全部结果（最快）
   - 只需要单一维度时，调用对应的 ask_*_analyst 工具
Step 3: 综合各维度结果，生成最终报告

## 综合报告格式

```markdown
## [币种] 综合分析报告

### 一、技术面摘要
[技术分析师的核心结论]

### 二、链上面摘要
[链上分析师的核心结论]

### 三、情绪面摘要
[情绪分析师的核心结论]

### 四、信号一致性分析
- 一致信号: [多个维度指向同一方向的信号]
- 矛盾信号: [不同维度给出相反结论的信号]
- 信号强度: 强/中/弱

### 五、综合判断
- 整体偏向: 看多/看空/中性
- 置信度: 高/中/低
- 时间框架: 短期/中期/长期

### 六、条件化建议
- 如果你是 [情况A]: [建议A]
- 如果你是 [情况B]: [建议B]
- 如果你是 [情况C]: [建议C]

### 七、风险提示
[关键风险因素和注意事项]

⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。
```

## 重要原则

1. **不做绝对预测**: 所有建议必须是条件化的，禁止使用"必然""一定会""稳赚"等绝对化表述
2. **标注不确定性**: 当信号矛盾时，明确说明
3. **风险优先**: 先讲风险，再讲机会
4. **区分事实和判断**: 数据是事实，结论是判断
5. **尊重用户自主权**: 提供信息和框架，让用户自己决策
6. **数据可溯源**: 报告中的所有价格、指标数值必须来自分析师的返回结果，严禁凭记忆编造任何数字
"""


class SubAgentTool(Tool):
    """子 Agent 调用工具 - 用于协调器调用专业分析 Agent"""

    def __init__(self, agent: SimpleAgent, agent_type: str):
        self._agent = agent
        self._agent_type = agent_type
        description_map = {
            "technical": "调用技术分析师，获取技术面分析（K线、指标、支撑阻力）",
            "onchain": "调用链上分析师，获取链上面分析（资金流向、巨鲸、活跃度）",
            "sentiment": "调用情绪分析师，获取情绪面分析（恐惧贪婪、费率、社交）",
        }
        super().__init__(
            name=f"ask_{agent_type}_analyst",
            description=description_map.get(agent_type, f"调用{agent_type}分析师")
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters.get("query", "")
        if not query:
            return f"错误: 请提供分析请求内容"

        try:
            result = self._agent.run(query)
            return f"## {self._agent_type.upper()} 分析师报告\n\n{result}"
        except Exception as e:
            return f"{self._agent_type} 分析师执行失败: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description=f"发送给{self._agent_type}分析师的分析请求",
                required=True
            ),
        ]


class FullAnalysisTool(Tool):
    """并行综合分析工具 - 同时调用三位分析师，显著缩短整体分析耗时

    三个子 Agent 相互独立 (各自的 LLM 推理 + 数据获取互不依赖)，
    串行调用时总耗时是三者之和，并行后约等于最慢的一个。
    """

    def __init__(self, technical_agent: SimpleAgent, onchain_agent: SimpleAgent,
                 sentiment_agent: SimpleAgent):
        self._analysts = {
            "technical": (technical_agent, "技术面"),
            "onchain": (onchain_agent, "链上面"),
            "sentiment": (sentiment_agent, "情绪面"),
        }
        super().__init__(
            name="run_full_analysis",
            description=(
                "并行调用技术分析师、链上分析师和情绪分析师，"
                "一次性获取三个维度的完整分析结果。"
                "需要综合分析时优先使用此工具，比逐个调用快得多。"
            )
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters.get("query", "")
        if not query:
            return "错误: 请提供分析请求内容"

        def run_analyst(key: str) -> str:
            agent, label = self._analysts[key]
            try:
                return f"## {label}分析师报告\n\n{agent.run(query)}"
            except Exception as e:
                return f"## {label}分析师报告\n\n执行失败: {e}"

        with ThreadPoolExecutor(max_workers=3) as executor:
            reports = list(executor.map(run_analyst, self._analysts.keys()))

        return "\n\n---\n\n".join(reports)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="分析请求内容，将同时发送给三位分析师，例如: 分析 BTC 当前的市场状况",
                required=True
            ),
        ]


def _resolve_sub_llm(llm: HelloAgentsLLM, sub_llm) -> HelloAgentsLLM:
    """解析子 Agent 使用的 LLM (模型分级路由)

    优先级: 显式传入的 sub_llm > 环境变量 LLM_SUB_MODEL_ID > 与协调员同款。
    子 Agent 的工作以数据整理为主，用更便宜的小模型即可，
    把强模型留给 Coordinator 的综合判断——显著降低单次分析成本。
    """
    if sub_llm is not None:
        return sub_llm
    sub_model = os.getenv("LLM_SUB_MODEL_ID")
    if sub_model:
        try:
            return HelloAgentsLLM(model=sub_model)
        except Exception as e:
            print(f"⚠️ 创建子 Agent 模型 {sub_model} 失败，回退为主模型: {e}")
    return llm


def create_coordinator(
    technical_agent: SimpleAgent = None,
    onchain_agent: SimpleAgent = None,
    sentiment_agent: SimpleAgent = None,
    llm: HelloAgentsLLM = None,
    sub_llm: HelloAgentsLLM = None,
    tool_counter=None,
) -> SimpleAgent:
    """
    创建综合分析协调 Agent

    Args:
        technical_agent: 技术分析 Agent (可选，不传则自动创建)
        onchain_agent: 链上分析 Agent (可选，不传则自动创建)
        sentiment_agent: 情绪分析 Agent (可选，不传则自动创建)
        llm: 协调员使用的 LLM (可选，不传则使用默认配置)
        sub_llm: 子 Agent 使用的 LLM (可选)。不传时若设置了环境变量
            LLM_SUB_MODEL_ID 则用该模型创建，否则与协调员共用 llm。
            推荐子 Agent 用小模型 (如 Qwen2.5-7B)、协调员用大模型，
            降低单次分析的 Token 成本
        tool_counter: 可选的 evaluation.ToolCallCounter，
            自动创建子 Agent 时为其工具挂上调用统计 (用于考核)
    """
    if llm is None:
        llm = HelloAgentsLLM()
    sub_llm = _resolve_sub_llm(llm, sub_llm)

    # 如果未提供子 Agent，则自动创建
    if technical_agent is None:
        from .technical_agent import create_technical_agent
        technical_agent = create_technical_agent(sub_llm, tool_counter=tool_counter)

    if onchain_agent is None:
        from .onchain_agent import create_onchain_agent
        onchain_agent = create_onchain_agent(sub_llm, tool_counter=tool_counter)

    if sentiment_agent is None:
        from .sentiment_agent import create_sentiment_agent
        sentiment_agent = create_sentiment_agent(sub_llm, tool_counter=tool_counter)

    # 创建工具注册表，将子 Agent 包装为工具
    # run_full_analysis 并行调用三位分析师 (综合分析场景)
    # ask_*_analyst 单独调用某一位 (定向分析场景)
    tool_registry = ToolRegistry()
    tool_registry.register_tool(
        FullAnalysisTool(technical_agent, onchain_agent, sentiment_agent)
    )
    tool_registry.register_tool(SubAgentTool(technical_agent, "technical"))
    tool_registry.register_tool(SubAgentTool(onchain_agent, "onchain"))
    tool_registry.register_tool(SubAgentTool(sentiment_agent, "sentiment"))

    # 创建协调 Agent
    coordinator = SimpleAgent(
        name="综合分析协调员",
        llm=llm,
        system_prompt=COORDINATOR_PROMPT,
        tool_registry=tool_registry,
    )

    return coordinator
