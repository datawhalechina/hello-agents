from copy import deepcopy
import json

import httpx
import pytest
from hello_agents.core.llm_adapters import OpenAIAdapter
from openai import OpenAI

from app.config import Settings
from app.extraction import holistic
from app.extraction.remote import ModelAnalysisCancelled, ModelResponseError
from app.schemas import ModelWorkflowReport, StandardMessage


def settings(**updates):
    return Settings(provider="helloagents-llm", external_llm_enabled=True, external_data_authorized=True,
                    llm_model="synthetic", llm_api_key="SYNTHETIC_PRIVATE_KEY",
                    llm_base_url="https://synthetic.invalid/v1?private=SYNTHETIC_QUERY", _env_file=None,
                    **updates)


def messages(count=50):
    return [StandardMessage(id=f"m{index}", source_id="synthetic", sender=f"发言人{index}",
                            timestamp="2026-11-10T09:00:00+08:00", text=f"第{index}条原始消息：准备交付",
                            thread_id="thread", metadata={"private": "DO_NOT_TRANSMIT_METADATA"})
            for index in range(count)]


def evidence(index=0):
    return {"source_id": "synthetic", "message_id": f"m{index}", "quote": f"第{index}条原始消息：准备交付"}


def report_dict():
    cross = [evidence(0), evidence(1)]
    return {"summary": "综合上下文后给出的改写概况，而非逐字摘要。",
            "workstreams": [{"id": "w", "name": "模型判断的交付线", "owners": ["模型判断的执行人"],
                             "status": "模型判断的状态", "summary": "综合多次讨论得出的解释", "evidence": cross}],
            "steps": [{"id": "a", "workstream_id": "w", "title": "归纳前置准备阶段", "actor": "模型判断的执行人",
                       "status": "待确认", "occurred_at": "2026-11-10T10:00:00+08:00", "evidence": cross},
                      {"id": "b", "workstream_id": "w", "title": "归纳交付阶段", "status": "待确认", "evidence": cross}],
            "relations": [{"source_step_id": "a", "target_step_id": "b", "relation": "precedes",
                           "rationale": "模型综合多条消息推断的方向", "evidence": cross}],
            "tables": [{"title": "工作线总览", "columns": ["工作线", "状态"],
                        "rows": [{"cells": ["模型判断的交付线", "待确认"], "evidence": cross}]},
                       {"title": "详细流程", "columns": ["步骤", "负责人"],
                        "rows": [{"cells": ["前置准备", "执行人待确认"], "evidence": cross}]}],
            "uncertainties": ["负责人需确认"], "limitations": ["附件内容未读取"]}


