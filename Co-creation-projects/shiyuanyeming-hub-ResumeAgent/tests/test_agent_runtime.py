from types import SimpleNamespace

import pytest

from resume_agent.agents.runtime import (
    AgentRuntimeSettings,
    FreshAgentRunner,
    build_mentor_runtime,
)
from resume_agent.agents.unavailable import AgentUnavailableError


VALID_ENV = {
    "LLM_MODEL_ID": "deepseek-chat",
    "LLM_API_KEY": "sk-real-test-value",
    "LLM_BASE_URL": "https://api.deepseek.com",
    "LLM_TIMEOUT": "45",
    "LLM_TEMPERATURE": "0.15",
    "LLM_MAX_TOKENS": "4096",
}


def test_settings_parse_supported_environment_values():
    settings = AgentRuntimeSettings.from_environ(VALID_ENV)

    assert settings.model == "deepseek-chat"
    assert settings.api_key.get_secret_value() == "sk-real-test-value"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.timeout == 45
    assert settings.temperature == 0.15
    assert settings.max_tokens == 4096


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"LLM_MODEL_ID": ""}, "LLM_MODEL_ID"),
        ({"LLM_API_KEY": ""}, "LLM_API_KEY"),
        ({"LLM_API_KEY": "sk-your-api-key-here"}, "placeholder"),
        ({"LLM_BASE_URL": "api.deepseek.com"}, "HTTP"),
        ({"LLM_TIMEOUT": "0"}, "LLM_TIMEOUT"),
        ({"LLM_TEMPERATURE": "3"}, "LLM_TEMPERATURE"),
        ({"LLM_MAX_TOKENS": "64"}, "LLM_MAX_TOKENS"),
    ],
)
def test_settings_reject_incomplete_or_unsafe_configuration(changes, expected):
    values = {**VALID_ENV, **changes}

    with pytest.raises(ValueError, match=expected):
        AgentRuntimeSettings.from_environ(values)


def test_legacy_deepseek_key_is_supported():
    values = {**VALID_ENV, "LLM_API_KEY": "", "DEEPSEEK_API_KEY": "legacy-key"}

    settings = AgentRuntimeSettings.from_environ(values)

    assert settings.api_key.get_secret_value() == "legacy-key"


def test_missing_config_returns_degraded_runtime_without_loading_framework():
    loaded = False

    def loader():
        nonlocal loaded
        loaded = True
        raise AssertionError("framework must not load")

    runtime = build_mentor_runtime({}, framework_loader=loader)

    assert runtime.fact_auditor is None
    assert runtime.question_writer is None
    assert runtime.capabilities.mentor is False
    assert runtime.capabilities.status == "degraded"
    assert "LLM_MODEL_ID" in runtime.capabilities.reason
    assert loaded is False


def test_missing_framework_returns_safe_degraded_runtime():
    def loader():
        raise ImportError("hello_agents missing")

    runtime = build_mentor_runtime(VALID_ENV, framework_loader=loader)

    assert runtime.capabilities.mentor is False
    assert runtime.capabilities.framework == "HelloAgents"
    assert "install" in runtime.capabilities.reason.lower()
    assert "sk-real-test-value" not in runtime.capabilities.model_dump_json()


def test_runtime_passes_exact_settings_without_calling_model():
    llm_calls = []
    agent_calls = []

    class FakeLLM:
        def __init__(self, **kwargs):
            llm_calls.append(kwargs)

    class FakeAgent:
        def __init__(self, **kwargs):
            agent_calls.append(kwargs)

        def run(self, prompt):
            if "事实审计" in self_kwargs(self)["name"]:
                return '{"dimension":"action","values":[{"text":"搭建看板"}]}'
            return '{"question":"你本人具体采取了什么行动？"}'

    def self_kwargs(instance):
        return next(item for item in agent_calls if item.get("_instance") is instance)

    original_init = FakeAgent.__init__

    def remembering_init(self, **kwargs):
        kwargs["_instance"] = self
        original_init(self, **kwargs)

    FakeAgent.__init__ = remembering_init

    runtime = build_mentor_runtime(
        VALID_ENV,
        framework_loader=lambda: SimpleNamespace(
            HelloAgentsLLM=FakeLLM,
            SimpleAgent=FakeAgent,
        ),
    )

    assert runtime.capabilities.mentor is True
    assert runtime.capabilities.model == "deepseek-chat"
    assert llm_calls == [
        {
            "model": "deepseek-chat",
            "api_key": "sk-real-test-value",
            "base_url": "https://api.deepseek.com",
            "timeout": 45,
            "temperature": 0.15,
            "max_tokens": 4096,
        }
    ]
    assert agent_calls == []


def test_fresh_runner_never_reuses_stateful_agent():
    instances = []

    class Agent:
        def __init__(self):
            instances.append(self)

        def run(self, prompt):
            return f"{prompt}:{len(instances)}"

    runner = FreshAgentRunner(Agent)

    assert runner.run("first") == "first:1"
    assert runner.run("second") == "second:2"
    assert instances[0] is not instances[1]


def test_fresh_runner_converts_provider_error_to_safe_unavailable_error():
    class BrokenAgent:
        def run(self, prompt):
            raise RuntimeError("provider rejected sk-secret-value")

    with pytest.raises(AgentUnavailableError) as error:
        FreshAgentRunner(BrokenAgent).run("prompt")

    assert "provider" not in str(error.value).lower()
    assert "sk-secret-value" not in str(error.value)


def test_runtime_disables_framework_persistence_for_sensitive_resume_prompts():
    configs = []
    agents = []

    class FakeConfig:
        def __init__(self, **kwargs):
            configs.append(kwargs)

    class FakeLLM:
        def __init__(self, **kwargs):
            pass

    class FakeAgent:
        def __init__(self, **kwargs):
            agents.append(kwargs)

        def run(self, prompt):
            return "{}"

    runtime = build_mentor_runtime(
        VALID_ENV,
        framework_loader=lambda: SimpleNamespace(
            Config=FakeConfig,
            HelloAgentsLLM=FakeLLM,
            SimpleAgent=FakeAgent,
        ),
    )

    runtime.fact_auditor.runner.factory()

    assert configs == [
        {
            "trace_enabled": False,
            "session_enabled": False,
            "skills_enabled": False,
            "todowrite_enabled": False,
            "devlog_enabled": False,
            "subagent_enabled": False,
        }
    ]
    assert agents[0]["config"].__class__ is FakeConfig
