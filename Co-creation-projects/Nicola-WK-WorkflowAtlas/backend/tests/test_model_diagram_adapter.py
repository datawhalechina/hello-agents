import json

import httpx
import pytest
from hello_agents.core.llm_adapters import OpenAIAdapter
from openai import OpenAI

from app.config import Settings
from app.extraction import direct
from app.extraction.remote import ModelAnalysisCancelled, ModelResponseError
from app.schemas import StandardMessage


SAVED = "# 工作报告\n工作线甲：准备、交付。实际交付时间未知。\n工作线乙：独立复核。"
DIAGRAM = "```mermaid\nflowchart TD\nsubgraph 甲\nA[准备] --> B[交付]\nend\nsubgraph 乙\nC[复核]\nend\n```"


def settings(**updates):
    values = dict(provider="helloagents-llm", external_llm_enabled=True, external_data_authorized=True,
                  llm_model="deepseek-flash", llm_api_key="SYNTHETIC_KEY", llm_base_url="https://api.deepseek.com/v1",
                  llm_thinking=False, _env_file=None)
    values.update(updates)
    return Settings(**values)


def native(monkeypatch, content=DIAGRAM, finish="stop", interrupt=False, status=200):
    sent, clients, bodies = [], [], []

    def event(delta=None, reason=None, usage=None):
        payload = {"id": "fixture", "object": "chat.completion.chunk", "created": 0, "model": "synthetic",
                   "choices": [{"index": 0, "delta": delta or {}, "finish_reason": reason}] if delta is not None or reason else []}
        if usage:
            payload["usage"] = usage
        return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode()

    class Body(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield event({"reasoning_content": "PRIVATE_REASONING"})
            yield event({"content": content})
            if interrupt:
                raise httpx.ReadError("PRIVATE_ERROR SYNTHETIC_KEY")
            yield event(reason=finish)
            yield event(usage={"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130})
            yield b"data: [DONE]\n\n"

        def close(self):
            self.closed = True

    def handler(request):
        sent.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "PRIVATE_ERROR SYNTHETIC_KEY"}})
        body = Body()
        bodies.append(body)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    def client(adapter):
        assert adapter.timeout == 180
        item = OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1", max_retries=2,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        clients.append(item)
        return item

    monkeypatch.setattr(OpenAIAdapter, "create_client", client)
    return sent, clients, bodies


def test_standard_report_prompt_requests_model_mermaid_with_50_messages_one_call(monkeypatch):
    sent, clients, bodies = native(monkeypatch, "原有自然 Markdown 报告\n\n" + DIAGRAM)
    source = [StandardMessage(id=f"private-id-{index}", source_id="private-source", sender="测试人",
                             timestamp="2026-11-10T09:00:00+08:00", text=f"原始消息{index}",
                             metadata={"secret": "PRIVATE_METADATA"}) for index in range(50)]
    answer = direct.DirectAnalyzer(settings()).analyze(source)
    assert len(sent) == 1 and answer.complete and answer.markdown.endswith(DIAGRAM)
    assert sent[0]["messages"][0]["content"] == direct.DIRECT_PROMPT
    assert len(direct.DIRECT_PROMPT) < 300 and "mermaid flowchart" in direct.DIRECT_PROMPT and "subgraph" in direct.DIRECT_PROMPT
    transcript = sent[0]["messages"][1]["content"]
    assert all(item.text in transcript for item in source)
    assert "PRIVATE_METADATA" not in transcript and "private-id" not in transcript
    assert "max_tokens" not in sent[0] and not sent[0].get("tools") and not sent[0].get("response_format")
    assert clients[0].max_retries == 0 and clients[0].is_closed() and bodies[0].closed


@pytest.mark.parametrize("config,expected_thinking", [({}, {"type": "disabled"}),
                                                        ({"llm_thinking": True}, {"type": "enabled"}),
                                                        ({"llm_base_url": "https://compatible.invalid/v1", "llm_thinking": True}, None)])
