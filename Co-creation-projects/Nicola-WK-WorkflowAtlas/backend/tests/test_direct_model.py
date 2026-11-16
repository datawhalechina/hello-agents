import json

import httpx
import pytest
from hello_agents.core.llm_adapters import OpenAIAdapter
from openai import OpenAI

from app.config import Settings
from app.extraction import direct
from app.extraction.remote import ModelAnalysisCancelled, ModelResponseError
from app.schemas import StandardMessage


def settings(**updates):
    values = dict(provider="helloagents-llm", external_llm_enabled=True, external_data_authorized=True,
                  llm_model="deepseek-flash", llm_api_key="SYNTHETIC_PRIVATE_KEY",
                  llm_base_url="https://api.deepseek.com/v1", llm_thinking=False, _env_file=None)
    values.update(updates)
    return Settings(**values)


def messages(count=50):
    return [StandardMessage(id=f"PRIVATE_MESSAGE_ID_{index}", source_id="PRIVATE_SOURCE_ID",
                            sender=f"发言人{index}", timestamp=f"2026-11-10T09:{index % 60:02d}:00+08:00",
                            text=f"完整聊天记录第{index}条正文：计划交付，实际待确认。",
                            metadata={"secret": "PRIVATE_METADATA"}) for index in range(count)]


def event(content=None, reasoning=None, finish=None, usage=None):
    choices = []
    if content is not None or reasoning is not None or finish is not None:
        delta = {}
        if content is not None:
            delta["content"] = content
        if reasoning is not None:
            delta["reasoning_content"] = reasoning
        choices = [{"index": 0, "delta": delta, "finish_reason": finish}]
    payload = {"id": "fixture", "object": "chat.completion.chunk", "created": 0,
               "model": "synthetic", "choices": choices}
    if usage is not None:
        payload["usage"] = usage
    return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")


DEFAULT_USAGE = {"prompt_tokens": 120, "completion_tokens": 20, "total_tokens": 140,
                 "completion_tokens_details": {"reasoning_tokens": 7}}


def native(monkeypatch, content=("# 工作概况\n", "| 工作线 | 计划 | 实际 |\n|---|---|---|\n| 交付 | 今日 | 待确认 |"),
           finish="stop", status=200, interrupt=False):
    sent, clients, configurations, bodies = [], [], [], []

    class Body(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield event(reasoning="PRIVATE_REASONING_NEVER_EXPOSE")
            for part in content:
                yield event(content=part)
            if interrupt:
                raise httpx.ReadError("PRIVATE_PROVIDER_BODY SYNTHETIC_PRIVATE_KEY PRIVATE_QUERY")
            yield event(finish=finish)
            yield event(usage=DEFAULT_USAGE)
            yield b"data: [DONE]\n\n"

        def close(self):
            self.closed = True

    def handler(request):
        sent.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "PRIVATE_PROVIDER_BODY SYNTHETIC_PRIVATE_KEY PRIVATE_QUERY"}})
        body = Body()
        bodies.append(body)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    def client(adapter):
        assert adapter.timeout == 180
        item = OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1", max_retries=2,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        clients.append(item)
        return item

    actual = direct.HelloAgentsLLM

    def configured(**kwargs):
        configurations.append(kwargs)
        return actual(**kwargs)

    monkeypatch.setattr(OpenAIAdapter, "create_client", client)
    monkeypatch.setattr(direct, "HelloAgentsLLM", configured)
    return sent, clients, configurations, bodies


def test_native_stream_50_messages_complete_plaintext_no_json_and_public_deltas(monkeypatch):
    sent, clients, configurations, bodies = native(monkeypatch)
    source = list(reversed(messages()))
    source[0] = source[0].model_copy(update={"text": "[file message]"})
    deltas = []
    answer = direct.DirectAnalyzer(settings()).analyze(source, on_delta=deltas.append)
    assert len(sent) == 1 and sent[0]["stream"] is True
    payload = sent[0]
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["thinking"] == {"type": "disabled"}
    assert "max_tokens" not in payload and "max_completion_tokens" not in payload
    assert not payload.get("tools") and not payload.get("response_format")
    assert len(payload["messages"]) == 2 and payload["messages"][0]["content"] == direct.DIRECT_PROMPT
    assert len(direct.DIRECT_PROMPT) < 300
    transcript = payload["messages"][1]["content"]
    assert transcript.startswith("2026-11-10T09:00:00+08:00 发言人0\n")
    for item in source:
        assert item.text in transcript
    assert "[file message]" in transcript
    assert all(private not in transcript for private in ["PRIVATE_SOURCE_ID", "PRIVATE_MESSAGE_ID", "PRIVATE_METADATA"])
    assert answer.markdown == "".join(deltas) and answer.markdown.startswith("# 工作概况")
    assert answer.complete is True and answer.finish_reason == "stop" and answer.thinking is False
    assert answer.usage == {"prompt_tokens": 120, "completion_tokens": 20, "total_tokens": 140, "reasoning_tokens": 7}
    assert "PRIVATE_REASONING" not in answer.model_dump_json() + "".join(deltas)
    assert answer.elapsed_ms >= 0
    config = configurations[0]
    assert "max_tokens" not in config and config["budget"].max_calls == 1 and config["budget"].max_seconds == 240
    assert clients[0].max_retries == 0 and clients[0].is_closed() and bodies[0].closed


