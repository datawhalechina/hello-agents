"""
智能股票分析助手 — AI对话助手（协调者Agent）

解析用户需求，**智能选择需要调用的子Agent**（不一定全调），
每个子Agent**非流式执行**，协调者收集全部输出后：
1. 分析哪些输出应传递给其他子Agent（如投资顾问需要数据+舆情）
2. 将子Agent输出总结后以流式输出给用户
"""

import sys
import os
import re
from pathlib import Path
from typing import Iterator, Optional

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
for p in [_HELLO_PATH, _BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.core.llm import HelloAgentsLLM

from .text_truncation import truncate_at_natural_boundary

# 协调者调子 Agent 时的输出上限（任务提示 + 硬截断）
COORD_DATA_MAX_CHARS = 2200
COORD_SENTIMENT_MAX_CHARS = 2200
COORD_ADVISOR_MAX_CHARS = 1600
COORD_MERGE_SECTION_MAX_CHARS = 2600
COORD_MERGE_OUTPUT_CHARS_HINT = 1000
# 整合步骤流式输出的 API max_tokens 上限（汉语约 1 token≈1~2 字，用于抑制冗长）
COORD_MERGE_MAX_TOKENS = 1400

# 路由：必须先由 LLM 决定是否调用子 Agent
AGENT_SELECTION_PROMPT = """你是金融分析系统的「路由调度器」，只做一件事：判断是否需要调用后台分析 Agent。

可调用的模块（小写英文关键字）：
- data：仅当用户明确需要行情、财务、估值、基本面数据时
- sentiment：仅当用户明确需要新闻、舆情、公告、研报、市场情绪时
- advisor：仅当用户明确要投资建议、买卖参考、仓位建议时

规则（必读）：
1. 寒暄、科普、与个股无关的问题 → 只回复 none
2. 用户未给出股票代码/名称且无法推断 → 只回复 none
3. 用户仅问单一维度 → 只选一个关键字，不要贪多
4. 不要输出解释、Markdown、引号包裹；不要输出未列出的词

只能输出下面八种形式之一（整行，无其它字符）：
none
data
sentiment
advisor
data,sentiment
data,advisor
sentiment,advisor
data,sentiment,advisor

用户输入:
{message}

你的输出（单行）:"""


def coordinator_chat_stream(
    llm: HelloAgentsLLM,
    user_message: str,
    history: list,
    agent_system,
) -> Iterator[dict]:
    """
    AI对话助手流式接口

    流程:
    1. 解析意图，智能选择需调用的子Agent
    2. 非流式调用选取的子Agent，收集完整输出
    3. 若需投资顾问，将其它子Agent输出作为输入传递
    4. 协调者整理所有输出，流式返回给用户
    """
    yield {"type": "thinking", "content": "正在分析您的问题...\n"}

    stock_info = _extract_stock_info(user_message, history)

    # Step 1：仅一次 LLM 调用 — 决定是否启用子 Agent（避免无谓的全链路透传）
    yield {"type": "status", "content": "路由决策：正在判断是否调用分析引擎...\n"}
    agents_to_call = _select_agents(llm, user_message)
    yield {"type": "status", "content": f"路由结果: {_agents_label(agents_to_call)}\n"}

    if not agents_to_call:
        yield from _handle_general(llm, user_message, history, agent_system, stock_info)
        yield {"type": "done"}
        return

    code = stock_info.get("code", "")
    name = stock_info.get("name", "")

    if not code:
        yield {"type": "thinking", "content": "请提供具体的股票代码或名称，我可以为您做更精准的分析。"}
        yield {"type": "done"}
        return

    # Step 2：按路由顺序调用子 Agent（带字数上限，防止报告无限拉长）
    agent_results = {}
    yield {"type": "status", "content": "正在依次调用分析引擎（带输出篇幅限制）...\n"}

    if "data" in agents_to_call:
        yield {"type": "thinking", "content": "> 正在查询行情与财务数据...\n"}
        agent_results["data"] = agent_system.run_data_analysis(
            code, name, max_answer_chars=COORD_DATA_MAX_CHARS
        )
        yield {"type": "status", "content": "数据分析完成\n"}

    if "sentiment" in agents_to_call:
        yield {"type": "thinking", "content": "> 正在搜索资讯与分析舆情...\n"}
        agent_results["sentiment"] = agent_system.run_sentiment(
            code, name, max_answer_chars=COORD_SENTIMENT_MAX_CHARS
        )
        yield {"type": "status", "content": "舆情分析完成\n"}

    # Step 3: 若需要投资顾问，将数据+舆情结果传递给它
    if "advisor" in agents_to_call:
        yield {"type": "thinking", "content": "> 正在整合数据与舆情，生成投资建议...\n"}
        advisor_input = _build_advisor_input(agent_results, code, name)
        agent_results["advisor"] = agent_system.run_advisor(
            advisor_input, max_answer_chars=COORD_ADVISOR_MAX_CHARS
        )
        yield {"type": "status", "content": "投资分析完成\n"}

    # Step 4: 协调者整理输出，流式返回给用户
    yield {"type": "status", "content": "\n---\n"}
    yield from _stream_aggregated_response(llm, user_message, agent_results, agents_to_call, code, name)

    if len(agent_results) > 1:
        yield {
            "type": "summary",
            "content": "以上为各分析引擎输出的整合结果，仅供参考，不构成投资建议。",
        }
    elif agent_results:
        yield {"type": "summary", "content": "分析已完成，仅供参考，不构成投资建议。"}
    yield {"type": "done"}


def _parse_route_line(raw: str) -> list[str]:
    """解析路由 LLM 输出为有序、去重的 agent 列表。"""
    if not raw:
        return []
    line = raw.strip().splitlines()[0].strip()
    line = re.sub(r"^[`\s]+|[`\s]+$", "", line)
    line = line.lower()
    if line.startswith("```"):
        line = re.sub(r"^```\w*", "", line).strip("`").strip()
    # 去掉常见前缀
    for prefix in ("输出:", "输出：", "answer:", "agents:", "列表:", "列表："):
        if line.startswith(prefix):
            line = line[len(prefix) :].strip()
    tokens = [t.strip() for t in re.split(r"[,，;\s|]+", line) if t.strip()]
    order = ("data", "sentiment", "advisor")
    seen = set()
    out: list[str] = []
    for t in tokens:
        if t == "none":
            return []
        if t in order and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _select_agents(llm: HelloAgentsLLM, message: str) -> list[str]:
    """单次 LLM 调用：决定是否调用子 Agent。"""
    try:
        prompt = AGENT_SELECTION_PROMPT.format(message=message)
        result = llm.invoke(
            [
                {
                    "role": "system",
                    "content": "你只输出路由关键字行，禁止开场白与解释。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=48,
            temperature=0,
        )
        parsed = _parse_route_line(result or "")
        if parsed:
            return parsed
    except Exception:
        pass

    # 兜底：关键词（保守：尽量不触发全链路）
    if any(kw in message for kw in ["新闻", "舆情", "情绪", "资讯", "公告", "研报"]):
        return ["sentiment"]
    if any(kw in message for kw in ["财务", "营收", "利润", "ROE", "PE", "估值", "行情", "价格", "涨跌"]):
        return ["data"]
    if any(kw in message for kw in ["建议", "推荐", "买卖", "买入", "卖出", "投资建议"]):
        return ["advisor"]
    return []


def _build_advisor_input(agent_results: dict, code: str, name: str) -> str:
    """将其他子Agent的输出整合为投资顾问的输入"""
    cap = COORD_MERGE_SECTION_MAX_CHARS
    parts = [
        f"请对股票 {name}({code}) 进行综合投资分析，以下是参考数据（可能已截断）：\n"
    ]

    if "data" in agent_results:
        data_text = agent_results["data"]
        parts.append(f"## 数据分析结果\n{data_text[:cap]}\n")

    if "sentiment" in agent_results:
        sent_text = agent_results["sentiment"]
        parts.append(f"## 舆情分析结果\n{sent_text[:cap]}\n")

    parts.append(
        "请根据以上数据给出投资建议：核心观点、简要逻辑、风险提示；表述简练。"
    )
    return "\n".join(parts)


def _stream_aggregated_response(
    llm: HelloAgentsLLM,
    message: str,
    agent_results: dict,
    agents_to_call: list[str],
    code: str,
    name: str,
) -> Iterator[dict]:
    """协调者将子Agent输出总结后流式输出"""

    # 如果只有一个Agent，直接输出其结果（仍遵守该 Agent 的字数上限）
    if len(agents_to_call) == 1 and len(agent_results) == 1:
        key = agents_to_call[0]
        limit = {
            "data": COORD_DATA_MAX_CHARS,
            "sentiment": COORD_SENTIMENT_MAX_CHARS,
            "advisor": COORD_ADVISOR_MAX_CHARS,
        }.get(key, COORD_DATA_MAX_CHARS)
        result_text = list(agent_results.values())[0]
        yield {"type": "delta", "content": _hard_cap_text(result_text, limit)}
        return

    # 多个Agent：用LLM整合
    stock_label = f"{name}({code})"

    summary_prompt = f"""用户问题: {message}

以下是各分析Agent针对 {stock_label} 的输出结果，请整合为一份清晰的回答：

"""
    for agent_type, text in agent_results.items():
        label_map = {"data": "数据分析", "sentiment": "舆情分析", "advisor": "投资建议"}
        label = label_map.get(agent_type, agent_type)
        body = (text or "").strip()
        if not body:
            body = "（该维度无输出，可能超时或未调用成功。）"
        body = _hard_cap_text(body, COORD_MERGE_SECTION_MAX_CHARS)
        summary_prompt += f"\n## {label}结果\n{body}\n"

    summary_prompt += f"""
请整合以上结果，用以下结构输出（全文总字数控制在约 {COORD_MERGE_OUTPUT_CHARS_HINT} 个汉字以内，禁止复述原文大段）:
1. 核心发现（2-3句）
2. 关键依据（每维度各 2-4 条要点）
3. 综合建议
4. 风险提示
"""

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是金融分析总结助手。输出务必简练，总篇幅控制在约 "
                    f"{COORD_MERGE_OUTPUT_CHARS_HINT} 个汉字内，避免堆砌重复。"
                ),
            },
            {"role": "user", "content": summary_prompt},
        ]
        for chunk in llm.stream_invoke(
            messages,
            max_tokens=COORD_MERGE_MAX_TOKENS,
            temperature=0.2,
        ):
            if chunk:
                yield {"type": "delta", "content": chunk}
    except Exception:
        # 兜底：直接拼接所有结果
        for agent_type, text in agent_results.items():
            label_map = {"data": "数据分析", "sentiment": "舆情分析", "advisor": "投资建议"}
            label = label_map.get(agent_type, agent_type)
            capped = _hard_cap_text(text or "", COORD_MERGE_SECTION_MAX_CHARS)
            yield {"type": "delta", "content": f"\n## {label}\n{capped}\n"}


