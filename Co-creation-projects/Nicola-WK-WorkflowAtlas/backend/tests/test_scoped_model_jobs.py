"""Batched source-only model jobs; all inference is an invented bounded fake."""
import math
import threading

import pytest

from app.extraction.local import extract_local
from app.schemas import ReviewRequest
from test_model_settings import BASE, KEY, MODEL, enable_remote, fake_connection

TARGET = "synthetic/selected"
OTHER = "synthetic/keep"


def add_messages(client, source, count, prefix="m"):
    messages = [{"id": f"{prefix}-{index}", "source_id": source, "sender": "虚构发言人",
                 "text": f"【虚构来源项目】[任务:接口{prefix}{index}] 开始接口测试", "timestamp": "2026-01-01T09:00:00+08:00",
                 "metadata": {"private": "not-a-network-payload"}} for index in range(count)]
    response = client.post("/api/import", json={"source_id": source, "messages": messages})
    assert response.status_code == 200, response.text
    return messages


def install_reasoner(monkeypatch, *, fail_instance=None, entered=None, release=None):
    from app.agents import orchestrator
    instances = []
    sent = []

    class BudgetedFakeReasoner:
        def __init__(self, **kwargs):
            self.index = len(instances)
            self.calls = 0
            self.closed = False
            self.cancel_check = kwargs.get("cancel_check")
            self.max_calls = kwargs.get("max_calls", 60)
            instances.append(self)

        def _tick(self, message):
            if self.cancel_check and self.cancel_check():
                raise RuntimeError("Synthetic cancellation before transmission")
            self.calls += 1
            if self.calls > self.max_calls:
                raise RuntimeError("Synthetic per-batch 60-call budget exceeded")
            sent.append((message.source_id, message.id))
            if self.index == fail_instance:
                raise RuntimeError("Synthetic provider failure")
            if entered is not None and self.index == 0 and self.calls == 1:
                entered.set()
                assert release.wait(8), "Test release was not signalled"

        def classify(self, message):
            self._tick(message)
            return "work"

        def extract(self, message):
            self._tick(message)
            return extract_local(message)

        def close(self):
            self.closed = True

    monkeypatch.setattr(orchestrator, "RemoteReasoner", BudgetedFakeReasoner)
    return instances, sent


def seed_existing_data(client):
    add_messages(client, OTHER, 2, prefix="other")
    add_messages(client, TARGET, 2, prefix="selected")
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    repository = client.app.state.repository
    fact = next(f for f in repository.facts() if f.evidence[0].source_id == OTHER)
    repository.review(fact.id, ReviewRequest(status="accepted", reviewer="synthetic-human"))
    return fact.id


def test_216_selected_messages_use_fresh_bounded_batches_and_preserve_other_source(client, monkeypatch, fake_connection):
    add_messages(client, OTHER, 2, prefix="other")
    assert client.post("/api/process", json={}).json()["status"] == "completed"
    repository = client.app.state.repository
    keep = repository.facts()[0]
    repository.review(keep.id, ReviewRequest(status="accepted", reviewer="synthetic-reviewer"))
    before = next(f for f in repository.facts() if f.id == keep.id).model_dump(mode="json")
    add_messages(client, TARGET, 216)
    enable_remote(client)
    instances, sent = install_reasoner(monkeypatch)
    response = client.post("/api/process", json={"source_id": TARGET})
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "completed", job
    assert len(instances) == math.ceil(216 / 5) and all(i.closed and i.calls <= 60 for i in instances)
    assert len(sent) == 432 and {source for source, _ in sent} == {TARGET}
    assert len({identifier for _, identifier in sent}) == 216
    assert len(client.get("/api/facts", params={"source_id": TARGET}).json()) == 216
    assert next(f for f in repository.facts() if f.id == keep.id).model_dump(mode="json") == before
    assert job["source_id"] == TARGET and job["progress"]["processed_messages"] == 216
    assert job["progress"]["total_messages"] == 216
    assert len(job["result"]["agent_results"]) == 6
    assert all(f["review_status"] == "pending" for f in client.get("/api/facts", params={"source_id": TARGET}).json())


def test_remote_job_requires_an_explicit_source_before_any_transmission(client, monkeypatch, fake_connection):
    add_messages(client, TARGET, 2)
    enable_remote(client)
    instances, sent = install_reasoner(monkeypatch)
    response = client.post("/api/process", json={})
    # Synchronous compatibility endpoint reports job failure; a request guard may
    # instead reject it directly, but neither route may invoke a provider.
    assert response.status_code in {200, 400, 422}
    if response.status_code == 200:
        assert response.json()["status"] == "failed"
    assert sent == [] and instances == []


