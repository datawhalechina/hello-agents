"""Whole-source model semantics and report persistence, with no paid inference."""
import json
import threading

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.schemas import ModelWorkflowReport
from test_model_settings import KEY, check_connection, enable_remote, payload
from test_scoped_model_jobs import TARGET, OTHER, add_messages


def synthetic_report(messages, suffix=""):
    def evidence(message):
        return {"source_id": message.source_id, "message_id": message.id, "quote": message.text}

    start, end = evidence(messages[0]), evidence(messages[-1])
    return ModelWorkflowReport.model_validate({
        "summary": "模型将分散记录综合为跨消息工作流" + suffix,
        "workstreams": [
            {"id": "shared-model-id", "name": "模型综合归纳的交付主线" + suffix, "owners": ["虚构统筹人"], "status": "模型判断待跨部门确认", "summary": "这一主线是综合归纳而非逐字复述", "evidence": [start, end]},
            {"id": "no-steps", "name": "仅有总结的模型主线", "owners": [], "status": "模型判断已经完成", "summary": "该主线没有单独列举步骤", "evidence": [end]},
        ],
        "steps": [
            {"id": "step-a", "workstream_id": "shared-model-id", "title": "模型综合判断的准备阶段", "kind": "task", "actor": "模型识别的协作人", "status": "模型认为尚未确认", "evidence": [start, end]},
            {"id": "step-b", "workstream_id": "shared-model-id", "title": "模型综合判断的交付阶段", "kind": "event", "actor": None, "status": "模型保留的原始判断", "evidence": [end]},
            {"id": "unassigned", "workstream_id": None, "title": "模型未归属的独立观察", "kind": "issue", "status": "模型尚无法归因", "evidence": [start]},
        ],
        "relations": [{"source_step_id": "step-a", "target_step_id": "step-b", "relation": "blocks", "rationale": "模型基于两条记录综合得出的阻塞判断", "evidence": [start, end]}],
        "tables": [{"title": "模型汇总表", "columns": ["主线", "判断"], "rows": [{"cells": ["交付主线", "仍需确认"], "evidence": [start, end]}]}],
        "uncertainties": ["模型识别的责任归属尚需人工确认"], "limitations": ["只分析文本记录"],
    })


@pytest.fixture
def holistic_provider(monkeypatch):
    from app.agents import orchestrator
    from app.extraction import holistic, remote
    monkeypatch.setattr(remote, "test_model_connection", lambda *args: {"ok": True, "detail": "Synthetic test", "latency_ms": 0})
    state = {"calls": [], "suffix": "", "fail": False, "entered": None, "release": None, "invalid": False}

    class FakeAnalyzer:
        def __init__(self, settings):
            self.settings = settings

        def analyze(self, messages, cancel_check=None):
            state["calls"].append([message.model_copy(deep=True) for message in messages])
            if state["entered"]:
                state["entered"].set()
                assert state["release"].wait(8), "Synthetic model release timed out"
            if state["fail"]:
                raise RuntimeError("Synthetic failure containing " + KEY)
            report = synthetic_report(messages, state["suffix"])
            if state["invalid"]:
                report.steps[0].evidence[0].quote = "Unsupported synthetic quote"
            return report

    monkeypatch.setattr(holistic, "HolisticAnalyzer", FakeAnalyzer)
    def forbidden_legacy_model(*args, **kwargs):
        raise AssertionError("Whole-source tests forbid all legacy or real model requests")
    monkeypatch.setattr(orchestrator, "RemoteReasoner", forbidden_legacy_model)
    monkeypatch.setattr(remote, "RemoteReasoner", forbidden_legacy_model)
    return state


def run(client, source=TARGET):
    response = client.post("/api/process", json={"source_id": source})
    assert response.status_code == 200, response.text
    return response.json()


def report_view(client, source=TARGET):
    response = client.get("/api/model/report", params={"source_id": source})
    assert response.status_code == 200, response.text
    return response.json()


