import json
from types import SimpleNamespace

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.config import ModelConfigInput, save_config
from app.engine import Engine, ModelError
from app.main import create_app
from app.schemas import AnalysisOutput
from app import demo
from app.usage import CURRENT_CALL, begin_call, end_call, instrument, public_usage


@pytest.fixture
def clean_config(monkeypatch):
    for name in ("API_KEY", "BASE_URL", "MODEL", "MAX_TOKENS"):
        monkeypatch.delenv("OFFERNOTE_" + name, raising=False)
    # save_config writes process env; monkeypatch owns restoration for these keys.
    for name in ("API_KEY", "BASE_URL", "MODEL", "MAX_TOKENS"):
        monkeypatch.setenv("OFFERNOTE_" + name, "")


def test_save_preserves_key_comments_other_values_and_reload(tmp_path, clean_config):
    env = tmp_path / ".env"
    env.write_text("# keep this\nOTHER=value\n", encoding="utf-8")
    secret = "test-$token-${do_not_expand}-'quote'-\\slash"
    config = ModelConfigInput(
        base_url="https://example.com/v1/", model="test-model", api_key=secret
    )
    first = save_config(config, env)
    assert first["configured"] and first["api_key_configured"]
    assert secret not in json.dumps(first)
    assert dotenv_values(env, interpolate=False)["OFFERNOTE_API_KEY"] == secret
    assert "# keep this" in env.read_text() and "OTHER=value" in env.read_text()
    second = save_config(
        ModelConfigInput(base_url="https://example.com/v1", model="updated"), env
    )
    assert second["model"] == "updated"
    assert dotenv_values(env, interpolate=False)["OFFERNOTE_API_KEY"] == secret
    assert env.read_text().count("OFFERNOTE_API_KEY=") == 1


def test_settings_api_redaction_validation_and_origin(tmp_path, clean_config):
    env = tmp_path / ".env"
    with TestClient(create_app(str(tmp_path / "test.sqlite3"), env)) as client:
        body = {
            "base_url": "https://example.com/v1",
            "model": "test",
            "api_key": "private-test-key",
        }
        assert (
            client.put(
                "/api/settings",
                json=body,
                headers={"Origin": "https://foreign.example"},
            ).status_code
            == 403
        )
        assert not env.exists()
        assert (
            client.put(
                "/api/settings",
                json={**body, "base_url": "https://example.com/v1/chat/completions"},
            ).status_code
            == 422
        )
        saved = client.put("/api/settings", json=body)
        assert saved.status_code == 200 and saved.json()["configured"]
        assert "private-test-key" not in saved.text
        assert "private-test-key" not in client.get("/api/settings").text
        invalid = client.put(
            "/api/settings", json={**body, "api_key": {"secret": "private-test-key"}}
        )
        assert invalid.status_code == 422 and "private-test-key" not in invalid.text


def fake_llm(responses):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_: next(responses))
        ),
        close=lambda: None,
    )
    return SimpleNamespace(_client=client)


def response(finish="stop", usage=True):
    return SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        if usage
        else None,
        choices=[SimpleNamespace(finish_reason=finish)],
    )


def test_usage_counts_tool_rounds_retries_and_truncation():
    state, token = begin_call({})
    try:
        llm = instrument(fake_llm(iter([response(), response("length")])))
        llm._client.chat.completions.create()
        with pytest.raises(ModelError, match="Token 上限"):
            llm._client.chat.completions.create()
        usage = public_usage(state)
        assert (
            usage["tokens"] == 60
            and usage["input_tokens"] == 20
            and usage["output_tokens"] == 40
        )
        assert usage["usage_complete"] and usage["finish_reason"] == "length"
    finally:
        end_call(state, token)
    assert CURRENT_CALL.get() is None


def test_missing_usage_is_not_zero():
    state, token = begin_call({})
    try:
        llm = instrument(fake_llm(iter([response(usage=False)])))
        llm._client.chat.completions.create()
        assert public_usage(state)["tokens"] is None
        assert not public_usage(state)["usage_complete"]
    finally:
        end_call(state, token)


