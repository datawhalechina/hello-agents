"""Step 2: StockInsightAgent — ReAct 范式智能股票分析助手"""
import re
from llm_client import HelloAgentsLLM
from tools import (
    ToolExecutor, get_realtime_quote, get_historical_data,
    get_financial_data, calc_indicators, get_news
)

STOCK_AGENT_PROMPT = """
你是一个专业的股票分析助手 StockInsightAgent。你可以获取A股实时行情、历史K线、
财务报表、技术指标和新闻舆情，然后综合这些信息给出分析结论。

可用工具如下：
{tools}

请严格按照以下格式进行回应：

Thought: 你的思考过程，分析用户需求并规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一：
- `{{tool_name}}[{{tool_input}}]`：调用一个可用工具。
  工具输入格式说明：
  - 实时行情: 股票代码 或 股票简称，如 "600519" 或 "贵州茅台"
  - 历史K线: "代码|周期|天数"，如 "600519|daily|60"
  - 财务数据: 股票代码，如 "600519"
  - 技术指标: "代码|周期|天数"，如 "600519|daily|120"
  - 新闻舆情: 股票代码，如 "600519"
- `Finish[最终分析报告]`：当你收集到足够的信息，能够输出完整分析报告时。

分析报告的格式应该包含：
1. 股票基本概况（最新价、涨跌幅、市值等）
2. 技术面分析（趋势、均线、MACD、RSI、支撑压力位）
3. 基本面分析（财务指标解读）
4. 消息面（近期新闻舆情）
5. 风险提示
6. 综合小结

重要：
- 每次只调用一个工具
- 如果用户只给名称没给代码，用该名称搜索实时行情就能找到代码
- 收集到足够信息后输出完整的 Markdown 分析报告
- 数据异常时如实说明，不要编造

现在，请开始分析：
Question: {question}
History: {history}
"""


class StockInsightAgent:
    """智能股票分析 Agent — ReAct 范式"""

    def __init__(self, llm_client: HelloAgentsLLM, max_steps: int = 8):
        self.llm_client = llm_client
        self.tool_executor = ToolExecutor()
        self.max_steps = max_steps
        self.history = []

        # 注册 5 个分析工具
        print("注册工具:")
        self.tool_executor.registerTool(
            "GetRealtimeQuote",
            "获取实时行情(最新价/涨跌幅/成交量/PE/市值)。输入: 股票代码或简称",
            get_realtime_quote
        )
        self.tool_executor.registerTool(
            "GetHistoricalData",
            "获取历史K线(OHLCV)。输入格式: '代码|周期|天数'，周期=daily/weekly/monthly",
            get_historical_data
        )
        self.tool_executor.registerTool(
            "GetFinancialData",
            "获取财务指标(ROE/ROA/毛利率/营收增长等)。输入: 股票代码",
            get_financial_data
        )
        self.tool_executor.registerTool(
            "CalcIndicators",
            "计算技术指标(MA/MACD/RSI/布林带/支撑压力位)。输入格式: '代码|周期|天数'",
            calc_indicators
        )
        self.tool_executor.registerTool(
            "GetNews",
            "获取近期新闻舆情。输入: 股票代码",
            get_news
        )
        print()

    def run(self, question: str):
        self.history = []
        current_step = 0

        print(f"\n{'='*60}")
        print(f"  [用户]: {question}")
        print(f"{'='*60}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step}/{self.max_steps} 步 ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history) if self.history else "（首次执行，无历史）"
            prompt = STOCK_AGENT_PROMPT.format(
                tools=tools_desc, question=question, history=history_str
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("  LLM 未返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought:
                print(f"  [思考] {thought}")
            if not action:
                print("  未能解析出 Action，流程终止。")
                break

            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                print(f"\n{'='*60}")
                print(f"  [分析报告]")
                print(f"{'='*60}")
                print(final_answer)
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name:
                self.history.append("Observation: Action 格式无效。")
                continue

            print(f"  [行动] {tool_name}[{tool_input[:60]}{'...' if len(tool_input)>60 else ''}]")
            tool_func = self.tool_executor.getTool(tool_name)
            observation = (
                tool_func(tool_input) if tool_func
                else f"错误：未找到工具 '{tool_name}'"
            )
            print(f"  [观察]\n{observation[:300]}{'...' if len(str(observation))>300 else ''}")

            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print(f"\n  已达到最大步数 ({self.max_steps})，流程终止。")
        return None

    def _parse_output(self, text: str):
        # 支持 Thought: / **Thought:** / Thought： 等多种格式
        thought_match = re.search(
            r"(?:\*\*)?Thought(?:\*\*)?\s*[:：]\s*(.*?)(?=\n(?:\*\*)?Action(?:\*\*)?\s*[:：]|$)",
            text, re.DOTALL | re.IGNORECASE
        )
        action_match = re.search(
            r"(?:\*\*)?Action(?:\*\*)?\s*[:：]\s*(.*?)$",
            text, re.DOTALL | re.IGNORECASE
        )
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        # 清理 markdown 反引号
        if action:
            action = action.strip("`\"' \n\r")
        return thought, action

    def _parse_action(self, action_text: str):
        # 清理反引号、markdown bold 等
        clean = action_text.strip("`\"' \n\r*_")
        match = re.match(r"(\w+)\[(.*)\]", clean, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)

    def _parse_action_input(self, action_text: str):
        clean = action_text.strip("`\"' \n\r*_")
        match = re.match(r"\w+\[(.*)\]", clean, re.DOTALL)
        return match.group(1) if match else ""