def test_diagram_sends_only_saved_text_under_short_diagram_instruction(monkeypatch, config, expected_thinking):
    sent, clients, bodies = native(monkeypatch)
    deltas = []
    answer = direct.DiagramAnalyzer(settings(**config)).analyze(SAVED, "PRIVATE_SOURCE_ID", on_delta=deltas.append)
    assert len(sent) == 1 and sent[0]["stream"] is True
    assert sent[0]["messages"][0]["content"] == direct.DIAGRAM_PROMPT
    assert len(direct.DIAGRAM_PROMPT) < 300
    transcript = sent[0]["messages"][1]["content"]
    assert transcript.endswith(SAVED) and transcript.count(SAVED) == 1
    assert all(private not in transcript for private in ["PRIVATE_SOURCE_ID", "saved-answer-diagram", "metadata", "原始消息", "[file message]"])
    assert answer.markdown == "".join(deltas) == DIAGRAM and "PRIVATE_REASONING" not in answer.model_dump_json()
    assert answer.complete and answer.usage == {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130}
    assert sent[0].get("thinking") == expected_thinking
    assert sent[0]["stream_options"] == {"include_usage": True} and "max_tokens" not in sent[0]
    assert clients[0].is_closed() and bodies[0].closed


def test_custom_instruction_is_keyword_only_and_legacy_default_unchanged(monkeypatch):
    sent, _, _ = native(monkeypatch)
    item = StandardMessage(id="m", source_id="s", sender="测试", timestamp="2026-11-10T09:00:00+08:00", text="正文")
    analyzer = direct.DirectAnalyzer(settings())
    analyzer.analyze([item], instruction="自定义的纯文字图示指令")
    assert sent[0]["messages"][0]["content"] == "自定义的纯文字图示指令"
    analyzer.analyze([item], instruction="")
    assert sent[1]["messages"][0]["content"] == direct.DIRECT_PROMPT
    with pytest.raises(TypeError):
        analyzer.analyze([item], None, None, "positional instruction")


def test_saved_answer_is_not_subject_to_imported_message_text_length_cap(monkeypatch):
    sent, _, _ = native(monkeypatch)
    saved = "已有报告" + "长" * 100001 + "保留尾部"
    answer = direct.DiagramAnalyzer(settings()).analyze(saved, "s")
    assert answer.complete and len(sent) == 1 and sent[0]["messages"][1]["content"].endswith(saved)


@pytest.mark.parametrize("finish,interrupt,expected", [("length", False, "length"), ("stop", True, "interrupted")])
def test_partial_diagram_preserves_exact_model_body_and_closes(monkeypatch, finish, interrupt, expected):
    sent, clients, bodies = native(monkeypatch, "```mermaid\nflowchart TD\nA[部分", finish, interrupt)
    answer = direct.DiagramAnalyzer(settings()).analyze(SAVED, "s")
    assert len(sent) == 1 and not answer.complete and answer.finish_reason == expected
    assert answer.markdown == "```mermaid\nflowchart TD\nA[部分"
    assert "PRIVATE_ERROR" not in answer.model_dump_json()
    assert clients[0].is_closed() and bodies[0].closed


def test_diagram_adapter_does_not_parse_or_repair_model_mermaid(monkeypatch):
    sent, _, _ = native(monkeypatch, "图示材料不足。\n```mermaid\nunsupported syntax exact original\n```")
    answer = direct.DiagramAnalyzer(settings()).analyze(SAVED, "s")
    assert answer.complete and "unsupported syntax exact original" in answer.markdown and len(sent) == 1


def test_diagram_cancel_keeps_public_draft_without_returning_success(monkeypatch):
    sent, clients, bodies = native(monkeypatch)
    draft = []
    with pytest.raises(ModelAnalysisCancelled):
        direct.DiagramAnalyzer(settings()).analyze(SAVED, "s", cancel_check=lambda: bool(draft), on_delta=draft.append)
    assert draft == [DIAGRAM] and len(sent) == 1 and clients[0].is_closed() and bodies[0].closed


def test_retryable_diagram_http_error_is_safe_single_request(monkeypatch):
    sent, clients, _ = native(monkeypatch, status=429)
    with pytest.raises(ModelResponseError) as caught:
        direct.DiagramAnalyzer(settings()).analyze(SAVED, "s")
    assert "PRIVATE_ERROR" not in str(caught.value) + caught.value.public_detail
    assert "SYNTHETIC_KEY" not in str(caught.value) + caught.value.public_detail
    assert len(sent) == 1 and clients[0].max_retries == 0 and clients[0].is_closed()


@pytest.mark.parametrize("saved,source", [("", "s"), ("  ", "s"), (None, "s"), (SAVED, ""), (SAVED, None)])
def test_missing_saved_answer_or_source_fails_before_client(monkeypatch, saved, source):
    monkeypatch.setattr(direct, "HelloAgentsLLM", lambda **kwargs: pytest.fail("unexpected model client"))
    with pytest.raises(ModelResponseError):
        direct.DiagramAnalyzer(settings()).analyze(saved, source)