def test_background_job_endpoint_preserves_source_and_reports_completed_progress(client, monkeypatch, fake_connection):
    add_messages(client, TARGET, 7)
    enable_remote(client)
    instances, sent = install_reasoner(monkeypatch)
    response = client.post("/api/jobs", json={"source_id": TARGET})
    assert response.status_code == 202
    queued = response.json()
    assert queued["source_id"] == TARGET
    # TestClient drains the background task before returning this response.
    completed = client.get(f"/api/jobs/{queued['id']}").json()
    assert completed["status"] == "completed" and completed["progress"]["processed_messages"] == 7
    assert len(instances) == 2 and all(i.closed for i in instances)
    assert len(sent) == 14 and {source for source, _ in sent} == {TARGET}


def test_demo_stays_local_after_model_is_enabled(client, monkeypatch, fake_connection):
    enable_remote(client)
    instances, sent = install_reasoner(monkeypatch)
    response = client.post("/api/demo")
    assert response.status_code == 200 and response.json()["job"]["status"] == "completed"
    assert response.json()["job"]["result"]["provider"] == "local-demo"
    assert client.get("/api/health").json()["provider"] == "helloagents-llm"
    assert instances == [] and sent == []


def test_later_batch_failure_does_not_commit_partial_results(client, monkeypatch, fake_connection):
    seed_existing_data(client)
    add_messages(client, TARGET, 8, prefix="new")
    repository = client.app.state.repository
    before = repository.latest()[1].model_dump(mode="json")
    before_facts = [f.model_dump(mode="json") for f in repository.facts()]
    enable_remote(client)
    instances, sent = install_reasoner(monkeypatch, fail_instance=1)
    job = client.post("/api/process", json={"source_id": TARGET}).json()
    assert job["status"] == "failed" and job["error"]
    assert len(instances) == 2 and all(i.closed for i in instances)
    assert repository.latest()[1].model_dump(mode="json") == before
    assert [f.model_dump(mode="json") for f in repository.facts()] == before_facts
    assert KEY not in str(job)


def start_blocked_job(client, monkeypatch, fake_connection):
    seed_existing_data(client)
    enable_remote(client)
    entered, release = threading.Event(), threading.Event()
    instances, sent = install_reasoner(monkeypatch, entered=entered, release=release)
    before = client.app.state.repository.latest()[1].model_dump(mode="json")
    result = []
    worker = threading.Thread(target=lambda: result.append(client.post("/api/process", json={"source_id": TARGET}).json()), daemon=True)
    worker.start()
    assert entered.wait(4), "Synthetic provider was not invoked"
    return release, worker, result, instances, sent, before


def test_progress_reads_and_cancel_remain_responsive_during_model_wait(client, monkeypatch, fake_connection):
    release, worker, result, instances, sent, before = start_blocked_job(client, monkeypatch, fake_connection)
    observations, finished = [], threading.Event()

    def read_and_cancel():
        jobs = client.app.state.repository.jobs()
        running = next(job for job in jobs if job.status == "running")
        progress = client.get(f"/api/jobs/{running.id}")
        observations.append(progress.json())
        observations.append(client.post(f"/api/jobs/{running.id}/cancel").json())
        finished.set()

    reader = threading.Thread(target=read_and_cancel, daemon=True)
    reader.start()
    try:
        assert finished.wait(2), "Model transmission is holding the repository lock; progress/cancel cannot be read"
        assert observations[0]["status"] == "running"
        assert observations[0]["progress"]["total_messages"] == 2
        assert observations[1]["cancel_requested"]
    finally:
        release.set()
        worker.join(5)
        reader.join(5)
    assert result and result[0]["status"] == "cancelled", result
    assert client.app.state.repository.latest()[1].model_dump(mode="json") == before
    assert len(sent) == 1 and all(i.closed for i in instances)


def test_source_change_during_transmission_prevents_commit(client, monkeypatch, fake_connection):
    release, worker, result, instances, sent, before = start_blocked_job(client, monkeypatch, fake_connection)
    try:
        add_messages(client, TARGET, 1, prefix="arrived-during-model")
    finally:
        release.set()
        worker.join(5)
    assert result and result[0]["status"] == "failed", result
    assert client.app.state.repository.latest()[1].model_dump(mode="json") == before
    assert len(client.get("/api/messages", params={"source_id": TARGET}).json()) == 3
    assert all(i.closed for i in instances)


@pytest.fixture(autouse=True)
def legacy_batch_pipeline_contract(monkeypatch):
    """Keep these historical batch-cache tests on their explicit legacy seam."""
    from app.services.processing import ProcessingService
    monkeypatch.setattr(ProcessingService, "_run", ProcessingService._run_legacy)
