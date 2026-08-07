"""Step 3: Plan-and-Solve 股票多维度分析
来自 hello-agents 教程第4章 Plan-and-Solve 范式:
  Planner: 将复杂分析问题分解为有序步骤
  Executor: 逐步执行，积累上下文，最终综合生成报告
"""
import ast
from llm_client import HelloAgentsLLM
from tools import (
    get_realtime_quote, get_historical_data, get_financial_data,
    calc_indicators, get_news
)

PLANNER_PROMPT = """你是一个顶级的股票分析规划专家。用户会提出一个股票分析请求，你的任务是将它分解成一个由多个独立步骤组成的分析计划。

每个步骤应该聚焦一个分析维度，按从数据收集到综合分析的逻辑顺序排列。
可用数据维度: 实时行情、历史K线、技术指标(MA/MACD/RSI/布林带)、财务数据、新闻舆情。

问题: {question}

请严格按照以下格式输出计划，```python与```作为前后缀是必要的:
```python
["步骤1: 具体行动描述", "步骤2: 具体行动描述", ...]
```

示例:
```python
["获取600519的实时行情和60天历史K线", "计算技术指标评估趋势和动能", "获取财务数据评估估值", "获取新闻舆情评估市场情绪", "综合所有数据输出完整分析报告"]
```
"""

EXECUTOR_PROMPT = """你是一位专业的股票分析师。你正在按预定计划逐步分析一只股票。

## 完整计划:
{plan}

## 已完成步骤的结果:
{history}

## 当前步骤:
{current_step}

## 可用工具
- GetRealtimeQuote: 获取实时行情。输入: 股票代码
- GetHistoricalData: 获取历史K线。输入格式: "代码|daily|天数"
- CalcIndicators: 计算技术指标。输入格式: "代码|daily|天数"
- GetFinancialData: 获取财务数据。输入: 股票代码
- GetNews: 获取新闻舆情。输入: 股票代码

请执行当前步骤。如果需要获取数据，请在回复中明确指定要调用的工具和参数，格式为:
[[TOOL:工具名:参数]]

示例:
[[TOOL:GetRealtimeQuote:600519]]
[[TOOL:GetHistoricalData:600519|daily|60]]

如果当前步骤是综合分析（不需要获取新数据），请直接基于已有结果给出分析。
如果这是最后一步，请输出完整的综合分析报告，包含: 基本概况、技术面、基本面、消息面、风险提示、投资建议。

现在请执行当前步骤。"""


class Planner:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def plan(self, question: str) -> list:
        prompt = PLANNER_PROMPT.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("\n  [规划中...]")
        response = self.llm_client.think(messages=messages) or ""

        try:
            plan_str = response.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            if isinstance(plan, list) and len(plan) > 0:
                return plan
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"  [规划解析失败: {e}]")

        # 回退：默认分析计划
        return [
            "获取实时行情和60天历史K线数据",
            "计算技术指标(MACD/RSI/布林带/均线)",
            "获取财务数据评估基本面和估值",
            "获取新闻舆情了解市场情绪",
            "综合所有数据生成完整分析报告"
        ]


class Executor:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client
        # 工具映射
        self.tools = {
            "GetRealtimeQuote": get_realtime_quote,
            "GetHistoricalData": get_historical_data,
            "CalcIndicators": calc_indicators,
            "GetFinancialData": get_financial_data,
            "GetNews": get_news,
        }

    def execute(self, question: str, plan: list) -> str:
        import re
        history = ""
        final_result = ""

        print(f"\n  [计划共 {len(plan)} 步]")
        for i, step in enumerate(plan, 1):
            print(f"\n{'='*50}")
            print(f"  步骤 {i}/{len(plan)}: {step}")
            print(f"{'='*50}")

            prompt = EXECUTOR_PROMPT.format(
                plan="\n".join([f"{j}. {s}" for j, s in enumerate(plan, 1)]),
                history=history if history else "（尚无已完成步骤）",
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.think(messages=messages) or ""
            print(f"  [LLM 响应]\n{response[:500]}{'...' if len(response)>500 else ''}")

            # 解析工具调用 [[TOOL:Name:args]]
            tool_pattern = re.findall(r"\[\[TOOL:(\w+):(.*?)\]\]", response)
            tool_results = []

            for tool_name, tool_args in tool_pattern:
                func = self.tools.get(tool_name)
                if func:
                    result = func(tool_args.strip())
                    tool_results.append(f"[{tool_name}结果]\n{result}")
                    print(f"  [工具] {tool_name} 执行完成")

            # 如果有工具调用，让 LLM 基于工具结果再回答一次
            if tool_results:
                followup = f"工具执行结果:\n\n" + "\n\n".join(tool_results)
                followup += f"\n\n请基于以上数据完成当前步骤: {step}"
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": followup})
                final_response = self.llm_client.think(messages=messages) or ""
                step_result = final_response
            else:
                step_result = response

            print(f"  [步骤 {i} 结果]\n{step_result[:300]}{'...' if len(step_result)>300 else ''}")

            history += f"\n--- 步骤{i}: {step} ---\n{step_result}\n"
            final_result = step_result

        return final_result


class PlanAndSolveStockAgent:
    """Plan-and-Solve 股票分析 Agent"""

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client
        self.planner = Planner(llm_client)
        self.executor = Executor(llm_client)

    def run(self, question: str):
        print(f"\n{'='*60}")
        print(f"  Plan-and-Solve 模式")
        print(f"  问题: {question}")
        print(f"{'='*60}")

        # 1. 规划
        plan = self.planner.plan(question)
        print(f"\n  分析计划:")
        for i, step in enumerate(plan, 1):
            print(f"    {i}. {step}")

        # 2. 执行
        final_answer = self.executor.execute(question, plan)

        print(f"\n{'='*60}")
        print(f"  分析完成")
        print(f"{'='*60}")
        return final_answer
