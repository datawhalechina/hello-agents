"""Natural model answers are stored verbatim; no real model is contacted."""
import json
import threading

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from test_model_settings import KEY, check_connection, enable_remote, payload
from test_scoped_model_jobs import TARGET, OTHER, add_messages
from test_holistic_processing import forbid_semantic_rules, report_view, state_rows, synthetic_report


@pytest.fixture
def direct_provider(monkeypatch):
    from app.agents import orchestrator
    from app.extraction import direct, holistic, remote

    def forbidden(*args, **kwargs):
        raise AssertionError("Direct-answer tests forbid structured and real model requests")

    monkeypatch.setattr(holistic, "HolisticAnalyzer", forbidden)
    monkeypatch.setattr(orchestrator, "RemoteReasoner", forbidden)
    monkeypatch.setattr(remote, "RemoteReasoner", forbidden)
    monkeypatch.setattr(remote, "test_model_connection", lambda *args: {"ok": True, "detail": "Synthetic connection", "latency_ms": 0})
    state = {"calls": [], "chunks": ["## 模型自然回答\n", "跨记录综合判断，不是结构化JSON，也不要求逐字证据。\n", "|事项|状态|\n|---|---|\n|虚构交付|仍待确认|\n"],
             "complete": True, "finish_reason": "stop", "fail": False, "entered": None, "release": None}

    class FakeDirectAnalyzer:
        def __init__(self, settings):
            self.settings = settings

        def analyze(self, messages, cancel_check=None, on_delta=None):
            from app.schemas import DirectModelAnswer
            state["calls"].append({"messages": [m.model_copy(deep=True) for m in messages], "settings": self.settings})
            assert callable(on_delta), "Processing must publish public answer deltas"
            on_delta(state["chunks"][0])
            if state["entered"]:
                state["entered"].set()
                assert state["release"].wait(8), "Synthetic stream release timed out"
            if state["fail"]:
                raise RuntimeError("Synthetic failure containing " + KEY)
            for delta in state["chunks"][1:]:
                on_delta(delta)
            return DirectModelAnswer(markdown="".join(state["chunks"]), complete=state["complete"], finish_reason=state["finish_reason"],
                                     usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}, model=self.settings.llm_model,
                                     thinking=getattr(self.settings, "llm_thinking", False), elapsed_ms=12.5)

    monkeypatch.setattr(direct, "DirectAnalyzer", FakeDirectAnalyzer)
    return state


def run_direct(client, source=TARGET):
    response = client.post("/api/process", json={"source_id": source})
    assert response.status_code == 200, response.text
    return response.json()


def graph_records(client):
    repository = client.app.state.repository
    version, graph = repository.latest()
    return {"version": version, "graph": graph.model_dump(mode="json"), "facts": [f.model_dump(mode="json") for f in repository.facts()],
            "projects": [p.model_dump(mode="json") for p in repository.projects()], "reviews": repository.reviews(), "versions": repository.versions()}


def seed_local_graph(client):
    add_messages(client, TARGET, 2, prefix="selected")
    add_messages(client, OTHER, 2, prefix="other")
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    fact = client.app.state.repository.facts()[0]
    assert client.post(f"/api/facts/{fact.id}/review", json={"status": "accepted", "reviewer": "synthetic-human"}).status_code == 200


def direct_caches(client):
    return {key: row for key, row in state_rows(client).items() if key.startswith("direct_cache:")}


def test_fifty_complete_messages_once_markdown_verbatim_without_semantic_pipeline(client, direct_provider, monkeypatch):
    seed_local_graph(client)
    add_messages(client, TARGET, 48)
    before = graph_records(client)
    enable_remote(client)
    forbid_semantic_rules(monkeypatch)
    from app.extraction import holistic
    from app.services import model_reports

    def forbidden(*args, **kwargs):
        raise AssertionError("Markdown must not enter structured report validation or graph projection")

    monkeypatch.setattr(holistic, "validate_report", forbidden)
    monkeypatch.setattr(model_reports, "report_proposal", forbidden)
    job = run_direct(client)
    assert job["status"] == "completed" and job["result"]["complete"] is True, job
    assert len(direct_provider["calls"]) == 1
    original = [m for m in client.app.state.repository.messages() if m.source_id == TARGET]
    assert len(original) == 50 and direct_provider["calls"][0]["messages"] == original
    view = report_view(client)
    assert view["format"] == "direct" and not view["stale"] and view["version"] is None
    assert view["report"]["markdown"] == "".join(direct_provider["chunks"])
    assert view["report"]["complete"] and view["report"]["finish_reason"] == "stop"
    assert view["report"]["usage"]["total_tokens"] == 150
    assert job["progress"]["markdown"] == view["report"]["markdown"]
    for field in ("usage", "model", "thinking", "finish_reason", "elapsed_ms"):
        assert job["progress"][field] == view["report"][field]
    assert graph_records(client) == before
    assert KEY not in json.dumps(state_rows(client))


