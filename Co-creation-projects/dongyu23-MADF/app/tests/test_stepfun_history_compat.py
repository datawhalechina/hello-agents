from hello_agents import Message

from app.agent.agent import normalize_framework_history


def test_summary_history_is_mapped_to_stepfun_supported_role():
    class TestAgent:
        _history = [
            Message(content="archived context", role="summary"),
            Message(content="recent reply", role="assistant"),
        ]

    agent = TestAgent()
    normalize_framework_history(agent)

    assert [message.role for message in agent._history] == ["user", "assistant"]
    assert agent._history[0].content == "archived context"
