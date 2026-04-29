from tutor.state import init_state


def test_init_state_uses_default_values() -> None:
    state = init_state("什么是列表推导式？")

    assert state["user_input"] == "什么是列表推导式？"
    assert state["mode"] == ""
    assert state["question_text"] == ""
    assert state["code_text"] == ""
    assert state["history"] == []
    assert state["answer"] == ""
    assert state["practice"] == ""
    assert state["summary"] == ""


def test_init_state_copies_history() -> None:
    history = [{"user": "上一次问题", "answer": "上一次回答"}]

    state = init_state(history=history)
    history.append({"user": "新问题", "answer": "新回答"})

    assert state["history"] == [{"user": "上一次问题", "answer": "上一次回答"}]
