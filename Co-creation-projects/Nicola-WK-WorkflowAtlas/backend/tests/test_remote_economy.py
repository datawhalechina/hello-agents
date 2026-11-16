import json

import httpx
import pytest
from hello_agents.core.llm_adapters import OpenAIAdapter
from openai import OpenAI

from app.agents.orchestrator import WorkflowOrchestrator
from app.extraction import remote
from app.schemas import StandardMessage


def message(identity="m", text="开始开发"):
    return StandardMessage(id=identity, source_id="synthetic", sender="测试",
                           timestamp="2026-11-10T09:00:00+08:00", text=text,
                           metadata={"secret": "NEVER_TRANSMIT_METADATA"})


def response(payload):
    return {"messages": [{"message_id": item["message_id"], "facts": [
        {"kind": "task", "quote": item["text"]}
    ]} for item in payload["messages"]]}


def setup_fake(monkeypatch, handler=response, max_calls=60):
    calls = []

    class LLM:
        def __init__(self, **kwargs):
            self.max_tokens = kwargs["max_tokens"]
            self.closed = False

        def close(self):
            self.closed = True

    class Agent:
        def __init__(self, *args, **kwargs):
            assert kwargs["enable_tool_calling"] is False

        def run_as_subagent(self, text, **kwargs):
            payload = json.loads(text)
            calls.append(payload)
            result = handler(payload)
            if result is None:
                return {"success": False, "metadata": {"error": "子任务未完成：output_limit"}}
            return {"success": True, "result": json.dumps(result, ensure_ascii=False)}

    monkeypatch.setattr(remote, "HelloAgentsLLM", LLM)
    monkeypatch.setattr(remote, "SimpleAgent", Agent)
    reasoner = remote.RemoteReasoner(external_llm_enabled=True, external_data_authorized=True,
                                    model="synthetic", api_key="synthetic", base_url="https://synthetic.invalid/v1",
                                    max_calls=max_calls)
    return reasoner, calls


def test_216_short_messages_use_44_calls_without_classification(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch)
    facts = reasoner.extract_many([message(str(index), f"开始开发{index}") for index in range(216)])
    assert len(calls) == 44 and len(facts) == 216
    assert all(len(call["messages"]) <= 5 and sum(len(item["text"]) for item in call["messages"]) <= 1800 for call in calls)
    assert "NEVER_TRANSMIT_METADATA" not in json.dumps(calls)


def test_long_message_segments_preserve_tail_and_original_identity(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch)
    original = message(text="首段开始开发\n" + "中" * 2101 + "\n尾部完成验收")
    facts = reasoner.extract_many([original])
    pieces = [item["text"] for call in calls for item in call["messages"]]
    assert "".join(pieces) == original.text
    assert max(map(len, pieces)) <= 800
    assert any("尾部完成验收" in fact.evidence[0].quote for fact in facts)
    assert all(fact.evidence[0].message_id == original.id and fact.evidence[0].quote in original.text for fact in facts)


def test_truncation_splits_input_without_increasing_tokens(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, lambda payload: None if len(payload["messages"]) > 1 else response(payload))
    facts = reasoner.extract_many([message(str(index)) for index in range(5)])
    assert len(facts) == 5 and len(calls) == 9
    assert reasoner.llm.max_tokens == 3000


def test_single_segment_truncation_is_explicit_bounded_failure(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, lambda payload: None)
    with pytest.raises(remote.ModelResponseError, match="Single segment") as caught:
        reasoner.extract_many([message()])
    assert "长度上限" in caught.value.public_detail and len(calls) == 1


def test_truncated_single_message_splits_to_small_exact_segments(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, lambda payload: None if len(payload["messages"][0]["text"]) > 200 else response(payload))
    original = message(text="开始" + "".join(chr(0x4e00 + index) for index in range(697)) + "尾部完成")
    facts = reasoner.extract_many([original])
    assert len(calls) == 7
    assert "".join(fact.evidence[0].quote for fact in facts) == original.text
    assert all(fact.evidence[0].message_id == original.id for fact in facts)


