from tutor.graph import build_tutor_graph, route_mode
from tutor.model import FakeLLMAdapter
from tutor.state import init_state


def test_route_mode_points_question_to_answer_node() -> None:
    assert route_mode({"mode": "question"}) == "answer_question"


def test_route_mode_points_review_to_review_node() -> None:
    assert route_mode({"mode": "review"}) == "review_code"


def test_graph_runs_question_flow() -> None:
    llm = FakeLLMAdapter([
        '{"answer": "for 循环适合遍历，while 循环适合按条件重复执行"}',
        '{"practice": "请你分别写一个 for 和 while 的例子"}',
    ])
    graph = build_tutor_graph(llm).compile()

    result = graph.invoke(init_state(user_input="for 和 while 有什么区别？"))

    assert result["mode"] == "question"
    assert "【编程问题讲解】" in result["summary"]
    assert "for 循环适合遍历" in result["summary"]
    assert "请你分别写一个 for 和 while 的例子" in result["summary"]


def test_graph_runs_review_flow() -> None:
    llm = FakeLLMAdapter([
        '{"answer": "这段代码的主要问题是函数定义后少了冒号"}',
        '{"practice": "请你补全冒号后再写一个 subtract 函数"}',
    ])
    graph = build_tutor_graph(llm).compile()
    user_input = "请帮我看看\n```python\ndef add(a, b)\n    return a + b\n```"

    result = graph.invoke(init_state(user_input=user_input))

    assert result["mode"] == "review"
    assert "【代码点评结果】" in result["summary"]
    assert "函数定义后少了冒号" in result["summary"]
    assert "subtract 函数" in result["summary"]