def state_rows(client):
    repository = client.app.state.repository
    with repository.lock:
        return {row[0]: json.loads(row[1]) for row in repository.connection.execute("SELECT key,payload FROM state").fetchall()}


def saved_outputs(client):
    repository = client.app.state.repository
    version, graph = repository.latest()
    return {"version": version, "graph": graph.model_dump(mode="json"), "facts": [f.model_dump(mode="json") for f in repository.facts()], "runtime": repository.runtime(), "report": report_view(client)}


def forbid_semantic_rules(monkeypatch):
    from app.agents import orchestrator
    from app.extraction import contextual, local
    from app.resolution import projects
    from app.services import completion
    from app.workflow import builder

    def forbidden(*args, **kwargs):
        raise AssertionError("Whole-source model output must not enter deterministic semantic rules")

    for module, name in [(projects, "resolve_projects"), (builder, "build_workflow"), (completion, "update_project_status"),
                         (contextual, "classify_local_message"), (contextual, "extract_messages"), (local, "extract_local"),
                         (orchestrator, "resolve_projects"), (orchestrator, "build_workflow"),
                         (orchestrator, "classify_local_message"), (orchestrator, "extract_messages")]:
        monkeypatch.setattr(module, name, forbidden)


def test_whole_source_once_preserves_model_semantics_without_rules(client, holistic_provider, monkeypatch):
    add_messages(client, TARGET, 50)
    add_messages(client, OTHER, 3)
    enable_remote(client)
    forbid_semantic_rules(monkeypatch)
    job = run(client)
    assert job["status"] == "completed", job
    assert len(holistic_provider["calls"]) == 1 and len(holistic_provider["calls"][0]) == 50
    assert {message.source_id for message in holistic_provider["calls"][0]} == {TARGET}
    original = [m for m in client.app.state.repository.messages() if m.source_id == TARGET]
    assert holistic_provider["calls"][0] == original
    view = report_view(client)
    assert view["source_id"] == TARGET and view["version"] == job["result"]["version"] and view["created_at"]
    assert view['format'] == 'structured' and view['stale']  # Historical output is not a current direct-chat answer.
    assert view["report"] == synthetic_report(holistic_provider["calls"][0]).model_dump(mode="json")
    repository = client.app.state.repository
    projects = {project.name: project for project in repository.projects()}
    assert projects["模型综合归纳的交付主线"].status == "模型判断待跨部门确认"
    assert projects["仅有总结的模型主线"].status == "模型判断已经完成"
    facts = {fact.summary: fact for fact in repository.facts()}
    step = facts["模型综合判断的准备阶段"]
    assert step.actor == "模型识别的协作人" and step.status == "模型认为尚未确认" and len(step.evidence) == 2
    assert step.project_id == projects["模型综合归纳的交付主线"].id
    assert facts["模型未归属的独立观察"].project_id is None
    visible_projects = client.get("/api/projects", params={"source_id": TARGET}).json()
    assert any(p["name"] == "仅有总结的模型主线" for p in visible_projects)
    assert all(f.verified and f.review_status == "pending" for f in facts.values())
    assert len(repository.latest()[1].edges) == 1 and repository.latest()[1].edges[0].relation == "blocks"
    assert KEY not in json.dumps(state_rows(client))
    assert client.get("/api/export", params={"format": "training"}).text.strip() == ""


