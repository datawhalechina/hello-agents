"""把各个节点函数组织成完整的编程导师工作流。"""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from tutor.model import LLMAdapter
from tutor.state import HistoryItem, TutorState
from tutor.tools import build_fallback_answer, build_history_text, detect_mode, extract_code_block


def classify_request(state: TutorState) -> TutorState:
    """识别请求模式，并把问题文本和代码片段拆开。"""

    mode = detect_mode(state["user_input"])
    code_text = extract_code_block(state["user_input"])

    state["mode"] = mode
    state["code_text"] = code_text
    state["question_text"] = state["user_input"] if mode == "question" else "请帮我点评这段 Python 代码"
    return state


def answer_question(state: TutorState, llm_adapter: LLMAdapter) -> TutorState:
    """处理普通编程问题，生成适合初学者阅读的教学回答。"""

    history_text = build_history_text(state["history"])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一名耐心的智能编程导师，面对的是初学者。\n"
                "请严格返回 JSON，格式为 {{\"answer\": \"...\"}}。\n"
                "回答要包含概念解释，解题思路，简单示例，容易犯错的点。\n"
                "不要输出 JSON 之外的文字。""",
            ),
            (
                "user",
                """最近上下文：\n{history_text}\n\n"
                "当前问题：{question_text}""",
            ),
        ]
    )
    raw_result = llm_adapter.invoke(
        prompt.format_messages(
            history_text=history_text,
            question_text=state["question_text"],
        )
    )

    try:
        result = json.loads(raw_result.strip())
        state["answer"] = result["answer"]
    except (json.JSONDecodeError, KeyError, TypeError):
        state["answer"] = build_fallback_answer("question")
    return state


def review_code(state: TutorState, llm_adapter: LLMAdapter) -> TutorState:
    """处理代码点评请求，给出问题分析和修改建议。"""

    history_text = build_history_text(state["history"])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一名细心的 Python 编程导师，要帮初学者看代码。\n"
                "请严格返回 JSON，格式为 {{\"answer\": \"...\"}}。\n"
                "回答要包含主要问题，修改建议，参考改法，学习提醒。\n"
                "不要输出 JSON 之外的文字。""",
            ),
            (
                "user",
                """最近上下文：\n{history_text}\n\n"
                "请点评下面这段代码：\n```python\n{code_text}\n```""",
            ),
        ]
    )
    raw_result = llm_adapter.invoke(
        prompt.format_messages(
            history_text=history_text,
            code_text=state["code_text"] or state["user_input"],
        )
    )

    try:
        result = json.loads(raw_result.strip())
        state["answer"] = result["answer"]
    except (json.JSONDecodeError, KeyError, TypeError):
        state["answer"] = build_fallback_answer("review")
    return state


def generate_practice(state: TutorState, llm_adapter: LLMAdapter) -> TutorState:
    """不管是哪种模式，都补一条下一步练习建议。"""

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "请严格返回 JSON，格式为 {{\"practice\": \"...\"}}，内容是一条适合初学者的课后练习建议，不要输出额外文字。",
            ),
            (
                "user",
                "当前模式：{mode}\n当前内容：{content}",
            ),
        ]
    )
    raw_result = llm_adapter.invoke(
        prompt.format_messages(
            mode=state["mode"],
            content=state["question_text"] or state["code_text"] or state["user_input"],
        )
    )

    try:
        result = json.loads(raw_result.strip())
        state["practice"] = result["practice"]
    except (json.JSONDecodeError, KeyError, TypeError):
        state["practice"] = "你可以自己再写一个相似的小例子，然后改动输入和条件，观察结果怎么变化。"
    return state


def summarize_result(state: TutorState) -> TutorState:
    """把回答和练习建议整合成最终输出，并写回历史。"""

    title = "编程问题讲解" if state["mode"] == "question" else "代码点评结果"
    state["summary"] = f"【{title}】\n{state['answer']}\n\n【练习建议】\n{state['practice']}"
    history_item: HistoryItem = {
        "user": state["user_input"],
        "answer": state["summary"],
    }
    state["history"] = [*state["history"], history_item][-3:]
    return state
