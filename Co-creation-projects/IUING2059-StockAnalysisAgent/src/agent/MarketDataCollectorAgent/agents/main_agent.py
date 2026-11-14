# agents/main_agent.py
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .stock_data_tool import STOCK_DATA_TOOL

# 加载项目根目录的 .env（按需调整路径）
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MAIN_SYSTEM_PROMPT = """你是一个股票分析助手。你有以下子 agent 可用：
- stock_data_agent：获取单只 A 股的行情、估值、技术面、基本面数据。
  参数 dims 可选：quote、valuation、technical、fundamental。
  用户问"现在多少钱/涨跌"用 quote；问"贵不贵"用 valuation；
  问"趋势/超买超卖"用 technical；问"财务质量/盈利/成长"用 fundamental（较慢）。
  如果用户没指定维度，默认只调 quote。

规则：
1. 只调用与用户问题相关的 dims，不要一次性拉全部数据。
2. 子 agent 返回的 errors 列表要原样保留在回答中，不要编造数据。
3. meta.trade_status 为非交易时段时，要说明"价格为上一交易日收盘"。
4. 不做投资建议，不做跨股票比较。"""

MAIN_TOOLS = [STOCK_DATA_TOOL]


def _get_env(name: str, *aliases: str, required: bool = True) -> str | None:
    """依次尝试 name 和 aliases，返回第一个非空环境变量值。"""
    for key in (name, *aliases):
        value = os.getenv(key)
        if value:
            return value
    if required:
        raise RuntimeError(
            f"缺少环境变量 {name}"
            + (f"（或别名 {', '.join(aliases)}）" if aliases else "")
            + "，请检查 .env 文件。"
        )
    return None


def build_main_agent(model: str | None = None):
    api_key = _get_env("LLM_API_KEY")
    base_url = _get_env("LLM_BASE_URL", "LLM_BASE_URL", required=False)
    model = model or _get_env("LLM_MODEL_ID")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,   # None 时走官方默认
        temperature=0,
    )
    return create_react_agent(llm, MAIN_TOOLS, prompt=MAIN_SYSTEM_PROMPT)