@pytest.mark.parametrize("malformation", ["cross_message", "fabrication", "missing", "duplicate", "unknown", "trusted"])
def test_batch_identity_and_evidence_are_strict(monkeypatch, malformation):
    def handler(payload):
        result = response(payload)
        item = result["messages"][0]
        if malformation == "cross_message":
            item["facts"][0].update(quote="另一条独有内容", summary="另一条独有内容")
        elif malformation == "fabrication":
            item["facts"][0].update(quote="不存在的伪造事实", summary="不存在的伪造事实")
        elif malformation == "missing":
            result["messages"].pop()
        elif malformation == "duplicate":
            result["messages"].append(item)
        elif malformation == "unknown":
            item["message_id"] = "unknown"
        else:
            item["facts"][0]["verified"] = True
        return result

    reasoner, calls = setup_fake(monkeypatch, handler)
    with pytest.raises(remote.ModelResponseError):
        reasoner.extract_many([message("a"), message("b", "另一条独有内容")])
    assert len(calls) == 2


def test_duplicate_input_and_facts_deduplicate_but_conflicts_fail(monkeypatch):
    def handler(payload):
        result = response(payload)
        result["messages"][0]["facts"] *= 2
        return result

    reasoner, calls = setup_fake(monkeypatch, handler)
    assert len(reasoner.extract_many([message(), message()])) == 1 and len(calls) == 1
    with pytest.raises(ValueError, match="Conflicting"):
        reasoner.extract_many([message(), message(text="另一个版本")])
    with pytest.raises(ValueError, match="one source"):
        reasoner.extract_many([message(), message("b").model_copy(update={"source_id": "other"})])


def test_budget_is_hard_capped_even_when_fake_agent_ignores_run_budget(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch, max_calls=1000)
    with pytest.raises(remote.ModelResponseError, match="budget exhausted"):
        reasoner.extract_many([message(str(index)) for index in range(301)])
    assert len(calls) == 60


def test_economy_orchestrator_skips_classification_and_empty_messages(monkeypatch):
    reasoner, calls = setup_fake(monkeypatch)
    monkeypatch.setattr(remote.RemoteReasoner, "classify", lambda *args: pytest.fail("classification must be combined"))
    monkeypatch.setattr(remote.RemoteReasoner, "extract", lambda *args: pytest.fail("single extraction must be combined"))
    from app.agents import orchestrator
    monkeypatch.setattr(orchestrator, "RemoteReasoner", lambda **kwargs: reasoner)
    result = WorkflowOrchestrator("helloagents-llm", external_llm_enabled=True, external_data_authorized=True,
                                  economy_mode=True).analyze([message(), message("blank", "  \n")])
    assert len(result.proposal.facts) == 1 and result.proposal.facts[0].verified
    assert len(calls) == 1 and reasoner.llm.closed


def test_native_transport_combines_five_messages_and_preserves_evidence(monkeypatch):
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        batch = json.loads(payload["messages"][-1]["content"])
        content = json.dumps(response(batch), ensure_ascii=False)
        return httpx.Response(200, json={"id": "fixture", "object": "chat.completion", "created": 0,
            "model": "synthetic", "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                                  "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}})

    def client(adapter):
        return OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1", max_retries=0,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(OpenAIAdapter, "create_client", client)
    reasoner = remote.RemoteReasoner(external_llm_enabled=True, external_data_authorized=True,
                                    model="synthetic", api_key="synthetic", base_url="https://synthetic.invalid/v1")
    try:
        facts = reasoner.extract_many([message(str(index), f"开始开发{index}") for index in range(5)])
        assert len(facts) == 5 and len(sent) == 1 and sent[0]["max_tokens"] == 3000
        assert not sent[0].get("tools")
        assert "NEVER_TRANSMIT_METADATA" not in json.dumps(sent)
        assert {fact.evidence[0].message_id for fact in facts} == {str(index) for index in range(5)}
    finally:
        reasoner.close()
