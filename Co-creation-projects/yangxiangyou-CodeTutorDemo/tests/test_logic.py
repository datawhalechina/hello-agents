from tutor.logic import answer_question, classify_request, generate_practice, review_code, summarize_result
from tutor.model import FakeLLMAdapter
from tutor.state import init_state
from tutor.tools import build_history_text, detect_mode, extract_code_block


def test_detect_mode_returns_question_for_plain_question() -> None:
    assert detect_mode("Python 的字典和列表有什么区别？") == "question"


def test_detect_mode_returns_review_for_code_block() -> None:
    user_input = "请帮我看看\n```python\ndef hello():\n    print('hi')\n```"
    assert detect_mode(user_input) == "review"


def test_extract_code_block_reads_markdown_code() -> None:
    user_input = "```python\nfor i in range(3):\n    print(i)\n```"
    assert extract_code_block(user_input) == "for i in range(3):\n    print(i)"


def test_build_history_text_uses_recent_three_items() -> None:
    history = [
        {"user": "问题1", "answer": "回答1"},
        {"user": "问题2", "answer": "回答2"},
        {"user": "问题3", "answer": "回答3"},
        {"user": "问题4", "answer": "回答4"},
    ]

    history_text = build_history_text(history)

    assert "问题1" not in history_text
    assert "第1轮提问：问题2" in history_text
    assert "第3轮回答：回答4" in history_text


def test_classify_request_sets_question_fields() -> None:
    state = init_state("什么是递归？")

    result = classify_request(state)

    assert result["mode"] == "question"
    assert result["question_text"] == "什么是递归？"
    assert result["code_text"] == ""


def test_classify_request_sets_review_fields() -> None:
    state = init_state("请帮我看代码\n```python\ndef add(a, b):\n    return a + b\n```")

    result = classify_request(state)

    assert result["mode"] == "review"
    assert result["question_text"] == "请帮我点评这段 Python 代码"
    assert result["code_text"] == "def add(a, b):\n    return a + b"


def test_answer_question_reads_json_answer() -> None:
    llm = FakeLLMAdapter(['{"answer": "这是关于列表推导式的讲解"}'])
    state = init_state("什么是列表推导式？", history=[{"user": "上次问什么是变量", "answer": "变量是用来保存数据的名字"}])
    state["question_text"] = "什么是列表推导式？"
    state["mode"] = "question"

    result = answer_question(state, llm)

    assert result["answer"] == "这是关于列表推导式的讲解"


def test_review_code_uses_fallback_on_invalid_json() -> None:
    llm = FakeLLMAdapter(["这不是合法 JSON"])
    state = init_state("请帮我看代码")
    state["mode"] = "review"
    state["code_text"] = "def add(a, b):\nreturn a + b"

    result = review_code(state, llm)

    assert "先检查变量名和缩进是否正确" in result["answer"]


def test_generate_practice_reads_json_result() -> None:
    llm = FakeLLMAdapter(['{"practice": "请你再写一个 while 循环练习"}'])
    state = init_state("while 循环怎么用？")
    state["mode"] = "question"
    state["question_text"] = "while 循环怎么用？"

    result = generate_practice(state, llm)

    assert result["practice"] == "请你再写一个 while 循环练习"


def test_summarize_result_updates_summary_and_history() -> None:
    state = init_state("什么是函数？", history=[{"user": "什么是变量？", "answer": "变量是名字"}])
    state["mode"] = "question"
    state["answer"] = "函数是一段可重复使用的代码"
    state["practice"] = "请你自己写一个 greet 函数"

    result = summarize_result(state)

    assert "【编程问题讲解】" in result["summary"]
    assert "函数是一段可重复使用的代码" in result["summary"]
    assert result["history"][-1]["user"] == "什么是函数？"