def native(monkeypatch, report=None, finish="stop", status=200):
    sent, clients, configurations = [], [], []
    if report is None:
        report = report_dict()

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "SYNTHETIC_PRIVATE_KEY SYNTHETIC_QUERY PROVIDER_PRIVATE_BODY"}})
        content = report if isinstance(report, str) else json.dumps(report, ensure_ascii=False)
        return httpx.Response(200, json={"id": "fixture", "object": "chat.completion", "created": 0,
            "model": "synthetic", "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}})

    def client(adapter):
        assert adapter.timeout == 180
        item = OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1", max_retries=2,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        clients.append(item)
        return item

    actual = holistic.HelloAgentsLLM

    def configured(**kwargs):
        configurations.append(kwargs)
        return actual(**kwargs)

    monkeypatch.setattr(OpenAIAdapter, "create_client", client)
    monkeypatch.setattr(holistic, "HelloAgentsLLM", configured)
    return sent, clients, configurations


def test_native_50_messages_one_complete_request_allows_global_evidence_and_paraphrase(monkeypatch):
    sent, clients, configurations = native(monkeypatch)
    source = messages()
    source[-1] = source[-1].model_copy(update={"text": "[file message]"})
    result = holistic.HolisticAnalyzer(settings()).analyze(source)
    assert result.summary == report_dict()["summary"]
    assert result.steps[0].title not in source[0].text
    assert len(result.steps[0].evidence) == 2
    assert len(sent) == 1 and sent[0]["max_tokens"] == 12000
    assert sent[0]["messages"][0]["content"] == holistic.REPORT_PROMPT
    transmitted = json.loads(sent[0]["messages"][1]["content"])["messages"]
    assert len(transmitted) == 50
    assert [item["text"] for item in transmitted] == [item.text for item in source]
    assert set(transmitted[0]) == {"source_id", "message_id", "sender", "timestamp", "text", "thread_id"}
    assert "DO_NOT_TRANSMIT_METADATA" not in json.dumps(sent)
    assert not sent[0].get("tools") and not sent[0].get("stream")
    config = configurations[0]
    assert config["provider"] == "openai" and config["timeout"] == 180
    assert config["budget"].max_calls == 1 and config["budget"].max_seconds == 240
    assert clients[0].max_retries == 0 and clients[0].is_closed()


@pytest.mark.parametrize("bad", ["quote", "source", "message", "duplicate_workstream", "duplicate_step", "cross_type_id",
                                "unknown_workstream", "unknown_step", "unassigned_relation",
                                "table_width", "no_tables", "naive_time", "extra_field"])
def test_native_invalid_reports_fail_safely_once_and_close(monkeypatch, bad):
    report = report_dict()
    if bad in {"quote", "source", "message"}:
        key, value = {"quote": ("quote", "PROVIDER_PRIVATE_BODY"), "source": ("source_id", "other"),
                      "message": ("message_id", "unknown")}[bad]
        report["steps"][0]["evidence"][0][key] = value
    elif bad == "duplicate_workstream":
        report["workstreams"].append(deepcopy(report["workstreams"][0]))
    elif bad == "duplicate_step":
        report["steps"].append(deepcopy(report["steps"][0]))
    elif bad == "cross_type_id":
        report["steps"][0]["id"] = "w"
    elif bad == "unknown_workstream":
        report["steps"][0]["workstream_id"] = "unknown"
    elif bad == "unknown_step":
        report["relations"][0]["source_step_id"] = "unknown"
    elif bad == "unassigned_relation":
        for item in report["steps"]:
            item["workstream_id"] = None
    elif bad == "table_width":
        report["tables"][0]["rows"][0]["cells"].append("extra")
    elif bad == "no_tables":
        report["tables"] = []
    elif bad == "naive_time":
        report["steps"][0]["occurred_at"] = "2026-11-10T10:00:00"
    else:
        report["private_secret"] = "PROVIDER_PRIVATE_BODY"
    sent, clients, _ = native(monkeypatch, report)
    with pytest.raises(ModelResponseError) as caught:
        holistic.HolisticAnalyzer(settings()).analyze(messages())
    assert len(sent) == 1 and clients[0].is_closed()
    assert "校验" in caught.value.public_detail
    assert all(secret not in str(caught.value) + caught.value.public_detail
               for secret in ["SYNTHETIC_PRIVATE_KEY", "SYNTHETIC_QUERY", "PROVIDER_PRIVATE_BODY"])


@pytest.mark.parametrize("finish,content", [("length", None), ("stop", "{invalid JSON"), ("stop", "")])
def test_truncation_or_invalid_json_never_retries(monkeypatch, finish, content):
    sent, clients, _ = native(monkeypatch, content, finish)
    with pytest.raises(ModelResponseError):
        holistic.HolisticAnalyzer(settings()).analyze(messages())
    assert len(sent) == 1 and clients[0].is_closed()


@pytest.mark.parametrize("status", [401, 429, 503])
def test_provider_errors_are_sanitized_and_sdk_retries_disabled(monkeypatch, status):
    sent, clients, _ = native(monkeypatch, status=status)
    with pytest.raises(ModelResponseError) as caught:
        holistic.HolisticAnalyzer(settings()).analyze(messages())
    assert len(sent) == 1 and clients[0].is_closed()
    assert all(secret not in str(caught.value) + caught.value.public_detail
               for secret in ["SYNTHETIC_PRIVATE_KEY", "SYNTHETIC_QUERY", "PROVIDER_PRIVATE_BODY"])


@pytest.mark.parametrize("case", ["messages", "characters", "mixed_sources", "duplicates", "empty", "unauthorized"])
def test_invalid_inputs_never_construct_client(monkeypatch, case):
    monkeypatch.setattr(holistic, "HelloAgentsLLM", lambda **kwargs: pytest.fail("must not create client"))
    source, configuration = messages(2), settings()
    if case == "messages":
        source = messages(1001)
    elif case == "characters":
        source = [source[0].model_copy(update={"text": "长" * 48001})]
    elif case == "mixed_sources":
        source[0] = source[0].model_copy(update={"source_id": "other"})
    elif case == "duplicates":
        source = [source[0], source[0]]
    elif case == "empty":
        source = []
    else:
        configuration.external_data_authorized = False
    with pytest.raises(ModelResponseError):
        holistic.HolisticAnalyzer(configuration).analyze(source)


def test_cancel_before_or_after_transmission_closes_without_retry(monkeypatch):
    sent, clients, _ = native(monkeypatch)
    with pytest.raises(ModelAnalysisCancelled):
        holistic.HolisticAnalyzer(settings()).analyze(messages(), cancel_check=lambda: True)
    assert not sent and not clients
    checks = iter([False, False, True])
    with pytest.raises(ModelAnalysisCancelled):
        holistic.HolisticAnalyzer(settings()).analyze(messages(), cancel_check=lambda: next(checks))
    assert len(sent) == 1 and clients[0].is_closed()


def test_exported_validator_allows_empty_work_and_semantic_paraphrase():
    holistic.validate_report(ModelWorkflowReport.model_validate(report_dict()), messages())
    empty = ModelWorkflowReport(summary="没有可还原工作", workstreams=[], steps=[], limitations=["材料有限"])
    holistic.validate_report(empty, messages())
