"""Explicit diagrams consume saved answer text only; providers are invented."""
import hashlib
import threading

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.schemas import DirectModelAnswer, Job
from test_direct_processing import graph_records, seed_local_graph
from test_holistic_processing import forbid_semantic_rules, report_view, state_rows
from test_model_settings import KEY, check_connection, enable_remote, payload
from test_scoped_model_jobs import TARGET, OTHER, add_messages

ANSWER = "## 已保存的虚构分析\n虚构阶段甲先准备，再推进阶段乙；这段是模型总结而非原始消息。"
DIAGRAM = "```mermaid\nflowchart LR\n  A[虚构准备] --> B[虚构推进]\n```\n"


@pytest.fixture
def diagram_provider(monkeypatch):
    from app.agents import orchestrator
    from app.extraction import direct, holistic, remote

    def forbidden(*args, **kwargs):
        raise AssertionError("Diagram tests forbid original-message and real model analysis")

    monkeypatch.setattr(direct, "DirectAnalyzer", forbidden)
    monkeypatch.setattr(holistic, "HolisticAnalyzer", forbidden)
    monkeypatch.setattr(orchestrator, "RemoteReasoner", forbidden)
    monkeypatch.setattr(remote, "RemoteReasoner", forbidden)
    monkeypatch.setattr(remote, "test_model_connection", lambda *args: {"ok": True, "detail": "Synthetic connection", "latency_ms": 0})
    state = {"calls": [], "complete": True, "fail": False, "entered": None, "release": None}

    class FakeDiagram:
        def __init__(self, settings):
            self.settings = settings

        def analyze(self, markdown, source_id, cancel_check=None, on_delta=None):
            assert isinstance(markdown, str)
            state["calls"].append((markdown, source_id))
            assert callable(on_delta)
            on_delta("```mermaid\n")
            if state["entered"]:
                state["entered"].set()
                assert state["release"].wait(8), "Synthetic diagram release timed out"
            if state["fail"]:
                raise RuntimeError("Synthetic provider failure containing " + KEY)
            on_delta(DIAGRAM[len("```mermaid\n"):])
            return DirectModelAnswer(markdown=DIAGRAM, complete=state["complete"], finish_reason="stop" if state["complete"] else "length",
                                     usage={"total_tokens": 40}, model=self.settings.llm_model, thinking=self.settings.llm_thinking, elapsed_ms=9)

    monkeypatch.setattr(direct, "DiagramAnalyzer", FakeDiagram)
    return state


def save_answer(client, markdown=ANSWER, source=TARGET):
    from app.services.processing import _direct_cache_key
    repository = client.app.state.repository
    answer = DirectModelAnswer(markdown=markdown, model=client.app.state.models.effective().llm_model).model_dump(mode="json")
    selected = [m for m in repository.messages() if m.source_id == source]
    wrapper = {"source_id": source, "format": "direct", "report": answer, "created_at": "2026-01-01T00:00:00Z", "version": None,
               "cache_key": _direct_cache_key(selected, client.app.state.models.effective()), "cached": False}
    repository.write_state("holistic_report:" + source, wrapper)
    return wrapper


def setup_answer(client):
    add_messages(client, TARGET, 3)
    enable_remote(client)
    save_answer(client)


def generate(client, source=TARGET):
    response = client.post("/api/model/diagram", params={"source_id": source})
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["purpose"] == "diagram" and queued["source_id"] == source
    return client.get(f"/api/jobs/{queued['id']}").json()


def diagram_caches(client):
    return {key: value for key, value in state_rows(client).items() if key.startswith("diagram_cache:")}


def unchanged_outputs(client):
    repository = client.app.state.repository
    return {"report": repository.read_state("holistic_report:" + TARGET), "graph": graph_records(client), "runtime": repository.runtime()}


def test_explicit_diagram_only_sends_saved_markdown_and_never_changes_report_or_graph(client, diagram_provider, monkeypatch):
    seed_local_graph(client)
    enable_remote(client)
    save_answer(client)
    before = unchanged_outputs(client)
    forbid_semantic_rules(monkeypatch)
    for _ in range(2):
        assert report_view(client)["diagram"] is None
    assert diagram_provider["calls"] == []  # Opening/reading the report is free.
    job = generate(client)
    assert job["status"] == "completed" and job["result"]["complete"], job
    assert diagram_provider["calls"] == [(ANSWER, TARGET)]
    view = report_view(client)
    assert view["diagram"]["markdown"] == DIAGRAM and not view["diagram_stale"] and not view["diagram_cached"]
    assert unchanged_outputs(client) == before
    saved = client.app.state.repository.read_state("model_diagram:" + TARGET)
    assert saved["answer_hash"] == hashlib.sha256(ANSWER.encode()).hexdigest()


