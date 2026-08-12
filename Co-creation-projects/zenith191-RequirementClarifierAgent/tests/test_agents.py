"""HelloAgents 官方类集成测试。"""

from hello_agents import Config, SimpleAgent

from src.agents import build_agent_team
from src.config import LLMSettings
from src.tools import create_tool_registry


def test_build_agent_team_creates_four_official_simple_agents() -> None:
    settings = LLMSettings(
        model="test-model",
        api_key="test-secret-key",
        base_url="https://example.test/v1",
    )
    registry = create_tool_registry()

    team = build_agent_team(settings, registry)

    assert all(
        isinstance(agent, SimpleAgent)
        for agent in (team.analyst, team.architect, team.reviewer, team.synthesizer)
    )
    assert team.analyst.tool_registry is registry
    assert team.synthesizer.tool_registry is registry
    assert team.architect.tool_registry is None
    assert team.reviewer.tool_registry is None


def test_official_simple_agent_runs_with_offline_fake_llm() -> None:
    class FakeLLM:
        def invoke(self, messages, **kwargs) -> str:
            assert messages[-1]["content"] == "请澄清这个需求"
            return "待确认：目标用户和验收标准。"

    agent = SimpleAgent(
        name="离线框架集成测试",
        llm=FakeLLM(),  # type: ignore[arg-type]
        config=Config(debug=False),
    )

    result = agent.run("请澄清这个需求")

    assert result == "待确认：目标用户和验收标准。"


def test_official_simple_agent_can_call_requirement_tool_with_plain_text() -> None:
    class ToolCallingFakeLLM:
        def __init__(self) -> None:
            self.responses = iter(
                [
                    "[TOOL_CALL:requirement_audit:面向居民做一个活动报名小程序]",
                    "需求初检已经完成。",
                ]
            )
            self.calls = []

        def invoke(self, messages, **kwargs) -> str:
            self.calls.append(messages)
            return next(self.responses)

    fake_llm = ToolCallingFakeLLM()
    agent = SimpleAgent(
        name="工具调用集成测试",
        llm=fake_llm,  # type: ignore[arg-type]
        config=Config(debug=False),
        tool_registry=create_tool_registry(),
    )

    result = agent.run("请检查需求完整度")

    assert result == "需求初检已经完成。"
    assert '"ok": true' in fake_llm.calls[1][-1]["content"]
