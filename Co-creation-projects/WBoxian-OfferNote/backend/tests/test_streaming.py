import asyncio
import json
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from app import demo
from app.interview import demo_decision
from app.main import create_app
from app.streaming import stream_answer
from app.usage import CURRENT_CALL, instrument


def chunk(text=None, finish=None, usage=None):
    return NS(
        choices=[NS(delta=NS(content=text), finish_reason=finish)]
        if text is not None or finish
        else [],
        usage=NS(
            prompt_tokens=usage[0], completion_tokens=usage[1], total_tokens=sum(usage)
        )
        if usage
        else None,
    )


class FakeStream:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.chunks)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closed = True


@pytest.fixture
def setup(tmp_path, monkeypatch):
    for key, value in {
        "API_KEY": "test-key",
        "BASE_URL": "https://example.com/v1",
        "MODEL": "TEST",
        "MAX_TOKENS": "12000",
    }.items():
        monkeypatch.setenv("OFFERNOTE_" + key, value)
    app = create_app(str(tmp_path / "stream.sqlite3"))
    engine = app.state.engine

    def model(stage, context, schema):
        if stage == "analysis":
            return demo.analyze(context["resume"], context["job"])
        return demo_decision(engine, context["session"])

    monkeypatch.setattr(engine, "live", model)
    options = {
        "chunks": [
            chunk("我负责本地后端接口，"),
            chunk("模型调用在数据库事务外，失败不保存成功答案。"),
            chunk(finish="stop"),
            chunk(usage=(20, 10)),
            chunk(usage=(20, 15)),
        ]
    }
    streams, requests = [], []

    def make_llm():
        def create(**kwargs):
            requests.append(kwargs)
            stream = FakeStream(options["chunks"])
            streams.append(stream)
            return stream

        return instrument(
            NS(_client=NS(chat=NS(completions=NS(create=create)), close=lambda: None))
        )

    monkeypatch.setattr(engine, "make_llm", make_llm)
    with TestClient(app) as client:
        wid = "demo-development"
        client.post(f"/api/workspaces/{wid}/analyze", json={"mode": "live"})
        response = client.post(
            f"/api/workspaces/{wid}/sessions", json={"mode": "live", "count": 4}
        )
        session = response.json()["sessions"][-1]
        yield client, app, options, streams, requests, wid, session


def request_stream(setup):
    client, _, _, _, _, wid, session = setup
    response = client.post(
        f"/api/workspaces/{wid}/sessions/{session['id']}/demonstration-answer/stream",
        json={"question_id": session["questions"][0]["id"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [
        json.loads(line[5:])
        for line in response.text.splitlines()
        if line.startswith("data:")
    ]


def test_stream_deltas_save_only_completed_answer_and_count_last_usage(setup):
    _, app, _, streams, requests, wid, session = setup
    events = request_stream(setup)
    assert [event["type"] for event in events] == ["start", "delta", "delta", "done"]
    assert events[-1]["answer"] == "".join(
        e["text"] for e in events if e["type"] == "delta"
    )
    saved = app.state.store.get(wid)["sessions"][-1]
    assert saved["turns"] == []
    assert (
        saved["demonstration_drafts"][session["questions"][0]["id"]]["answer"]
        == events[-1]["answer"]
    )
    usage = next(
        e for e in app.state.store.events(wid) if e["stage"] == "demonstration_answer"
    )
    assert (
        usage["tokens"] == 35
        and usage["output_tokens"] == 15
        and usage["usage_complete"]
    )
    assert requests[0]["stream_options"] == {"include_usage": True}
    assert streams[0].closed
    assert [e["type"] for e in request_stream(setup)] == ["done"]
    assert len(requests) == 1


@pytest.mark.parametrize("mode", ["length", "interrupted", "no_stop", "empty"])
def test_failed_stream_never_saves_partial_draft_and_releases_lock(setup, mode):
    _, app, options, _, requests, wid, _ = setup
    if mode == "length":
        options["chunks"][-3] = chunk(finish="length")
    elif mode == "interrupted":
        options["chunks"] = [chunk("这一段尚未完成"), OSError("provider disconnected")]
    elif mode == "no_stop":
        options["chunks"] = [
            chunk(usage=(10, 3)),
            chunk("即使正文长度足够，没有结束标志也不能当作完整回答保存。"),
        ]
    else:
        options["chunks"] = [chunk(finish="stop"), chunk(usage=(10, 1))]
    events = request_stream(setup)
    assert events[-1]["type"] == "error" and not any(
        e["type"] == "done" for e in events
    )
    saved = app.state.store.get(wid)["sessions"][-1]
    assert saved["turns"] == [] and not saved.get("demonstration_drafts")
    usage = next(
        e for e in app.state.store.events(wid) if e["stage"] == "demonstration_answer"
    )
    assert usage["status"] == "error"
    if mode == "no_stop":
        assert not usage["usage_complete"]
    if mode == "length":
        assert usage["tokens"] == 35  # length 后仍读取最终 usage，不丢失已返回消耗。
    request_stream(setup)
    assert len(requests) == 2


def test_stream_without_usage_preserves_unknown(setup):
    _, app, options, _, _, wid, _ = setup
    options["chunks"] = options["chunks"][:3]
    assert request_stream(setup)[-1]["type"] == "done"
    usage = next(
        e for e in app.state.store.events(wid) if e["stage"] == "demonstration_answer"
    )
    assert usage["tokens"] is None and not usage["usage_complete"]


def test_cancelled_stream_closes_client_and_marks_partial_usage(setup):
    _, app, options, streams, _, wid, _ = setup
    options["chunks"] = [chunk(usage=(10, 2)), chunk("部分正文"), chunk(finish="stop")]

    async def consume():
        source = stream_answer(app.state.engine, wid, {})
        assert await anext(source) == "部分正文"
        await source.aclose()
        assert CURRENT_CALL.get() is None

    asyncio.run(consume())
    usage = next(
        e for e in app.state.store.events(wid) if e["stage"] == "demonstration_answer"
    )
    assert (
        usage["status"] == "cancelled"
        and usage["tokens"] == 12
        and not usage["usage_complete"]
    )
    assert streams[0].closed