def test_long_generation_timeout_and_no_implicit_sdk_retries(monkeypatch, clean_config):
    for key, value in {
        "API_KEY": "local-test-key",
        "BASE_URL": "https://example.com/v1",
        "MODEL": "test",
    }.items():
        monkeypatch.setenv("OFFERNOTE_" + key, value)
    llm = Engine.make_llm()
    try:
        assert llm.timeout == 120
        assert llm._client.max_retries == 0
    finally:
        llm._client.close()


def test_wrapped_timeout_is_classified_without_leaking_details(
    monkeypatch, clean_config
):
    import httpx
    from openai import APITimeoutError
    from openai.resources.chat.completions import Completions

    for key, value in {
        "API_KEY": "local-test-key",
        "BASE_URL": "https://example.com/v1",
        "MODEL": "test",
    }.items():
        monkeypatch.setenv("OFFERNOTE_" + key, value)

    def fail(*_, **__):
        try:
            raise httpx.ReadTimeout("sensitive-provider-details")
        except httpx.ReadTimeout as exc:
            raise APITimeoutError(
                request=httpx.Request("POST", "https://example.com/v1/chat/completions")
            ) from exc

    monkeypatch.setattr(Completions, "create", fail)
    events = []
    engine = Engine(SimpleNamespace(event=lambda _id, event: events.append(event)))
    with pytest.raises(ModelError, match="模型生成超时") as caught:
        engine.call("test", "live", "analysis", {}, AnalysisOutput, lambda: {})
    assert "sensitive-provider-details" not in str(caught.value)
    assert events[0]["status"] == "error"


def test_contract_repair_once_and_failure_is_explicit():
    good = json.dumps(demo.analyze(demo.RESUME, demo.JOB), ensure_ascii=False)
    calls = []
    outputs = iter(['{"summary":"only summary"}', good])
    agent = SimpleNamespace(run=lambda prompt: (calls.append(prompt), next(outputs))[1])
    assert Engine(None).structured_run(agent, {}, AnalysisOutput)["claims"]
    assert len(calls) == 2 and "requirements" in calls[1]
    failing = SimpleNamespace(run=lambda _: "{}")
    with pytest.raises(ModelError, match="自动修正一次"):
        Engine(None).structured_run(failing, {}, AnalysisOutput)


def test_reasoning_exhaustion_is_reported_as_truncation_through_helloagents(
    monkeypatch, clean_config
):
    from openai.resources.chat.completions import Completions
    from openai.types.chat import ChatCompletion

    for key, value in {
        "API_KEY": "local-test-key",
        "BASE_URL": "https://example.com/v1",
        "MODEL": "test",
    }.items():
        monkeypatch.setenv("OFFERNOTE_" + key, value)
    response = ChatCompletion.model_validate(
        {
            "id": "truncated",
            "created": 0,
            "object": "chat.completion",
            "model": "test",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "length",
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "reasoning_content": "not an answer",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 1032,
                "completion_tokens": 6000,
                "total_tokens": 7032,
            },
        }
    )
    monkeypatch.setattr(Completions, "create", lambda *_, **__: response)
    events = []
    engine = Engine(SimpleNamespace(event=lambda _id, event: events.append(event)))
    with pytest.raises(ModelError, match="Token 上限"):
        engine.call(
            "test",
            "live",
            "analysis",
            {"resume": demo.RESUME, "job": demo.JOB},
            AnalysisOutput,
            lambda: {},
        )
    assert events[0]["tokens"] == 7032 and events[0]["status"] == "error"
    assert events[0]["finish_reason"] == "length" and events[0]["repairs"] == 0
    assert CURRENT_CALL.get() is None


def test_atomic_write_failure_preserves_existing_config(
    tmp_path, monkeypatch, clean_config
):
    from pathlib import Path
    from app.config import config_values

    env = tmp_path / ".env"
    env.write_text("OTHER=value\n", encoding="utf-8")

    def fail(*_):
        raise OSError("simulated write failure")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError):
        save_config(
            ModelConfigInput(
                base_url="https://example.com/v1",
                model="test",
                api_key="local-test-key",
            ),
            env,
        )
    assert env.read_text() == "OTHER=value\n"
    assert not config_values()["API_KEY"]
    assert list(tmp_path.glob(".env-*.tmp")) == []
