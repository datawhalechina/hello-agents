"""Native model connection and cancellation tests with synthetic HTTP only."""
import json

import httpx
from openai import OpenAI
import pytest

from hello_agents.core.llm_adapters import OpenAIAdapter

from app.agents.orchestrator import WorkflowOrchestrator
from app.extraction import remote
from app.schemas import StandardMessage


MODEL = "synthetic-connection-model"
KEY = "synthetic-secret-never-echo"
BASE = "https://connection-fixture.invalid/v1"


def completion(content="OK"):
    return {"id": "synthetic-completion", "object": "chat.completion", "created": 0,
            "model": MODEL, "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}}


def native_transport(monkeypatch, handler):
    requests, clients, adapters = [], [], []

    def transport(request):
        requests.append(json.loads(request.content))
        assert request.method == "POST" and request.url.path == "/v1/chat/completions"
        return handler(request)

    def client(adapter):
        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.timeout == 10
        adapters.append(adapter)
        http = httpx.Client(transport=httpx.MockTransport(transport), timeout=1)
        sdk = OpenAI(api_key=adapter.api_key, base_url=adapter.base_url, max_retries=0, http_client=http)
        clients.append((sdk, http))
        return sdk

    monkeypatch.setattr(OpenAIAdapter, "create_client", client)
    return requests, clients, adapters


def assert_closed(clients, adapters):
    assert len(clients) == 1
    assert clients[0][0].is_closed() and clients[0][1].is_closed
    assert adapters[0]._client is None


def test_connection_uses_real_framework_sdk_and_only_fixed_nonenterprise_prompt(monkeypatch):
    requests, clients, adapters = native_transport(monkeypatch, lambda request: httpx.Response(200, json=completion(KEY)))
    result = remote.test_model_connection(MODEL, KEY, BASE)
    assert result["ok"] is True and result["latency_ms"] >= 0
    assert len(requests) == 1
    request = requests[0]
    assert request["model"] == MODEL and request["max_tokens"] == 16
    assert request.get("stream", False) is False and not request.get("tools")
    assert request["messages"] == [{"role": "system", "content": "This is a connection test. Reply only OK."},
                                   {"role": "user", "content": "请回复 OK。"}]
    assert KEY not in json.dumps(result)
    assert_closed(clients, adapters)


@pytest.mark.parametrize("status,expected", [(401, "认证失败"), (403, "认证失败"), (429, "限流"), (404, "不存在"), (503, "连接失败")])
def test_native_wrapped_http_errors_are_sanitized_and_clients_closed(monkeypatch, status, expected):
    requests, clients, adapters = native_transport(monkeypatch, lambda request: httpx.Response(status, json={"error": {"message": KEY, "type": "fixture_error"}}))
    result = remote.test_model_connection(MODEL, KEY, BASE)
    assert result["ok"] is False and expected in result["detail"]
    assert len(requests) == 1 and KEY not in json.dumps(result)
    assert_closed(clients, adapters)


@pytest.mark.parametrize("error_type,expected", [(httpx.ReadTimeout, "超时"), (httpx.ConnectError, "无法连接")])
def test_native_network_errors_are_mapped_without_returning_request_data(monkeypatch, error_type, expected):
    def handler(request):
        raise error_type(KEY, request=request)

    requests, clients, adapters = native_transport(monkeypatch, handler)
    result = remote.test_model_connection(MODEL, KEY, BASE)
    assert result["ok"] is False and expected in result["detail"]
    assert len(requests) == 1 and KEY not in json.dumps(result)
    assert_closed(clients, adapters)


def test_empty_response_is_not_reported_as_a_successful_connection(monkeypatch):
    requests, clients, adapters = native_transport(monkeypatch, lambda request: httpx.Response(200, json=completion("  ")))
    result = remote.test_model_connection(MODEL, KEY, BASE)
    assert not result["ok"] and "有效文本" in result["detail"]
    assert_closed(clients, adapters)


def test_missing_connection_fields_never_construct_a_client(monkeypatch):
    def deny(**kwargs):
        raise AssertionError("No HTTP client should be constructed")
    monkeypatch.setattr(remote, "HelloAgentsLLM", deny)
    assert remote.test_model_connection("", KEY, BASE)["ok"] is False
    assert remote.test_model_connection(MODEL, "", BASE)["ok"] is False
    assert remote.test_model_connection(MODEL, KEY, "")["ok"] is False


def source():
    return StandardMessage(id="synthetic-message", source_id="synthetic-source", sender="synthetic-author",
                           text="开始虚构接口测试", timestamp="2026-01-01T09:00:00+08:00")


def fake_reasoner(monkeypatch, cancel_check, responses):
    clients, calls = [], []

    class FakeLLM:
        def __init__(self, **kwargs):
            assert kwargs["provider"] == "openai"
            self.closed = False
            clients.append(self)
        def close(self):
            self.closed = True

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            pass
        def run_as_subagent(self, payload, **kwargs):
            calls.append(json.loads(payload))
            return {"success": True, "result": responses.pop(0)}

    monkeypatch.setattr(remote, "HelloAgentsLLM", FakeLLM)
    monkeypatch.setattr(remote, "SimpleAgent", FakeAgent)
    monkeypatch.setattr(remote.time, "sleep", lambda _: None)
    reasoner = remote.RemoteReasoner(external_llm_enabled=True, external_data_authorized=True,
                                    model=MODEL, api_key=KEY, base_url=BASE, max_seconds=600,
                                    cancel_check=cancel_check)
    return reasoner, clients, calls


def test_cancellation_before_first_transmission_makes_no_model_call(monkeypatch):
    reasoner, clients, calls = fake_reasoner(monkeypatch, lambda: True, [])
    try:
        with pytest.raises(remote.ModelAnalysisCancelled):
            reasoner.classify(source())
        assert calls == [] and reasoner.budget.max_seconds == 600
    finally:
        reasoner.close()
    assert clients[0].closed


def test_cancellation_between_attempts_prevents_the_retry(monkeypatch):
    checks = iter([False, True])
    reasoner, clients, calls = fake_reasoner(monkeypatch, lambda: next(checks), ["not valid json"])
    try:
        with pytest.raises(remote.ModelAnalysisCancelled):
            reasoner.classify(source())
        assert len(calls) == 1
    finally:
        reasoner.close()
    assert clients[0].closed


def test_orchestrator_forwards_budget_and_cancellation_and_closes_on_failure(monkeypatch):
    import app.agents.orchestrator as module
    received = []

    class CancelledReasoner:
        def __init__(self, **kwargs):
            received.append(kwargs)
            self.closed = False
            received.append(self)
        def classify(self, message):
            assert received[0]["cancel_check"]()
            raise remote.ModelAnalysisCancelled("Synthetic cancellation")
        def close(self):
            self.closed = True

    monkeypatch.setattr(module, "RemoteReasoner", CancelledReasoner)
    check = lambda: True
    orchestrator = WorkflowOrchestrator(provider="helloagents-llm", external_llm_enabled=True,
                                       external_data_authorized=True, llm_model=MODEL, llm_api_key=KEY,
                                       llm_base_url=BASE, remote_max_seconds=600, cancel_check=check)
    with pytest.raises(module.AnalysisError):
        orchestrator.analyze([source()])
    assert received[0]["max_seconds"] == 600 and received[0]["cancel_check"] is check
    assert received[1].closed