def _handle_general(
    llm: HelloAgentsLLM,
    message: str,
    history: list,
    agent_system,
    stock_info: dict,
) -> Iterator[dict]:
    """处理一般对话"""
    code = stock_info.get("code", "")
    name = stock_info.get("name", "")

    # 如果提到了股票但没有明确分析需求，给出引导
    if code or name:
        stock_label = f"{name}({code})" if name else code
        yield {"type": "emotional", "content": f"我看到您提到了 {stock_label}。\n\n"}
        yield {"type": "delta", "content": "我可以为您：\n- 分析该股票的行情与财务数据\n- 查看市场舆情与资讯\n- 给出综合投资建议\n\n请告诉我想了解哪个方面？"}

    try:
        messages = [{"role": "system", "content": "你是一个友好的AI股票分析助手。请用简洁专业的语言回复用户，引导用户提出具体的分析需求。"}]
        for h in history[-6:]:
            messages.append(h)
        messages.append({"role": "user", "content": message})

        for chunk in llm.stream_invoke(messages):
            if chunk:
                yield {"type": "delta", "content": chunk}
    except Exception:
        yield {"type": "delta", "content": "您可以问我：分析某只股票、查看市场舆情、获取投资建议等。请提供具体的股票代码。"}


def _extract_stock_info(message: str, history: list) -> dict:
    """从消息中提取股票信息"""
    info = {"code": "", "name": ""}

    code_match = re.search(r'[6|0|3]\d{5}', message)
    if code_match:
        info["code"] = code_match.group()

    name_patterns = [r'分析一下(\S+)', r'(贵州茅台|比亚迪|宁德时代|招商银行|中国平安|五粮液)']
    for pattern in name_patterns:
        name_match = re.search(pattern, message)
        if name_match:
            info["name"] = name_match.group(1)
            break

    return info


def _agents_label(agents: list[str]) -> str:
    labels = {"data": "数据分析", "sentiment": "舆情分析", "advisor": "投资顾问"}
    return " + ".join(labels.get(a, a) for a in agents) if agents else "无需调用Agent"


def _hard_cap_text(text: str, max_chars: int) -> str:
    """截断过长文本（优先段落/句号），防止下游模型上下文膨胀。"""
    if max_chars <= 0 or not text:
        return text or ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return truncate_at_natural_boundary(
        t, max_chars, "\n\n…（已达协调者字数上限，略去后续）"
    )