def test_report_cache_reuse_after_success_and_restart(tmp_path, holistic_provider):
    settings = Settings(database_path=str(tmp_path / "whole.db"), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        add_messages(first, TARGET, 8)
        enable_remote(first)
        assert run(first)["status"] == "completed"
        expected = report_view(first)["report"]
        assert run(first)["status"] == "completed"
        assert len(holistic_provider["calls"]) == 1
    with TestClient(create_app(settings)) as reopened:
        assert run(reopened)["status"] == "completed"
        assert len(holistic_provider["calls"]) == 1
        assert report_view(reopened)["report"] == expected


def test_report_stale_after_new_data_and_model_change_then_refresh(client, holistic_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert report_view(client)["report"] is None
    assert run(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="arrived")
    assert report_view(client)["stale"]
    assert run(client)["status"] == "completed" and report_view(client)["stale"]
    check_connection(client, model="synthetic-new-whole-model")
    assert client.put("/api/model/settings", json=payload(model="synthetic-new-whole-model")).status_code == 200
    assert report_view(client)["stale"]
    assert run(client)["status"] == "completed" and report_view(client)["stale"]
    assert len(holistic_provider["calls"]) == 3


@pytest.mark.parametrize("change", [{"base_url": "https://synthetic-other.example/v1"}, {"api_key": "synthetic-next-whole-key"}])
def test_report_cache_invalidates_when_endpoint_or_credential_changes(client, holistic_provider, change):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    check_connection(client, **change)
    assert client.put("/api/model/settings", json=payload(**change)).status_code == 200
    assert report_view(client)["stale"]
    assert run(client)["status"] == "completed"
    assert len(holistic_provider["calls"]) == 2


def test_report_prompt_change_invalidates_cached_model_output(client, holistic_provider, monkeypatch):
    from app.extraction import holistic
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    monkeypatch.setattr(holistic, "REPORT_PROMPT", holistic.REPORT_PROMPT + "\nSynthetic policy version change.")
    assert report_view(client)["stale"]
    assert run(client)["status"] == "completed"
    assert len(holistic_provider["calls"]) == 2


def test_remote_whole_source_requires_explicit_source(client, holistic_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    response = client.post("/api/process", json={})
    assert response.status_code in {200, 400, 422}
    if response.status_code == 200:
        assert response.json()["status"] == "failed"
    assert holistic_provider["calls"] == []


@pytest.mark.parametrize("failure", ["provider", "evidence"])
def test_failed_analysis_preserves_report_graph_and_runtime(client, holistic_provider, failure):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    before = saved_outputs(client)
    holistic_provider["fail" if failure == "provider" else "invalid"] = True
    job = run(client)
    assert job["status"] == "failed" and KEY not in str(job), job
    assert saved_outputs(client) == before


def test_report_write_failure_rolls_back_graph_runtime_and_report_and_can_reuse_cache(client, holistic_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    holistic_provider["suffix"] = "更新版本"
    before = saved_outputs(client)
    repository = client.app.state.repository
    with repository.lock, repository.connection:
        repository.connection.execute("CREATE TRIGGER synthetic_report_failure BEFORE INSERT ON state WHEN NEW.key LIKE 'holistic_report:%' BEGIN SELECT RAISE(ABORT, 'synthetic report write failure'); END")
    try:
        job = run(client)
        assert job["status"] == "failed", job
        assert saved_outputs(client) == before
    finally:
        with repository.lock, repository.connection:
            repository.connection.execute("DROP TRIGGER synthetic_report_failure")
    call_count = len(holistic_provider["calls"])
    assert run(client)["status"] == "completed"
    assert len(holistic_provider["calls"]) == call_count
    assert report_view(client)["report"]["summary"].endswith("更新版本")


def test_tampered_report_cache_is_reverified_before_reuse(client, holistic_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    before = saved_outputs(client)
    key, cached = next((key, row) for key, row in state_rows(client).items() if key.startswith("holistic_cache:"))
    cached["report"]["steps"][0]["evidence"][0]["quote"] = "Forged quote absent from source"
    client.app.state.repository.write_state(key, cached)
    call_count = len(holistic_provider["calls"])
    job = run(client)
    assert job["status"] == "failed", job
    assert saved_outputs(client) == before
    assert len(holistic_provider["calls"]) == call_count


@pytest.mark.parametrize("during_wait", ["cancel", "source_change"])
def test_waiting_model_is_responsive_and_cannot_commit_after_cancel_or_change(client, holistic_provider, during_wait):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="before-wait")
    before = saved_outputs(client)
    entered, release = threading.Event(), threading.Event()
    holistic_provider.update(entered=entered, release=release)
    results = []
    worker = threading.Thread(target=lambda: results.append(run(client)), daemon=True)
    worker.start()
    try:
        assert entered.wait(5), "Synthetic whole-source analysis was not invoked"
        running = next(job for job in client.app.state.repository.jobs() if job.status == "running")
        assert client.get(f"/api/jobs/{running.id}").json()["status"] == "running"
        if during_wait == "cancel":
            assert client.post(f"/api/jobs/{running.id}/cancel").json()["cancel_requested"]
        else:
            add_messages(client, TARGET, 1, prefix="during-wait")
    finally:
        release.set()
        worker.join(5)
    assert results and results[0]["status"] == ("cancelled" if during_wait == "cancel" else "failed"), results
    assert saved_outputs(client) == before


def test_other_source_reviews_and_source_isolated_model_ids_survive(client, holistic_provider):
    add_messages(client, OTHER, 3)
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert run(client, OTHER)["status"] == "completed"
    other_report = report_view(client, OTHER)["report"]
    repository = client.app.state.repository
    fact = next(f for f in repository.facts() if f.evidence[0].source_id == OTHER)
    reviewed = client.post(f"/api/facts/{fact.id}/review", json={"status": "accepted", "reviewer": "synthetic-human"})
    assert reviewed.status_code == 200
    before = reviewed.json()
    assert {p.status for p in repository.projects()} == {"模型判断待跨部门确认", "模型判断已经完成"}
    assert run(client)["status"] == "completed"
    assert next(f.model_dump(mode="json") for f in repository.facts() if f.id == fact.id) == before
    assert report_view(client, OTHER)["report"] == other_report
    assert len(repository.projects()) == 4  # Identical model IDs stay source isolated.


def test_source_delete_clears_its_report_and_cache_only(client, holistic_provider):
    add_messages(client, TARGET, 5)
    add_messages(client, OTHER, 3)
    enable_remote(client)
    assert run(client)["status"] == "completed" and run(client, OTHER)["status"] == "completed"
    other_report = report_view(client, OTHER)
    other_projects = client.get("/api/projects", params={"source_id": OTHER}).json()
    assert any(row.get("source_id") == TARGET for row in state_rows(client).values())
    preview = client.get("/api/sources/delete-preview", params={"source_id": TARGET}).json()
    deleted = client.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={"confirmation": TARGET, "expected_messages": preview["messages"], "expected_version": preview["version"]})
    assert deleted.status_code == 200, deleted.text
    assert not any(row.get("source_id") == TARGET for row in state_rows(client).values())
    assert report_view(client, OTHER) == other_report
    assert client.get("/api/projects", params={"source_id": OTHER}).json() == other_projects
    before_calls = len(holistic_provider["calls"])
    assert run(client, OTHER)["status"] == "completed"
    assert len(holistic_provider["calls"]) == before_calls


def test_report_endpoint_obeys_bearer_auth(tmp_path, holistic_provider):
    settings = Settings(database_path=str(tmp_path / "secured.db"), provider="local-demo", api_token="synthetic-auth-token", _env_file=None)
    with TestClient(create_app(settings)) as secured:
        assert secured.get("/api/model/report", params={"source_id": TARGET}).status_code == 401
        response = secured.get("/api/model/report", params={"source_id": TARGET}, headers={"Authorization": "Bearer synthetic-auth-token"})
        assert response.status_code == 200 and response.json()["report"] is None
    assert holistic_provider["calls"] == []


@pytest.fixture(autouse=True)
def explicit_structured_report_compatibility_seam(monkeypatch):
    """Historical structured reports remain tested; production now returns Markdown."""
    from app.services.processing import ProcessingService
    def structured(self, job_id, source_id, *, force_local):
        if force_local or self.models.view().provider != "helloagents-llm":
            return self._run_legacy(job_id, source_id, force_local=force_local)
        return self._run_holistic(job_id, source_id)
    monkeypatch.setattr(ProcessingService, "_run", structured)
