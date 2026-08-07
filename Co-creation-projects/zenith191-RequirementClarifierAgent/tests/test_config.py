"""配置读取测试。"""

import pytest

from src.config import ConfigurationError, LLMSettings


ENV_NAMES = (
    "LLM_MODEL_ID",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT",
)


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_settings_from_env_reads_valid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL_ID", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "secret-for-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
    monkeypatch.setenv("LLM_TIMEOUT", "30")

    settings = LLMSettings.from_env()

    assert settings.model == "test-model"
    assert settings.temperature == 0.3
    assert settings.timeout == 30


def test_settings_reject_missing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)

    with pytest.raises(ConfigurationError, match="LLM_MODEL_ID"):
        LLMSettings.from_env()


def test_settings_reject_placeholder_key() -> None:
    settings = LLMSettings(
        model="test-model",
        api_key="your_api_key_here",
        base_url="https://example.test/v1",
    )

    with pytest.raises(ConfigurationError, match="占位符"):
        settings.validate()


@pytest.mark.parametrize(
    ("temperature", "timeout", "message"),
    [(-0.1, 30, "TEMPERATURE"), (0.2, 0, "TIMEOUT")],
)
def test_settings_reject_out_of_range_values(
    temperature: float, timeout: int, message: str
) -> None:
    settings = LLMSettings(
        model="test-model",
        api_key="secret-for-test",
        base_url="https://example.test/v1",
        temperature=temperature,
        timeout=timeout,
    )

    with pytest.raises(ConfigurationError, match=message):
        settings.validate()
