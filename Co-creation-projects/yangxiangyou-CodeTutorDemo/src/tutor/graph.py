"""构建智能编程导师的 LangGraph 执行图。"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from tutor.logic import (
    answer_question,
    classify_request,
    generate_practice,
    review_code,
    summarize_result,
)
from tutor.model import LLMAdapter
from tutor.state import TutorState


def route_mode(state: TutorState) -> str:
    """根据请求模式决定走问答还是代码点评分支。"""

    return "review_code" if state["mode"] == "review" else "answer_question"


def build_tutor_graph(llm_adapter: LLMAdapter):
    """把识别，回答，练习建议和总结节点组织成一张状态图。"""

    graph = StateGraph(TutorState)
    graph.add_node("classify_request", classify_request)
    graph.add_node("answer_question", lambda state: answer_question(state, llm_adapter))
    graph.add_node("review_code", lambda state: review_code(state, llm_adapter))
    graph.add_node("generate_practice", lambda state: generate_practice(state, llm_adapter))
    graph.add_node("summarize_result", summarize_result)

    graph.set_entry_point("classify_request")
    graph.add_conditional_edges("classify_request", route_mode)
    graph.add_edge("answer_question", "generate_practice")
    graph.add_edge("review_code", "generate_practice")
    graph.add_edge("generate_practice", "summarize_result")
    graph.add_edge("summarize_result", END)
    return graph