def test_complete_answer_reuses_cache_after_success_and_restart(tmp_path, direct_provider):
    settings = Settings(database_path=str(tmp_path / "direct.db"), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        add_messages(first, TARGET, 5)
        enable_remote(first)
        assert run_direct(first)["status"] == "completed"
        expected = report_view(first)["report"]
        assert run_direct(first)["status"] == "completed"
        assert len(direct_provider["calls"]) == 1 and len(direct_caches(first)) == 1
    with TestClient(create_app(settings)) as reopened:
        assert run_direct(reopened)["status"] == "completed"
        assert len(direct_provider["calls"]) == 1
        assert report_view(reopened)["report"] == expected


def test_truncated_markdown_is_kept_visible_but_never_complete_cached(client, direct_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    before = graph_records(client)
    direct_provider.update(complete=False, finish_reason="length")
    job = run_direct(client)
    assert job["status"] == "completed" and job["result"]["complete"] is False, job
    assert job["result"]["warnings"]
    view = report_view(client)
    assert view["report"]["markdown"] == "".join(direct_provider["chunks"])
    assert view["report"]["complete"] is False and view["report"]["finish_reason"] == "length"
    assert direct_caches(client) == {} and graph_records(client) == before
    assert run_direct(client)["status"] == "completed"
    assert len(direct_provider["calls"]) == 2 and direct_caches(client) == {}
    direct_provider.update(complete=True, finish_reason="stop")
    assert run_direct(client)["result"]["complete"] is True
    assert len(direct_caches(client)) == 1


@pytest.mark.parametrize("change", [{"model": "synthetic-direct-next"}, {"base_url": "https://synthetic-next.example/v1"}, {"api_key": "synthetic-next-direct-key"}])
def test_model_endpoint_or_key_change_marks_report_stale_and_invalidates_cache(client, direct_provider, change):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run_direct(client)["status"] == "completed"
    check_connection(client, **change)
    assert client.put("/api/model/settings", json=payload(**change)).status_code == 200
    assert report_view(client)["stale"]
    assert run_direct(client)["status"] == "completed"
    assert len(direct_provider["calls"]) == 2


def test_thinking_setting_persists_and_changes_answer_cache_identity(tmp_path, direct_provider):
    settings = Settings(database_path=str(tmp_path / "thinking.db"), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        add_messages(first, TARGET, 5)
        assert first.get("/api/model/settings").json()["thinking"] is False
        enable_remote(first)
        assert run_direct(first)["status"] == "completed"
        response = first.put("/api/model/settings", json=payload(thinking=True))
        assert response.status_code == 200 and response.json()["thinking"] is True
        assert report_view(first)["stale"]
        assert run_direct(first)["status"] == "completed"
        assert report_view(first)["report"]["thinking"] is True
        assert len(direct_provider["calls"]) == 2
    with TestClient(create_app(settings)) as reopened:
        assert reopened.get("/api/model/settings").json()["thinking"] is True
        assert run_direct(reopened)["status"] == "completed"
        assert len(direct_provider["calls"]) == 2


def test_prompt_and_source_change_mark_direct_answer_stale(client, direct_provider, monkeypatch):
    from app.extraction import direct
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run_direct(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    assert report_view(client)["stale"]
    assert run_direct(client)["status"] == "completed"
    monkeypatch.setattr(direct, "DIRECT_PROMPT", direct.DIRECT_PROMPT + "\nSynthetic new policy.")
    assert report_view(client)["stale"]
    assert run_direct(client)["status"] == "completed"
    assert len(direct_provider["calls"]) == 3


def test_legacy_structured_report_is_stale_and_never_reused_as_direct_answer(client, direct_provider):
    from app.services.processing import _holistic_cache_key, _message_signature
    add_messages(client, TARGET, 5)
    enable_remote(client)
    repository = client.app.state.repository
    messages = repository.messages()
    legacy = synthetic_report(messages).model_dump(mode="json")
    key = _holistic_cache_key(messages, client.app.state.models.effective())
    repository.write_state(key, {"source_id": TARGET, "report": legacy})
    repository.write_state("holistic_report:" + TARGET, {"source_id": TARGET, "report": legacy, "signature": _message_signature(messages), "cache_key": key, "version": 0, "created_at": "2026-01-01T00:00:00Z"})
    old = report_view(client)
    assert old["stale"] and old["report"] == legacy
    assert run_direct(client)["status"] == "completed"
    assert len(direct_provider["calls"]) == 1 and report_view(client)["format"] == "direct"


@pytest.mark.parametrize("outcome", ["success", "failure", "cancel", "source_change"])
def test_streaming_draft_readable_and_terminal_outcome_preserves_correct_outputs(client, direct_provider, outcome):
    seed_local_graph(client)
    enable_remote(client)
    assert run_direct(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    old_report = report_view(client)
    old_graph = graph_records(client)
    old_runtime = client.app.state.repository.runtime()
    entered, release = threading.Event(), threading.Event()
    direct_provider.update(entered=entered, release=release, fail=outcome == "failure")
    results, observations = [], []
    worker = threading.Thread(target=lambda: results.append(run_direct(client)), daemon=True)
    worker.start()
    try:
        assert entered.wait(5), "Synthetic stream never started"
        finished = threading.Event()

        def inspect_draft():
            job = next(job for job in client.app.state.repository.jobs() if job.status == "running")
            observations.append(client.get(f"/api/jobs/{job.id}").json())
            if outcome == "cancel":
                observations.append(client.post(f"/api/jobs/{job.id}/cancel").json())
            elif outcome == "source_change":
                add_messages(client, TARGET, 1, prefix="during-stream")
            finished.set()

        reader = threading.Thread(target=inspect_draft, daemon=True)
        reader.start()
        assert finished.wait(2), "Streaming provider is holding the repository lock"
        assert observations[0]["progress"]["markdown"] == direct_provider["chunks"][0]
        assert observations[0]["status"] == "running"
    finally:
        release.set()
        worker.join(5)
    assert results
    job = results[0]
    expected_status = "completed" if outcome == "success" else "cancelled" if outcome == "cancel" else "failed"
    assert job["status"] == expected_status and KEY not in str(job), job
    assert job["progress"]["markdown"].startswith(direct_provider["chunks"][0])
    assert graph_records(client) == old_graph
    if outcome != "success":
        assert report_view(client) == old_report
        assert client.app.state.repository.runtime() == old_runtime
    else:
        assert report_view(client)["report"]["markdown"] == "".join(direct_provider["chunks"])


def test_runtime_write_failure_rolls_back_report_and_reuses_complete_answer_cache(client, direct_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run_direct(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    repository = client.app.state.repository
    old_report, old_runtime, old_graph = report_view(client), repository.runtime(), graph_records(client)
    with repository.lock, repository.connection:
        # Runtime is written after the report, proving rollback spans both writes.
        repository.connection.execute("CREATE TRIGGER synthetic_direct_runtime_failure BEFORE INSERT ON state WHEN NEW.key = 'runtime' BEGIN SELECT RAISE(ABORT, 'synthetic direct runtime failure'); END")
    try:
        assert run_direct(client)["status"] == "failed"
        assert report_view(client) == old_report and repository.runtime() == old_runtime and graph_records(client) == old_graph
    finally:
        with repository.lock, repository.connection:
            repository.connection.execute("DROP TRIGGER synthetic_direct_runtime_failure")
    count = len(direct_provider["calls"])
    assert run_direct(client)["status"] == "completed"
    assert len(direct_provider["calls"]) == count


def test_background_job_runs_direct_answer_and_exposes_terminal_metadata(client, direct_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    response = client.post("/api/jobs", json={"source_id": TARGET})
    assert response.status_code == 202
    # TestClient drains background tasks before returning the queued response.
    job = client.get(f"/api/jobs/{response.json()['id']}").json()
    assert job["status"] == "completed" and job["source_id"] == TARGET
    assert job["result"]["complete"] and job["progress"]["markdown"] == "".join(direct_provider["chunks"])
    assert job["progress"]["usage"]["total_tokens"] == 150
    assert len(direct_provider["calls"]) == 1


def test_delete_source_removes_its_direct_cache_and_report_preserving_other_source(client, direct_provider):
    add_messages(client, TARGET, 5)
    add_messages(client, OTHER, 3)
    enable_remote(client)
    assert run_direct(client)["status"] == "completed" and run_direct(client, OTHER)["status"] == "completed"
    other = report_view(client, OTHER)
    assert {row["source_id"] for row in direct_caches(client).values()} == {TARGET, OTHER}
    preview = client.get("/api/sources/delete-preview", params={"source_id": TARGET}).json()
    response = client.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={"confirmation": TARGET, "expected_messages": preview["messages"], "expected_version": preview["version"]})
    assert response.status_code == 200, response.text
    assert {row["source_id"] for row in direct_caches(client).values()} == {OTHER}
    assert report_view(client)["report"] is None and report_view(client, OTHER) == other
    count = len(direct_provider["calls"])
    assert run_direct(client, OTHER)["status"] == "completed" and len(direct_provider["calls"]) == count


def test_direct_processing_requires_authorization_and_explicit_source(client, direct_provider):
    add_messages(client, TARGET, 5)
    check_connection(client)
    rejected = client.put("/api/model/settings", json=payload(external_data_authorized=False))
    assert rejected.status_code in {400, 409, 422}
    enable_remote(client)
    response = client.post("/api/process", json={})
    assert response.status_code in {200, 400, 422}
    if response.status_code == 200:
        assert response.json()["status"] == "failed"
    assert direct_provider["calls"] == []
