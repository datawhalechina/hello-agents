import json

import pytest

from app.agents.orchestrator import WorkflowOrchestrator
from app.extraction import remote
from app.schemas import StandardMessage


def source():
    return StandardMessage(id="m", source_id="s", timestamp="2026-11-02T09:00:00+08:00", sender="工程师",
                           text="【北辰门户】开始接口开发", metadata={"private_secret": "NEVER_SEND_METADATA"})


@pytest.mark.parametrize("enabled,authorized", [(False, False), (True, False), (False, True)])
def test_remote_requires_both_explicit_opt_ins(enabled, authorized, monkeypatch):
    def deny(**kwargs):
        raise AssertionError("LLM constructed before authorization")
    monkeypatch.setattr(remote, "HelloAgentsLLM", deny)
    with pytest.raises(PermissionError):
        remote.RemoteReasoner(external_llm_enabled=enabled, external_data_authorized=authorized,
                              model="unit-test", api_key="fake", base_url="https://example.invalid/v1")


def setup_fake(monkeypatch, responses):
    calls = []
    class FakeLLM:
        def __init__(self, **kwargs):
            self.closed = False
        def close(self):
            self.closed = True
    class FakeAgent:
        def __init__(self, *args, **kwargs):
            assert kwargs["enable_tool_calling"] is False
        def run_as_subagent(self, payload, **kwargs):
            calls.append(json.loads(payload))
            return {"success": True, "result": responses.pop(0)}
    monkeypatch.setattr(remote, "HelloAgentsLLM", FakeLLM)
    monkeypatch.setattr(remote, "SimpleAgent", FakeAgent)
    monkeypatch.setattr(remote.time, "sleep", lambda _: None)
    reasoner = remote.RemoteReasoner(external_llm_enabled=True, external_data_authorized=True,
                                    model="unit-test", api_key="fake", base_url="https://example.invalid/v1")
    return reasoner, calls


def test_remote_retries_bad_json_and_sends_only_bounded_source_fields(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, ["invalid JSON", '{"classification":"work"}'])
    try:
        assert reasoner.classify(source()) == "work"
        assert len(calls) == 2
        assert set(calls[0]) == {"message_id", "source_id", "sender", "timestamp", "text"}
        assert "NEVER_SEND_METADATA" not in json.dumps(calls)
    finally:
        reasoner.close()
    assert reasoner.llm.closed


def test_remote_fabrication_exhausts_only_two_attempts(monkeypatch):
    fabricated = json.dumps({"facts": [{"kind": "task", "summary": "伪造交付", "quote": "伪造交付"}]})
    reasoner, calls = setup_fake(monkeypatch, [fabricated, fabricated])
    try:
        with pytest.raises(RuntimeError, match="after two attempts"):
            reasoner.extract(source())
        assert len(calls) == 2
    finally:
        reasoner.close()


def test_remote_cannot_set_trusted_labels(monkeypatch):
    trusted = json.dumps({"facts": [{"kind": "task", "summary": "开始接口开发", "quote": "开始接口开发", "verified": True, "review_status": "accepted"}]})
    reasoner, calls = setup_fake(monkeypatch, [trusted, trusted])
    try:
        with pytest.raises(RuntimeError):
            reasoner.extract(source())
        assert len(calls) == 2
    finally:
        reasoner.close()


def test_authorization_revocation_blocks_subsequent_transmission(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, ['{"classification":"work"}'])
    reasoner.external_data_authorized = False
    try:
        with pytest.raises(PermissionError):
            reasoner.classify(source())
        assert calls == []
    finally:
        reasoner.close()


def test_remote_oversize_input_never_transmits(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, [])
    try:
        with pytest.raises(ValueError, match="context budget"):
            reasoner.classify(source().model_copy(update={"text": "x" * 17000}))
        assert calls == []
    finally:
        reasoner.close()
