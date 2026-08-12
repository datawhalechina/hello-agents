"""Step 5-8: HelloAgents 框架 StockInsightAgent + Memory + RAG + Context
工具: 5数据 + 7记忆 + 3知识库 + 3上下文
模式: ReActAgent / PlanSolveAgent / ReflectionAgent
"""
from dotenv import load_dotenv
load_dotenv()

from hello_agents import (
    HelloAgentsLLM, ToolRegistry,
    ReActAgent, PlanSolveAgent, ReflectionAgent
)
from tools import (
    get_realtime_quote, get_historical_data,
    get_financial_data, calc_indicators, get_news
)
from memory import (
    memory_add_watchlist, memory_remove_watchlist, memory_get_watchlist,
    memory_save_analysis, memory_get_history,
    memory_set_preference, memory_get_preferences,
)
from rag import rag_search, rag_import, rag_stats
from context_manager import get_context, context_stats, context_clear, context_summarize


def build_tool_registry():
    """注册全部工具: 5个数据 + 7个记忆"""
    registry = ToolRegistry()

    # 数据工具
    registry.register_function(get_realtime_quote, "GetRealtimeQuote",
        "获取A股实时行情(最新价/涨跌幅/成交量/PE/市值)。输入: 股票代码或简称")
    registry.register_function(get_historical_data, "GetHistoricalData",
        "获取历史K线数据(OHLCV)。输入格式: '代码|周期|天数'，如'600519|daily|60'")
    registry.register_function(get_financial_data, "GetFinancialData",
        "获取核心财务指标(净利润/营收/毛利率/负债率/ROE等)。输入: 股票代码")
    registry.register_function(calc_indicators, "CalcIndicators",
        "计算技术指标(MA5/10/20/60, MACD, RSI14, 布林带, 支撑压力位)。输入格式: '代码|daily|天数'")
    registry.register_function(get_news, "GetNews",
        "获取近期新闻舆情。输入: 股票代码")

    # 记忆工具
    registry.register_function(memory_add_watchlist, "AddToWatchlist",
        "添加股票到关注列表。输入: '代码|名称' 如 '600519|贵州茅台'")
    registry.register_function(memory_remove_watchlist, "RemoveFromWatchlist",
        "从关注列表移除股票。输入: 股票代码")
    registry.register_function(memory_get_watchlist, "GetWatchlist",
        "查看当前关注列表。无输入参数")
    registry.register_function(memory_save_analysis, "SaveAnalysis",
        "保存分析结果到历史记录。输入: '代码|问题|摘要'")
    registry.register_function(memory_get_history, "GetHistory",
        "查看分析历史记录。输入: 股票代码(可选)")
    registry.register_function(memory_set_preference, "SetPreference",
        "设置用户偏好。输入: 'key=value' 如 '风格=技术分析为主'")
    registry.register_function(memory_get_preferences, "GetPreferences",
        "查看用户偏好设置。无输入参数")

    # RAG 知识库工具
    registry.register_function(rag_search, "SearchKnowledge",
        "搜索投资知识库(估值方法/技术指标解读/风控原则/A股规则)。输入: 查询关键词")
    registry.register_function(rag_import, "ImportDocument",
        "导入文档到知识库。输入: 文件路径(.txt/.md)")
    registry.register_function(rag_stats, "KnowledgeStats",
        "查看知识库统计信息")

    # 上下文管理工具
    registry.register_function(context_stats, "ContextStats",
        "查看当前对话上下文使用情况(Token用量/轮次)")
    registry.register_function(context_clear, "ContextClear",
        "清空上下文开始新会话。无输入参数")
    registry.register_function(context_summarize, "ContextSummarize",
        "手动压缩对话上下文。无输入参数")

    return registry


