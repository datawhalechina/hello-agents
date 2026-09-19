from unittest.mock import MagicMock, patch

from hello_agents.tools import ToolResponse, ToolStatus

from app.agent.real_god import RealGodAgent, _StepSearchToolAdapter


def test_real_god_builds_react_agent_with_registered_stepsearch_tool():
    registry = MagicMock()
    react_agent = MagicMock()
    with patch.object(RealGodAgent, "_supports_persona_search", return_value=True), patch(
        "app.agent.real_god.ToolRegistry", return_value=registry
    ), patch(
        "app.agent.real_god.ReActAgent", return_value=react_agent
    ) as react_class, patch("app.agent.real_god.create_helloagents_llm"), patch(
        "app.agent.real_god.create_helloagents_config"
    ):
        result = RealGodAgent(max_steps=4)._build_agent("system")

    assert result is react_agent
    tool = registry.register_tool.call_args.args[0]
    assert isinstance(tool, _StepSearchToolAdapter)
    react_class.assert_called_once()
    assert react_class.call_args.kwargs["tool_registry"] is registry
    assert react_class.call_args.kwargs["max_steps"] == 4


def test_real_god_rejects_non_stepfun_provider():
    registry = MagicMock()
    with patch.object(RealGodAgent, "_supports_persona_search", return_value=False), patch(
        "app.agent.real_god.ToolRegistry", return_value=registry
    ):
        try:
            RealGodAgent()._build_agent("system")
        except RuntimeError as exc:
            assert "StepFun" in str(exc)
        else:
            raise AssertionError("non-StepFun provider should be rejected")

    registry.register_tool.assert_not_called()


def test_stepsearch_adapter_exposes_structured_helloagents_tool():
    backend = MagicMock()
    backend.search.return_value = "search result"
    tool = _StepSearchToolAdapter(backend)

    response = tool.run({"query": "Ada Lovelace"})

    assert response.status is ToolStatus.SUCCESS
    assert response.data["provider"] == "stepsearch"
    backend.search.assert_called_once_with("Ada Lovelace")


def test_real_god_run_emits_valid_result_events():
    framework_agent = MagicMock()
    framework_agent.run.return_value = '{"name":"Ada Lovelace","title":"Mathematician","bio":"Bio","theories":["1","2","3","4","5","6","7"],"stance":"Analytical","system_prompt":"I am Ada."}'
    agent = RealGodAgent()
    with patch.object(agent, "_build_agent", return_value=framework_agent), patch.object(
        agent, "_matches_user_request", return_value=True
    ):
        events = list(agent.run("create one", n=1))

    assert [event["type"] for event in events] == ["count", "thought_start", "progress", "result"]
    assert events[-1]["content"][0]["name"] == "Ada Lovelace"


def test_real_god_repairs_truncated_provider_json_once():
    framework_agent = MagicMock()
    framework_agent.run.side_effect = ["{\"name\": \"Ada", "{\"name\": \"Ada Lovelace\", \"title\": \"Math\", \"bio\": \"Bio\", \"theories\": [\"1\",\"2\",\"3\",\"4\",\"5\",\"6\",\"7\"], \"stance\": \"Analytical\", \"system_prompt\": \"I am Ada.\"}"]
    agent = RealGodAgent()
    with patch.object(agent, "_build_agent", return_value=framework_agent), patch.object(
        agent, "_matches_user_request", return_value=True
    ):
        events = list(agent.run("create one", n=1))

    assert [event["type"] for event in events] == ["count", "thought_start", "progress", "result"]
    assert framework_agent.run.call_count == 2
    assert events[-1]["content"][0]["name"] == "Ada Lovelace"


