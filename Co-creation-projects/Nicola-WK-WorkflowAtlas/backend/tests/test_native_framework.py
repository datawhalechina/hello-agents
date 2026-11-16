"""Real HelloAgents/OpenAI SDK integration with only HTTP transport substituted.

Synthetic completion bodies are test fixtures; no model server is contacted.
The production HelloAgentsLLM, SimpleAgent, run_as_subagent, budget, native
request serialization and response parsing all execute unchanged.
"""
import json
import socket

import httpx
from openai import OpenAI

from hello_agents import HelloAgentsLLM
from hello_agents.core.llm_adapters import OpenAIAdapter

from app.agents.orchestrator import WorkflowOrchestrator
from app.schemas import StandardMessage


def test_real_native_subagent_and_llm_execute_through_mock_http_only(monkeypatch, tmp_path):
    import tiktoken
    from app.extraction import remote

    assert remote.HelloAgentsLLM is HelloAgentsLLM

    # TokenCounter uses this public encoding for unknown model names. Loading it
    # here allows the tokenizer cache to be prepared separately from the actual
    # network-denied native integration run. No enterprise data is used.
    tiktoken.get_encoding("cl100k_base")
    monkeypatch.chdir(tmp_path)
    requests = []
    clients = []
    adapters = []
    responses = [
        {"classification": "work"},
        {"facts": [{"kind": "task", "summary": "Start API task", "quote": "[project:Native] [task:API] Start API task",
                    "project_hint": "Native", "entity_key": "API", "status": "in_progress", "relations": []}]},
    ]

    original_connect = socket.socket.connect

    def deny_external_socket(instance, address):
        # Windows asyncio creates a loopback socket pair for its own wakeup pipe.
        # Permit that interpreter mechanism while blocking all external hosts.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(instance, address)
        raise AssertionError("Native framework integration attempted an external socket connection")

    def completion_transport(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and request.url.path == "/v1/chat/completions"
        assert request.url.host == "native-fixture.invalid"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "native-fixture-model"
        assert payload.get("stream", False) is False
        assert not payload.get("tools")
        answer = responses.pop(0)
        return httpx.Response(200, json={
            "id": f"chatcmpl-fixture-{len(requests)}", "object": "chat.completion", "created": 0,
            "model": "native-fixture-model", "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(answer)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 32, "completion_tokens": 16, "total_tokens": 48},
        })

    def real_client_with_test_transport(adapter):
        assert isinstance(adapter, OpenAIAdapter)
        adapters.append(adapter)
        http_client = httpx.Client(transport=httpx.MockTransport(completion_transport), timeout=1)
        sdk_client = OpenAI(api_key=adapter.api_key, base_url=adapter.base_url, timeout=1,
                            max_retries=0, http_client=http_client)
        clients.append((sdk_client, http_client))
        return sdk_client

    # Substitute only client construction to inject the bottom HTTP transport;
    # use the real OpenAI SDK and real adapter methods for every request.
    monkeypatch.setattr(OpenAIAdapter, "create_client", real_client_with_test_transport)
    monkeypatch.setattr(socket.socket, "connect", deny_external_socket)
    message = StandardMessage(id="native-m1", source_id="native-source", sender="synthetic-author",
                              text="[project:Native] [task:API] Start API task", timestamp="2026-11-06T09:00:00+08:00",
                              metadata={"private": "MUST_NOT_TRANSMIT_METADATA"})
    orchestrator = WorkflowOrchestrator(provider="helloagents-llm", external_llm_enabled=True,
                                       external_data_authorized=True, llm_model="native-fixture-model",
                                       llm_api_key="synthetic-test-key", llm_base_url="https://native-fixture.invalid/v1")
    result = orchestrator.analyze([message])

    assert result.provider == "helloagents-llm"
    assert len(result.agent_results) == 6 and all(stage.status == "completed" for stage in result.agent_results)
    assert len(requests) == 2 and responses == []
    assert len(clients) == 1 and len(adapters) == 1
    assert clients[0][0].is_closed() and clients[0][1].is_closed
    assert adapters[0]._client is None
    facts = result.proposal.facts
    assert len(facts) == 1 and facts[0].verified and facts[0].review_status == "pending"
    assert facts[0].summary == "Start API task" and facts[0].actor == "synthetic-author"
    assert facts[0].evidence[0].message_id == "native-m1"
    assert len(result.proposal.projects) == 1 and result.proposal.projects[0].name == "Native"
    assert len(result.proposal.nodes) == 1
    for request in requests:
        assert "MUST_NOT_TRANSMIT_METADATA" not in json.dumps(request)
        user_messages = [item for item in request["messages"] if item["role"] == "user"]
        assert len(user_messages) == 1
        source_payload = json.loads(user_messages[0]["content"])
        assert set(source_payload) == {"message_id", "source_id", "sender", "timestamp", "text"}
        assert source_payload["message_id"] == "native-m1"
