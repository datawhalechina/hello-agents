"""
智能股票分析助手 — 智能体系统（统一Agent管理与流式调度）

基于 HelloAgents Optimized 框架，管理所有专业Agent的生命周期，
提供统一的流式分析接口供后端API调用。
"""

import sys
import os
import threading
from pathlib import Path
from typing import AsyncIterator, Optional


def _coord_answer_cap_hint(max_chars: int) -> str:
    return (
        f"\n\n【硬性要求】最终答案全文不得超过约 {max_chars} 个汉字（含标点），"
        "分条简练，禁止复述工具返回的全文或大段粘贴。"
    )


def _apply_answer_cap(text: str, max_chars: Optional[int]) -> str:
    if max_chars is None or max_chars <= 0:
        return text or ""
    from .text_truncation import truncate_at_natural_boundary

    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return truncate_at_natural_boundary(t, max_chars, "\n\n…（已达字数上限）")

_HELLO_AGENTS_PATH = Path(__file__).parent.parent / "HelloAgents Optimized"
if str(_HELLO_AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(_HELLO_AGENTS_PATH))

_SKILLS_PATH = Path(__file__).parent.parent / "skills"
if str(_SKILLS_PATH) not in sys.path:
    sys.path.insert(0, str(_SKILLS_PATH))

_BACKEND_PATH = Path(__file__).parent.parent / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))

from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config

_agent_lock = threading.Lock()
_agent_system_instance: Optional["AgentSystem"] = None