def test_real_god_retries_with_fresh_agent_when_persona_is_off_topic():
    wrong_agent = MagicMock()
    wrong_agent.run.return_value = '{"name":"Marie Curie","title":"Scientist","bio":"Bio","theories":["1","2","3","4","5","6","7"],"stance":"Science","system_prompt":"I am Marie."}'
    corrected_agent = MagicMock()
    corrected_agent.run.return_value = '{"name":"Edsger Dijkstra","title":"Computer Scientist","bio":"Bio","theories":["1","2","3","4","5","6","7"],"stance":"Structured programming","system_prompt":"I am Dijkstra."}'
    agent = RealGodAgent()

    with patch.object(agent, "_build_agent", side_effect=[wrong_agent, corrected_agent]), patch.object(
        agent, "_matches_user_request", side_effect=[False, True]
    ):
        events = list(agent.run("Create Edsger Dijkstra", n=1))

    assert events[-1]["content"][0]["name"] == "Edsger Dijkstra"
    assert "Marie Curie" in corrected_agent.run.call_args.args[0]


def test_multi_persona_generation_pins_each_agent_to_requested_position():
    first_agent = MagicMock()
    first_agent.run.return_value = '{"name":"Teacher A","title":"Innovator","bio":"Bio","theories":["1","2","3","4","5","6","7"],"stance":"Support","system_prompt":"I support adoption."}'
    second_agent = MagicMock()
    second_agent.run.return_value = '{"name":"Teacher B","title":"Ethicist","bio":"Bio","theories":["1","2","3","4","5","6","7"],"stance":"Cautious","system_prompt":"I focus on risks."}'
    agent = RealGodAgent()

    with patch.object(agent, "_build_agent", side_effect=[first_agent, second_agent]), patch.object(
        agent, "_matches_user_request", return_value=True
    ) as alignment:
        events = list(agent.run("第一位支持课堂 AI；第二位强调学术诚信风险", n=2))

    results = [event["content"][0]["name"] for event in events if event["type"] == "result"]
    assert results == ["Teacher A", "Teacher B"]
    assert "第 1 个描述" in first_agent.run.call_args.args[0]
    assert "第 2 个描述" in second_agent.run.call_args.args[0]
    assert "当前只校验第 1 位" in alignment.call_args_list[0].args[0]
    assert "当前只校验第 2 位" in alignment.call_args_list[1].args[0]
    assert "Teacher A" in alignment.call_args_list[1].args[0]


def test_explicit_named_person_is_checked_before_model_alignment():
    with patch("app.agent.real_god.run_simple_agent") as completion:
        assert RealGodAgent._matches_user_request(
            "创建哈利波特",
            {"name": "阿斯特拉·韦斯莱-布莱克"},
        ) is False

    completion.assert_not_called()


def test_explicit_named_person_allows_name_punctuation_variants():
    with patch("app.agent.real_god.run_simple_agent", return_value="YES"):
        assert RealGodAgent._matches_user_request(
            "创建阿不思邓布利多",
            {"name": "阿不思·邓布利多"},
        ) is True


def test_explicit_named_person_allows_translated_name_when_bio_confirms_identity():
    with patch("app.agent.real_god.run_simple_agent", return_value="YES"):
        assert RealGodAgent._matches_user_request(
            "创建哈利波特",
            {
                "name": "Harry Potter",
                "bio": "哈利·波特是霍格沃茨格兰芬多学院的学生。",
            },
        ) is True


def test_topic_request_does_not_force_persona_name():
    assert RealGodAgent._explicit_requested_name("创建一位算法专家") is None
    assert RealGodAgent._explicit_requested_name("生成一个科学家角色") is None


def test_long_named_person_prompt_forces_single_person_without_model_counting():
    prompt = "请联网核实并创建真实人物王佑镁，作为教育伦理讨论角色。必须生成王佑镁本人。"
    agent = RealGodAgent()

    with patch("app.agent.real_god.run_simple_agent") as completion:
        assert agent._explicit_requested_name(prompt) == "王佑镁"
        assert agent._get_persona_count(prompt) == 1

    completion.assert_not_called()


def test_stepsearch_adapter_converts_provider_errors():
    backend = MagicMock()
    backend.search.side_effect = RuntimeError("offline")
    response = _StepSearchToolAdapter(backend).run({"query": "Ada Lovelace"})
    assert isinstance(response, ToolResponse)
    assert response.status is ToolStatus.ERROR
    assert response.error_info["code"] == "SEARCH_FAILED"