@pytest.mark.parametrize("model", ["deepseek-flash", "deepseek-v4-flash", "deepseek-v4-pro"])
def test_supported_official_thinking_option(monkeypatch, model):
    sent, _, _, _ = native(monkeypatch)
    answer = direct.DirectAnalyzer(settings(llm_model=model, llm_thinking=True)).analyze(messages())
    assert sent[0]["thinking"] == {"type": "enabled"} and answer.thinking is True


@pytest.mark.parametrize("url,model", [("https://compatible.invalid/v1", "deepseek-v4-flash"),
                                     ("https://api.deepseek.com.evil.invalid/v1", "deepseek-flash"),
                                     ("https://api.deepseek.com/v1", "other-model")])
def test_other_compatible_providers_receive_no_thinking_parameter(monkeypatch, url, model):
    sent, _, _, _ = native(monkeypatch)
    answer = direct.DirectAnalyzer(settings(llm_base_url=url, llm_model=model, llm_thinking=True)).analyze(messages())
    assert "thinking" not in sent[0] and answer.thinking is False


def test_no_old_message_or_character_thresholds(monkeypatch):
    sent, _, _, _ = native(monkeypatch)
    source = messages(1001)
    source[-1] = source[-1].model_copy(update={"text": "尾部" + "长" * 49000})
    answer = direct.DirectAnalyzer(settings()).analyze(source)
    transcript = sent[0]["messages"][1]["content"]
    assert answer.complete and len(sent) == 1
    assert all(item.text in transcript for item in source)
    assert source[-1].text in transcript


def test_length_finish_preserves_answer_and_usage(monkeypatch):
    sent, clients, _, bodies = native(monkeypatch, content=("已生成的部分正文",), finish="length")
    answer = direct.DirectAnalyzer(settings()).analyze(messages())
    assert answer.markdown == "已生成的部分正文" and answer.complete is False and answer.finish_reason == "length"
    assert answer.usage["reasoning_tokens"] == 7
    assert len(sent) == 1 and clients[0].is_closed() and bodies[0].closed


def test_interrupted_stream_preserves_partial_answer_without_provider_error(monkeypatch):
    sent, clients, _, bodies = native(monkeypatch, content=("已生成正文",), interrupt=True)
    deltas = []
    answer = direct.DirectAnalyzer(settings()).analyze(messages(), on_delta=deltas.append)
    assert answer.markdown == "已生成正文" == "".join(deltas)
    assert not answer.complete and answer.finish_reason == "interrupted" and answer.usage == {}
    assert all(private not in answer.model_dump_json() for private in ["PRIVATE_PROVIDER_BODY", "SYNTHETIC_PRIVATE_KEY", "PRIVATE_QUERY", "PRIVATE_REASONING"])
    assert len(sent) == 1 and clients[0].is_closed() and bodies[0].closed


@pytest.mark.parametrize("interrupt", [False, True])
def test_no_public_text_is_a_safe_explicit_failure(monkeypatch, interrupt):
    sent, clients, _, bodies = native(monkeypatch, content=(), interrupt=interrupt)
    with pytest.raises(ModelResponseError) as caught:
        direct.DirectAnalyzer(settings()).analyze(messages())
    assert all(private not in str(caught.value) + caught.value.public_detail
               for private in ["PRIVATE_PROVIDER_BODY", "SYNTHETIC_PRIVATE_KEY", "PRIVATE_QUERY", "PRIVATE_REASONING"])
    assert len(sent) == 1 and clients[0].is_closed() and bodies[0].closed
    if not interrupt:
        assert isinstance(caught.value, direct.EmptyDirectAnswer)
        assert caught.value.usage['total_tokens'] == 140
        assert caught.value.usage['reasoning_tokens'] == 7


@pytest.mark.parametrize("status", [401, 429, 503])
def test_retryable_http_failures_are_safe_single_requests(monkeypatch, status):
    sent, clients, _, _ = native(monkeypatch, status=status)
    with pytest.raises(ModelResponseError) as caught:
        direct.DirectAnalyzer(settings()).analyze(messages())
    assert all(private not in str(caught.value) + caught.value.public_detail
               for private in ["PRIVATE_PROVIDER_BODY", "SYNTHETIC_PRIVATE_KEY", "PRIVATE_QUERY"])
    assert len(sent) == 1 and clients[0].is_closed()


def test_cancel_keeps_callback_draft_but_does_not_return_completed_answer(monkeypatch):
    sent, clients, _, bodies = native(monkeypatch)
    draft = []
    with pytest.raises(ModelAnalysisCancelled):
        direct.DirectAnalyzer(settings()).analyze(messages(), cancel_check=lambda: bool(draft), on_delta=draft.append)
    assert draft and len(sent) == 1 and clients[0].is_closed() and bodies[0].closed


@pytest.mark.parametrize("case", ["cancel", "unauthorized", "empty", "mixed", "url"])
def test_preflight_failures_never_construct_client(monkeypatch, case):
    monkeypatch.setattr(direct, "HelloAgentsLLM", lambda **kwargs: pytest.fail("unexpected client"))
    config, source = settings(), messages()
    if case == "unauthorized":
        config.external_data_authorized = False
    elif case == "empty":
        source = []
    elif case == "mixed":
        source[0] = source[0].model_copy(update={"source_id": "other"})
    elif case == "url":
        config.llm_base_url = "https://[broken"
    with pytest.raises(ModelAnalysisCancelled if case == "cancel" else ModelResponseError):
        direct.DirectAnalyzer(config).analyze(source, cancel_check=lambda: case == "cancel")