class AgentSystem:
    """智能体系统 — 统一管理所有Agent并提供流式分析接口"""

    def __init__(self):
        self._llm: Optional[HelloAgentsLLM] = None
        self._advisor = None         # 巴菲特评估 Agent (Reflection)
        self._sentiment = None       # 舆情分析 Agent (ReAct)
        self._data_analysis = None   # 数据分析 Agent (ReAct)
        self._general_advisor = None # 普通投资顾问 Agent
        self._initialized = False

    def _ensure_llm(self) -> HelloAgentsLLM:
        if self._llm is None:
            self._llm = _create_default_llm()
        return self._llm

    def _get_api_key(self) -> Optional[str]:
        key = os.getenv("MX_APIKEY", "").strip()
        if key and key != "your-mx-apikey-here":
            return key
        try:
            from app.config import settings
            return settings.MX_APIKEY or None
        except Exception:
            return None

    # ---- 巴菲特评估 Agent ----

    def get_advisor_agent(self):
        """获取巴菲特评估 Agent（仅限巴菲特评估界面调用）"""
        if self._advisor is None:
            from agents.advisor_agent import create_advisor_agent
            self._advisor = create_advisor_agent(llm=self._ensure_llm())
        return self._advisor

    def evaluate_buffett_stream(self, stock_code: str, stock_name: str = ""):
        """流式巴菲特评估 - 通过 advisor_agent 生成评估报告"""
        from agents.advisor_agent import evaluate_buffett_stream
        yield from evaluate_buffett_stream(
            llm=self._ensure_llm(),
            stock_code=stock_code,
            stock_name=stock_name,
        )

    # ---- 舆情分析 Agent ----

    def get_sentiment_agent(self):
        """获取舆情分析 Agent"""
        if self._sentiment is None:
            from agents.sentiment_agent import create_sentiment_agent
            self._sentiment = create_sentiment_agent(
                api_key=self._get_api_key(),
                llm=self._ensure_llm(),
            )
        return self._sentiment

    def run_sentiment(
        self,
        stock_code: str,
        stock_name: str = "",
        *,
        max_answer_chars: Optional[int] = None,
    ) -> str:
        """非流式舆情分析 — 返回完整文本，供协调者Agent内部调用"""
        agent = self.get_sentiment_agent()
        stock_label = f"{stock_name}({stock_code})" if stock_name else stock_code
        task = f"请搜索并分析股票 {stock_label} 的最新金融资讯、研究报告和公告，判断市场舆情趋势。"
        if max_answer_chars:
            task += _coord_answer_cap_hint(max_answer_chars)
        try:
            out = (agent.run(task) or "").strip()
            if not out:
                return (
                    "[舆情分析未生成有效正文：可能因网络/超时或模型提前结束。"
                    "建议在个股页使用「AI舆情分析」流式重试，或在 .env 将 LLM_TIMEOUT 调至 300 后重启后端。]"
                )
            return _apply_answer_cap(out, max_answer_chars)
        except Exception as e:
            return f"[舆情分析失败: {e}]"

    def analyze_sentiment_stream(self, stock_code: str, stock_name: str = ""):
        """流式舆情分析"""
        from agents.sentiment_agent import analyze_sentiment_stream
        yield from analyze_sentiment_stream(
            agent=self.get_sentiment_agent(),
            stock_code=stock_code,
            stock_name=stock_name,
        )

    # ---- 数据分析 Agent ----

    def get_data_analysis_agent(self):
        """获取数据分析 Agent"""
        if self._data_analysis is None:
            from agents.data_analysis_agent import create_data_analysis_agent
            self._data_analysis = create_data_analysis_agent(
                api_key=self._get_api_key(),
                llm=self._ensure_llm(),
            )
        return self._data_analysis

    def run_data_analysis(
        self,
        stock_code: str,
        stock_name: str = "",
        *,
        max_answer_chars: Optional[int] = None,
    ) -> str:
        """非流式数据分析 — 返回完整文本，供协调者Agent内部调用"""
        agent = self.get_data_analysis_agent()
        stock_label = f"{stock_name}({stock_code})" if stock_name else stock_code
        task = f"""请查询股票 {stock_label} 的以下数据并进行综合分析：
1. 实时行情（价格、涨跌幅、成交量、换手率等）
2. 核心财务指标（ROE、净利润、营收增长率、毛利率等）
3. 估值水平（市盈率、市净率、股息率等）
4. 公司基本概况

请给出专业的数据分析报告。"""
        if max_answer_chars:
            task += _coord_answer_cap_hint(max_answer_chars)
        try:
            out = (agent.run(task) or "").strip()
            if not out:
                return (
                    "[数据分析未生成有效正文：可能因网络/超时或模型提前结束。"
                    "建议使用个股页「AI数据分析」流式重试，或在 .env 将 LLM_TIMEOUT 调至 300 后重启后端。]"
                )
            return _apply_answer_cap(out, max_answer_chars)
        except Exception as e:
            return f"[数据分析失败: {e}]"

    def analyze_data_stream(self, stock_code: str, stock_name: str = ""):
        """流式数据分析"""
        from agents.data_analysis_agent import analyze_data_stream
        yield from analyze_data_stream(
            agent=self.get_data_analysis_agent(),
            stock_code=stock_code,
            stock_name=stock_name,
        )

    # ---- 普通投资顾问 Agent ----

    def get_general_advisor_agent(self):
        """获取普通投资顾问 Agent"""
        if self._general_advisor is None:
            from agents.general_advisor_agent import create_general_advisor_agent
            self._general_advisor = create_general_advisor_agent(
                llm=self._ensure_llm(),
            )
        return self._general_advisor

    def run_advisor(
        self,
        task: str,
        *,
        max_answer_chars: Optional[int] = None,
    ) -> str:
        """非流式投资建议 — 返回完整文本，供协调者Agent内部调用"""
        agent = self.get_general_advisor_agent()
        if max_answer_chars:
            task = task + _coord_answer_cap_hint(max_answer_chars)
        try:
            out = (agent.run(task) or "").strip()
            return _apply_answer_cap(out, max_answer_chars)
        except Exception as e:
            return f"[投资分析失败: {e}]"

    # ---- AI 对话助手（协调者）----

    def chat_stream(self, user_message: str, history: list = None):
        """AI对话助手流式接口 - 协调者Agent解析用户需求并调度子Agent"""
        from agents.coordinator_agent import coordinator_chat_stream
        yield from coordinator_chat_stream(
            llm=self._ensure_llm(),
            user_message=user_message,
            history=history or [],
            agent_system=self,
        )

    # ---- 健康检查 ----

    def is_ready(self) -> bool:
        try:
            self._ensure_llm()
            return True
        except Exception:
            return False


def _create_default_llm() -> HelloAgentsLLM:
    model = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    provider = os.getenv("LLM_PROVIDER", "auto")

    if not api_key:
        raise RuntimeError("LLM_API_KEY 环境变量未设置")

    try:
        from app.config import settings

        raw_timeout = int(settings.LLM_TIMEOUT)
    except Exception:
        raw_timeout = int(os.getenv("LLM_TIMEOUT", "60"))
    # ReAct 多轮 + 工具调用 + 协调者多 Agent 串联，默认 60s 极易中途超时
    timeout = max(raw_timeout, 180)

    return HelloAgentsLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        temperature=0.3,
        max_tokens=8192,
        timeout=timeout,
    )


def get_agent_system() -> AgentSystem:
    """获取 AgentSystem 全局单例"""
    global _agent_system_instance
    if _agent_system_instance is None:
        with _agent_lock:
            if _agent_system_instance is None:
                _agent_system_instance = AgentSystem()
    return _agent_system_instance
