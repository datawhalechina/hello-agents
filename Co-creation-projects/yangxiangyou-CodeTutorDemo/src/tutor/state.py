"""定义编程导师运行时共享状态。"""

from typing import List, Literal, TypedDict

Mode = Literal["", "question", "review"]


class HistoryItem(TypedDict):
    """保存一轮历史问答，便于后续回答参考上下文。"""

    user: str
    answer: str


class TutorState(TypedDict):
    """保存编程导师一次处理流程中需要共享的数据。"""

    user_input: str  # 用户输入的原始内容。
    mode: Mode  # 当前识别出的请求模式。
    question_text: str  # 提取出的自然语言问题。
    code_text: str  # 提取出的代码片段。
    history: List[HistoryItem]  # 最近几轮对话历史。
    answer: str  # 主回答内容。
    practice: str  # 给用户的练习建议。
    summary: str  # 最终整合后的输出。


def init_state(user_input: str = "", history: List[HistoryItem] | None = None) -> TutorState:
    """创建一份干净的初始状态，供状态图入口调用。"""

    return {
        "user_input": user_input,
        "mode": "",
        "question_text": "",
        "code_text": "",
        "history": list(history or []),
        "answer": "",
        "practice": "",
        "summary": "",
    }
