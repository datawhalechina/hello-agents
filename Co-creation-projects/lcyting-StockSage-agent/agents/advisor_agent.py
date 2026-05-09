"""
智能股票分析助手 — 巴菲特评估Agent（投资顾问Agent）

基于 HelloAgents ReflectionAgent（反思范式），结合巴菲特价值投资思维，
对股票进行深度评估分析。**仅允许巴菲特评估界面调用，不允许协调者Agent调用。**

支持流式输出评估报告。
"""

import sys
import os
from pathlib import Path
from typing import Iterator, Optional

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
for p in [_HELLO_PATH, _BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.agents.reflection_agent import ReflectionAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.core.stream import StreamEvent

from .text_truncation import truncate_at_natural_boundary

BUFFETT_INITIAL_PROMPT = """
你是一位深谙巴菲特价值投资理念的资深投资顾问。请根据以下数据，对股票进行专业的巴菲特式投资分析。

## 股票信息
- 股票代码: {stock_code}
- 股票名称: {stock_name}

## 分析数据:
{data_context}

## 评估维度（巴菲特价值投资框架）:
1. **能力圈评估**: 该公司的业务你是否能理解？商业模式是否简单清晰？
2. **护城河分析**: 公司是否有持久的竞争优势？（品牌、技术、规模、网络效应、成本优势等）
3. **管理层评估**: 管理层是否诚信、有能力？（经营历史、资本配置记录）
4. **财务健康**: 资产负债表是否稳健？（负债率、现金流、ROE稳定性、毛利率）
5. **估值分析**: 当前股价是否低于内在价值？安全边际是否充足？
6. **长期前景**: 公司未来5-10年是否能持续增长？（行业趋势、市场份额）

请提供一个完整、专业的巴菲特式投资分析报告。
文末必须标注：⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

BUFFETT_REFLECT_PROMPT = """
请以严格的投资委员会视角，审查以下巴菲特式投资分析报告的准确性和完整性：

# 原始分析数据:
{task}

# 当前分析报告:
{content}

请检查以下方面并提供改进建议：
1. 数据引用是否准确？有无断章取义？
2. 护城河分析是否有充分论据支撑？
3. 估值逻辑是否自洽？安全边际计算是否合理？
4. 是否遗漏了重要的风险因素？
5. 结论是否过于乐观或悲观？
6. 是否符合巴菲特的价值投资哲学？

如果你的回答已经全面、客观、准确，请回复"无需改进"。
"""

BUFFETT_REFINE_PROMPT = """
请根据投资委员会的反馈意见，改进你的巴菲特式投资分析报告：

# 原始分析数据:
{task}

# 上一轮分析报告:
{last_attempt}

# 委员会反馈:
{feedback}

请提供一个改进后的、更加严谨和完整的投资分析报告。

末尾必须标注：⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""


def _max_reflections_from_env() -> int:
    """环境变量 BUFFETT_MAX_REFLECTIONS，默认 0（初稿后即结束，避免「报告已完却仍在调 LLM」）。"""
    raw = os.getenv("BUFFETT_MAX_REFLECTIONS", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def create_advisor_agent(
    llm: HelloAgentsLLM = None,
    custom_prompts: dict = None,
    max_reflections: Optional[int] = None,
) -> ReflectionAgent:
    """创建巴菲特评估Agent（仅限巴菲特评估界面调用）

    Args:
        llm: HelloAgentsLLM实例
        custom_prompts: 自定义三阶段提示词
        max_reflections: 最大反思迭代次数；为 None 时读取环境变量 BUFFETT_MAX_REFLECTIONS（默认 0）

    Returns:
        配置好的ReflectionAgent实例
    """
    if llm is None:
        llm = _create_default_llm()

    if max_reflections is None:
        max_reflections = _max_reflections_from_env()

    prompts = custom_prompts or {
        "initial": BUFFETT_INITIAL_PROMPT,
        "reflect": BUFFETT_REFLECT_PROMPT,
        "refine": BUFFETT_REFINE_PROMPT,
    }

    agent = ReflectionAgent(
        name="巴菲特评估Agent",
        llm=llm,
        system_prompt="你是一位精通巴菲特价值投资理念的资深投资顾问，擅长护城河分析和安全边际评估。",
        config=Config(temperature=0.4, max_tokens=4096),
        max_iterations=max_reflections,
        custom_prompts=prompts,
    )

    return agent


def evaluate_buffett_stream(
    llm: HelloAgentsLLM = None,
    stock_code: str = "",
    stock_name: str = "",
) -> Iterator[dict]:
    """流式巴菲特评估 - 收集数据并通过ReflectionAgent生成评估报告

    Args:
        llm: HelloAgentsLLM实例
        stock_code: 股票代码
        stock_name: 股票名称

    Yields:
        dict: {"type": "meta"|"status"|"delta"|"done"|"error", "content": str}
    """
    if llm is None:
        llm = _create_default_llm()

    yield {"type": "meta", "stock_code": stock_code, "stock_name": stock_name}

    # 收集分析所需数据
    yield {"type": "status", "content": "正在获取分析数据..."}

    try:
        data_context = _collect_stock_data(stock_code, stock_name)
    except Exception as e:
        msg = f"数据获取失败: {e}"
        yield {"type": "error", "message": msg, "content": msg}
        return

    yield {"type": "status", "content": f"数据获取完成，开始巴菲特式评估分析..."}

    # 构建评估任务
    task = f"""
## 分析数据:
{data_context}

请对股票 {stock_name}({stock_code}) 进行巴菲特式价值投资分析。
"""

    # 创建Agent并使用流式运行
    agent = create_advisor_agent(llm=llm)
    agent.prompts["initial"] = BUFFETT_INITIAL_PROMPT.replace(
        "{stock_code}", stock_code
    ).replace("{stock_name}", stock_name).replace("{data_context}", data_context)

    try:
        for event in agent.stream_run(task, conversation_id=None):
            if event.event_type == "status":
                yield {"type": "status", "content": event.content}
            elif event.event_type == "text":
                chunk = event.content or ""
                yield {"type": "delta", "text": chunk, "content": chunk}
            elif event.event_type == "thought":
                yield {"type": "thought", "content": event.content}
            elif event.event_type == "done":
                yield {"type": "done"}
            elif event.event_type == "error":
                msg = event.content or ""
                yield {"type": "error", "message": msg, "content": msg}
    except Exception as e:
        msg = f"分析过程出错: {e}"
        yield {"type": "error", "message": msg, "content": msg}


def _collect_stock_data(stock_code: str, stock_name: str = "") -> str:
    """收集股票分析所需数据"""
    parts = []

    try:
        from app.services import market_service, news_service

        # 行情数据
        try:
            quote = market_service.get_stock_quote(stock_code)
            if quote and quote.get("success"):
                parts.append(f"## 行情数据\n```json\n{_truncate(str(quote), 3000)}\n```")
        except Exception:
            parts.append("## 行情数据\n获取失败")

        # 财务数据
        try:
            financial = market_service.get_stock_financial(stock_code)
            if financial and financial.get("success"):
                parts.append(f"## 财务数据\n```json\n{_truncate(str(financial), 4000)}\n```")
        except Exception:
            parts.append("## 财务数据\n获取失败")

        # 公司概况
        try:
            profile = market_service.get_stock_profile(stock_code)
            if profile and profile.get("success"):
                parts.append(f"## 公司概况\n```json\n{_truncate(str(profile), 3000)}\n```")
        except Exception:
            parts.append("## 公司概况\n获取失败")

        # 舆情数据
        try:
            sentiment = news_service.analyze_sentiment(stock_code)
            if sentiment and sentiment.get("success"):
                parts.append(f"## 舆情数据\n```json\n{_truncate(str(sentiment), 3000)}\n```")
        except Exception:
            parts.append("## 舆情数据\n获取失败")

    except Exception as e:
        parts.append(f"## 数据收集错误\n{str(e)}")

    return "\n\n".join(parts) if parts else "暂无可用数据"


def _truncate(text: str, max_len: int) -> str:
    return truncate_at_natural_boundary(text or "", max_len, "...[已截断]")


def _create_default_llm() -> HelloAgentsLLM:
    model = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    provider = os.getenv("LLM_PROVIDER", "auto")

    if not api_key:
        raise RuntimeError("LLM_API_KEY 环境变量未设置")

    raw_timeout = int(os.getenv("LLM_TIMEOUT", "60"))
    buffett_timeout = max(raw_timeout, 180)

    return HelloAgentsLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        temperature=0.4,
        max_tokens=6144,
        timeout=buffett_timeout,
    )
