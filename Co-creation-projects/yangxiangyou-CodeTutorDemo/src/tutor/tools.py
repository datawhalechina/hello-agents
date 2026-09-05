"""放置可复用的纯函数工具，优先承载容易测试的逻辑。"""

from __future__ import annotations

import re

from tutor.state import HistoryItem, Mode


CODE_PATTERN = re.compile(r"```(?:python)?\n([\s\S]*?)```", re.IGNORECASE)


def extract_code_block(user_input: str) -> str:
    """优先提取 Markdown 代码块，没有时再按简单特征判断整段是否像代码。"""

    match = CODE_PATTERN.search(user_input)
    if match:
        return match.group(1).strip()

    stripped = user_input.strip()
    code_marks = ["def ", "for ", "while ", "if ", "print(", "return ", "class ", "import "]
    if any(mark in stripped for mark in code_marks) and "\n" in stripped:
        return stripped
    return ""


def detect_mode(user_input: str) -> Mode:
    """根据输入内容判断当前更像普通提问还是代码点评。"""

    if extract_code_block(user_input):
        return "review"

    lowered = user_input.lower()
    review_words = ["报错", "这段代码", "帮我改", "帮我看看", "review", "bug", "代码"]
    if any(word in lowered for word in review_words) and any(token in user_input for token in ["def ", "print(", "return ", "="]):
        return "review"
    return "question"


def build_history_text(history: list[HistoryItem]) -> str:
    """把最近历史整理成提示词上下文。"""

    if not history:
        return "无"

    lines = ["【最近对话】"]
    for index, item in enumerate(history[-3:], start=1):
        lines.append(f"第{index}轮提问：{item['user']}")
        lines.append(f"第{index}轮回答：{item['answer']}")
    return "\n".join(lines)


def build_fallback_answer(mode: Mode) -> str:
    """当模型输出异常时，给出一份还能用于演示的兜底内容。"""

    if mode == "review":
        return (
            "一，先检查变量名和缩进是否正确，二，确认循环和条件分支是否符合预期，"
            "三，建议把功能拆成更小的函数，再逐步打印中间结果定位问题"
        )
    return (
        "这个问题可以先从概念理解开始，再看一个最小示例，最后自己动手改一改参数和输入，"
        "这样更容易真正掌握"
    )