STOCK_SYSTEM_PROMPT = """你是专业股票分析助手 StockInsightAgent，具备完整认知能力的智能分析系统。

## 核心能力
- 获取A股实时行情、历史K线、财务数据、技术指标和新闻舆情
- 记住用户的关注列表、分析偏好和历史分析记录
- 查询投资知识库（估值方法、技术指标解读、风控原则、A股交易规则）
- 管理对话上下文（长对话自动压缩，保持会话连贯性）

## 记忆功能
- 当用户说"关注XX股票"时，使用 AddToWatchlist 添加到关注列表
- 完成分析后，使用 SaveAnalysis 保存分析结果
- 看到用户有明确的投资风格倾向时，使用 SetPreference 记住偏好
- 在分析新股票前，先查看 GetWatchlist 和 GetPreferences 了解用户背景

## 知识库功能
- 估值分析时可查询 SearchKnowledge 获取 PE/PB/PEG/股息率 等方法论
- 解读技术指标时可查询 SearchKnowledge 了解 MACD/RSI/布林带 等标准解读
- 风险评估时可查询 SearchKnowledge 获取仓位管理和止损原则

## 上下文管理
- 多轮对话中自然引用之前分析过的结论
- 用户切换分析对象时，关联此前对该股票的分析
- 上下文过长时系统会自动压缩，保持关键信息不丢失

## 分析报告格式
1.基本概况 2.技术面分析 3.基本面与估值 4.消息面 5.风险提示 6.操作建议
当数据不可用时请如实说明，不要编造数据。"""


class FrameworkStockAgent:
    """基于 HelloAgents 框架 + Memory + RAG + Context 的股票分析 Agent"""

    def __init__(self):
        self.llm = self._build_llm()
        self.registry = build_tool_registry()
        self.ctx = get_context()

    def _build_llm(self):
        """构建 LLM，兼容 DeepSeek thinking mode 的 reasoning_content"""
        base = HelloAgentsLLM()
        reasoning_entries = []  # 按序存储每轮 assistant 的 reasoning_content

        try:
            adapter = base._adapter
            adapter._client = adapter.create_client()
            original_create = adapter._client.chat.completions.create

            def patched_create(*args, **kwargs):
                messages = kwargs.get("messages", [])
                # 注入 reasoning_content：给最近一条没有它的 assistant 消息
                missing_idx = 0
                fixed_msgs = []
                for m in messages:
                    m2 = dict(m)
                    if m2.get("role") == "assistant" and not m2.get("reasoning_content"):
                        if missing_idx < len(reasoning_entries):
                            m2["reasoning_content"] = reasoning_entries[missing_idx]
                        missing_idx += 1
                    fixed_msgs.append(m2)
                kwargs["messages"] = fixed_msgs
                resp = original_create(*args, **kwargs)
                # 保存新 reasoning_content
                try:
                    msg = resp.choices[0].message
                    rc = getattr(msg, "reasoning_content", None)
                    if rc:
                        reasoning_entries.append(rc)
                except Exception:
                    pass
                return resp

            adapter._client.chat.completions.create = patched_create
        except Exception as e:
            print(f"Warning: _build_llm monkey patch failed, falling back to standard LLM: {e}")
        return base

    def _run_with_context(self, agent, question: str, mode: str):
        """运行 Agent 并管理上下文"""
        self.ctx.add_turn("user", question)
        result = agent.run(question)
        if result:
            self.ctx.add_turn("assistant", result[:2000])  # 截取结果避免太长
        print(f"\n  [{mode}] {self.ctx.get_stats()}")
        return result

    def react(self, question: str):
        print(f"\n  [ReAct 框架模式] {question}")
        agent = ReActAgent(
            name="StockReAct", llm=self.llm,
            tool_registry=self.registry,
            system_prompt=STOCK_SYSTEM_PROMPT, max_steps=6,
        )
        return self._run_with_context(agent, question, "ReAct")

    def plan_solve(self, question: str):
        print(f"\n  [PlanSolve 框架模式] {question}")
        agent = PlanSolveAgent(
            name="StockPlanner", llm=self.llm,
            tool_registry=self.registry,
            system_prompt=STOCK_SYSTEM_PROMPT,
            enable_tool_calling=True, max_tool_iterations=10,
        )
        return self._run_with_context(agent, question, "PlanSolve")

    def reflect(self, question: str):
        print(f"\n  [Reflection 框架模式] {question}")
        agent = ReflectionAgent(
            name="StockAnalyst", llm=self.llm,
            max_iterations=2, tool_registry=self.registry,
            enable_tool_calling=True, max_tool_iterations=8,
        )
        return self._run_with_context(agent, question, "Reflect")


# ===== CLI =====
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python framework_agent.py react '问题'")
        print("  python framework_agent.py plan '问题'")
        print("  python framework_agent.py reflect '问题'")
        sys.exit(1)

    mode = sys.argv[1]
    question = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "分析贵州茅台600519近期走势"

    agent = FrameworkStockAgent()
    if mode == "react":
        result = agent.react(question)
    elif mode == "plan":
        result = agent.plan_solve(question)
    elif mode == "reflect":
        result = agent.reflect(question)
    else:
        print(f"未知模式: {mode}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(result)