def test_complete_diagram_cache_survives_repeated_clicks_and_restart(tmp_path, diagram_provider):
    settings = Settings(database_path=str(tmp_path / "diagram.db"), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        setup_answer(first)
        assert generate(first)["status"] == "completed"
        assert generate(first)["status"] == "completed"
        assert report_view(first)["diagram_cached"] and len(diagram_provider["calls"]) == 1
    with TestClient(create_app(settings)) as reopened:
        assert generate(reopened)["status"] == "completed"
        assert report_view(reopened)["diagram_cached"] and len(diagram_provider["calls"]) == 1


@pytest.mark.parametrize("change", ["answer", "model", "endpoint", "key", "thinking", "prompt"])
def test_diagram_stale_and_cache_identity_follow_answer_and_model_settings(client, diagram_provider, monkeypatch, change):
    from app.extraction import direct
    setup_answer(client)
    assert generate(client)["status"] == "completed"
    if change == "answer":
        save_answer(client, ANSWER + "\n新增模型总结。")
    elif change == "prompt":
        monkeypatch.setattr(direct, "DIAGRAM_PROMPT", direct.DIAGRAM_PROMPT + "\nSynthetic diagram policy.")
    else:
        changed = {"model": {"model": "synthetic-diagram-next"}, "endpoint": {"base_url": "https://synthetic-diagram.example/v1"},
                   "key": {"api_key": "synthetic-next-diagram-key"}, "thinking": {"thinking": True}}[change]
        if change != "thinking":
            check_connection(client, **changed)
        assert client.put("/api/model/settings", json=payload(**changed)).status_code == 200
    assert report_view(client)["diagram_stale"]
    assert generate(client)["status"] == "completed"
    assert len(diagram_provider["calls"]) == 2 and not report_view(client)["diagram_stale"]


def test_old_text_prompt_or_new_raw_messages_do_not_force_answer_regeneration(client, diagram_provider, monkeypatch):
    from app.extraction import direct
    setup_answer(client)
    assert generate(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new-unanalysed")
    monkeypatch.setattr(direct, "DIRECT_PROMPT", direct.DIRECT_PROMPT + "\nChanged answer instructions.")
    assert report_view(client)["stale"]
    assert not report_view(client)["diagram_stale"]
    job = generate(client)
    assert job["status"] == "completed", job
    assert diagram_provider["calls"] == [(ANSWER, TARGET)]
    assert report_view(client)["diagram_cached"]


def test_partial_diagram_is_saved_with_warning_but_never_complete_cached(client, diagram_provider):
    setup_answer(client)
    before = unchanged_outputs(client)
    diagram_provider["complete"] = False
    job = generate(client)
    assert job["status"] == "completed" and not job["result"]["complete"] and job["result"]["warnings"]
    view = report_view(client)
    assert view["diagram"]["markdown"] == DIAGRAM and view["diagram"]["complete"] is False
    assert diagram_caches(client) == {} and unchanged_outputs(client) == before
    assert generate(client)["status"] == "completed" and len(diagram_provider["calls"]) == 2


@pytest.mark.parametrize("status", ["queued", "running"])
def test_existing_active_job_prevents_diagram_enqueue(client, diagram_provider, status):
    setup_answer(client)
    repository = client.app.state.repository
    repository.save_job(Job(id="synthetic-active", status=status))
    before = len(repository.jobs())
    response = client.post("/api/model/diagram", params={"source_id": TARGET})
    assert response.status_code == 409 and len(repository.jobs()) == before
    assert diagram_provider["calls"] == []


def test_missing_report_unknown_source_and_disabled_model_are_explicit_errors(client, diagram_provider):
    add_messages(client, TARGET, 1)
    response = client.post("/api/model/diagram", params={"source_id": TARGET})
    assert response.status_code == 403
    enable_remote(client)
    assert client.post("/api/model/diagram", params={"source_id": "synthetic-unknown"}).status_code == 404
    assert client.post("/api/model/diagram", params={"source_id": TARGET}).status_code == 400
    assert diagram_provider["calls"] == [] and client.app.state.repository.jobs() == []


@pytest.mark.parametrize("kind", ["blank", "structured"])
def test_only_nonblank_direct_answers_can_enqueue_diagram(client, diagram_provider, kind):
    setup_answer(client)
    repository = client.app.state.repository
    if kind == "blank":
        save_answer(client, " \n\t")
    else:
        from test_holistic_processing import synthetic_report
        repository.write_state("holistic_report:" + TARGET, {"source_id": TARGET, "format": "structured", "report": synthetic_report(repository.messages()).model_dump(mode="json")})
    response = client.post("/api/model/diagram", params={"source_id": TARGET})
    assert response.status_code == 400 and repository.jobs() == []
    assert diagram_provider["calls"] == []


def test_queued_diagram_rejects_changed_answer_before_any_model_request(client, diagram_provider, monkeypatch):
    from app.services.processing import ProcessingService
    setup_answer(client)
    original_run = ProcessingService.run
    monkeypatch.setattr(ProcessingService, "run", lambda *args, **kwargs: None)
    response = client.post("/api/model/diagram", params={"source_id": TARGET})
    assert response.status_code == 202
    save_answer(client, ANSWER + "\n排队后改写。")
    job = original_run(client.app.state.processing, response.json()["id"])
    assert job.status == "failed" and diagram_provider["calls"] == []
    assert client.app.state.repository.read_state("model_diagram:" + TARGET) is None


@pytest.mark.parametrize("outcome", ["failure", "cancel", "answer_change"])
def test_diagram_stream_draft_remains_readable_and_failed_or_cancelled_output_does_not_commit(client, diagram_provider, outcome):
    setup_answer(client)
    assert generate(client)["status"] == "completed"
    old_diagram = client.app.state.repository.read_state("model_diagram:" + TARGET)
    save_answer(client, ANSWER + "\n用于新图示的保存回答。")
    before = unchanged_outputs(client)
    entered, release = threading.Event(), threading.Event()
    diagram_provider.update(entered=entered, release=release, fail=outcome == "failure")
    results, observations, errors = [], [], []

    def generate_in_thread():
        try:
            results.append(generate(client))
        except Exception as error:
            errors.append(error)
            entered.set()

    worker = threading.Thread(target=generate_in_thread, daemon=True)
    worker.start()
    try:
        assert entered.wait(5), "Synthetic diagram stream never started"
        assert not errors, errors
        finished = threading.Event()

        def observe():
            try:
                running = next(job for job in client.app.state.repository.jobs() if job.status == "running")
                observations.append(client.get(f"/api/jobs/{running.id}").json())
                if outcome == "cancel":
                    assert client.post(f"/api/jobs/{running.id}/cancel").json()["cancel_requested"]
                elif outcome == "answer_change":
                    save_answer(client, ANSWER + "\n模型等待期间已改写。")
            except Exception as error:
                errors.append(error)
            finally:
                finished.set()

        reader = threading.Thread(target=observe, daemon=True)
        reader.start()
        assert finished.wait(2), "Model wait blocks diagram progress/cancel"
        assert not errors, errors
        assert observations[0]["progress"]["markdown"] == "```mermaid\n"
    finally:
        release.set()
        worker.join(5)
    assert results
    job = results[0]
    assert job["status"] == ("cancelled" if outcome == "cancel" else "failed"), job
    assert job["progress"]["markdown"].startswith("```mermaid\n") and KEY not in str(job)
    assert client.app.state.repository.read_state("model_diagram:" + TARGET) == old_diagram
    if outcome != "answer_change":
        assert unchanged_outputs(client) == before
    else:
        assert graph_records(client) == before["graph"] and client.app.state.repository.runtime() == before["runtime"]


def test_diagram_state_rolls_back_when_completed_job_write_fails(client, diagram_provider):
    setup_answer(client)
    repository = client.app.state.repository
    before = unchanged_outputs(client)
    with repository.lock, repository.connection:
        repository.connection.execute("CREATE TRIGGER synthetic_diagram_job_failure BEFORE UPDATE ON jobs WHEN json_extract(NEW.payload, '$.purpose')='diagram' AND json_extract(NEW.payload, '$.status')='completed' BEGIN SELECT RAISE(ABORT, 'synthetic diagram terminal failure'); END")
    try:
        job = generate(client)
        assert job["status"] == "failed", job
        assert repository.read_state("model_diagram:" + TARGET) is None and unchanged_outputs(client) == before
    finally:
        with repository.lock, repository.connection:
            repository.connection.execute("DROP TRIGGER synthetic_diagram_job_failure")


def test_delete_source_clears_diagram_and_cache_while_preserving_other_source(client, diagram_provider):
    setup_answer(client)
    add_messages(client, OTHER, 2)
    save_answer(client, source=OTHER)
    assert generate(client)["status"] == "completed" and generate(client, OTHER)["status"] == "completed"
    keep = client.app.state.repository.read_state("model_diagram:" + OTHER)
    preview = client.get("/api/sources/delete-preview", params={"source_id": TARGET}).json()
    response = client.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={"confirmation": TARGET, "expected_messages": preview["messages"], "expected_version": preview["version"]})
    assert response.status_code == 200, response.text
    assert client.app.state.repository.read_state("model_diagram:" + TARGET) is None
    assert {row["source_id"] for row in diagram_caches(client).values()} == {OTHER}
    assert client.app.state.repository.read_state("model_diagram:" + OTHER) == keep
    count = len(diagram_provider["calls"])
    assert generate(client, OTHER)["status"] == "completed" and len(diagram_provider["calls"]) == count


def test_diagram_endpoint_obeys_bearer_auth(tmp_path, diagram_provider):
    settings = Settings(database_path=str(tmp_path / "diagram-auth.db"), provider="local-demo", api_token="synthetic-auth", _env_file=None)
    with TestClient(create_app(settings)) as secured:
        denied = secured.post("/api/model/diagram", params={"source_id": TARGET})
        assert denied.status_code == 401 and diagram_provider["calls"] == []
