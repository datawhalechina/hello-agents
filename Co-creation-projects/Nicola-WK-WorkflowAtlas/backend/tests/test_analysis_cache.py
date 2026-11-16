"""Cost-saving cache boundaries use only invented data and fake inference."""
import json
import threading

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.extraction.local import extract_local
from app.main import create_app
from test_model_settings import KEY, MODEL, BASE, check_connection, enable_remote, payload
from test_scoped_model_jobs import TARGET, OTHER, add_messages


@pytest.fixture
def cache_provider(monkeypatch):
    """Keep the real coordinator, verifier, API and persistence paths exercised."""
    from app.agents import orchestrator
    from app.extraction import remote
    monkeypatch.setattr(remote, "test_model_connection", lambda *args: {"ok": True, "detail": "Synthetic connection", "latency_ms": 0})
    state = {"calls": [], "fail_id": None, "block_id": None, "empty": False, "invalid": False, "entered": None, "release": None}

    class FakeReasoner:
        def __init__(self, **kwargs):
            self.model = kwargs["model"]
            self.cancel_check = kwargs.get("cancel_check")

        def extract_many(self, messages):
            if self.cancel_check and self.cancel_check():
                raise RuntimeError("Synthetic cancellation")
            state["calls"].append((self.model, tuple((m.source_id, m.id) for m in messages)))
            if state["entered"] is not None and messages[0].id == state["block_id"]:
                state["entered"].set()
                assert state["release"].wait(8), "Synthetic provider release timed out"
            if messages[0].id == state["fail_id"]:
                raise RuntimeError("Synthetic provider failure")
            facts = [] if state["empty"] else [fact for message in messages for fact in extract_local(message)]
            if state["invalid"] and facts:
                facts[0].evidence[0].quote = "Synthetic unsupported provider quote"
            return facts

        def classify(self, message):
            return "work"

        def extract(self, message):
            return self.extract_many([message])

        def close(self):
            pass

    monkeypatch.setattr(orchestrator, "RemoteReasoner", FakeReasoner)
    return state


def process(client, source=TARGET):
    response = client.post("/api/process", json={"source_id": source})
    assert response.status_code == 200, response.text
    return response.json()


def cache_rows(client):
    repository = client.app.state.repository
    with repository.lock:
        return {row[0]: json.loads(row[1]) for row in repository.connection.execute("SELECT key,payload FROM state WHERE key LIKE 'analysis_cache:%'").fetchall()}


def graph_snapshot(client):
    repository = client.app.state.repository
    return repository.latest()[0], [fact.model_dump(mode="json") for fact in repository.facts()]


def test_failed_later_batch_is_retried_without_repaying_completed_batches(client, cache_provider):
    add_messages(client, TARGET, 12)
    enable_remote(client)
    before = graph_snapshot(client)
    ordered_ids = [message.id for message in client.app.state.repository.messages()]
    cache_provider["fail_id"] = ordered_ids[5]
    failed = process(client)
    assert failed["status"] == "failed" and graph_snapshot(client) == before
    assert len(cache_rows(client)) == 1  # Only the fully verified first five.
    assert all(KEY not in json.dumps(row) for row in cache_rows(client).values())
    cache_provider["fail_id"] = None
    cache_provider["calls"].clear()
    retried = process(client)
    assert retried["status"] == "completed", retried
    assert [len(batch) for _, batch in cache_provider["calls"]] == [5, 2]
    assert {message for _, batch in cache_provider["calls"] for _, message in batch} == set(ordered_ids[5:])
    assert retried["progress"]["cached_messages"] == 5 and retried["progress"]["processed_messages"] == 12
    assert len(client.get("/api/facts", params={"source_id": TARGET}).json()) == 12
    assert len(cache_rows(client)) == 3


@pytest.mark.parametrize("empty", [False, True])
def test_identical_successful_batches_and_empty_results_are_cache_hits(client, cache_provider, empty):
    add_messages(client, TARGET, 7)
    enable_remote(client)
    cache_provider["empty"] = empty
    first = process(client)
    assert first["status"] == "completed", first
    expected_facts = [] if empty else client.get("/api/facts").json()
    assert len(cache_rows(client)) == 2
    cache_provider["calls"].clear()
    second = process(client)
    assert second["status"] == "completed", second
    assert cache_provider["calls"] == []
    assert second["progress"]["cached_messages"] == 7
    assert client.get("/api/facts").json() == expected_facts
    assert len(second["result"]["agent_results"]) == 6


@pytest.mark.parametrize("fail_later_batch", [False, True])
def test_completed_batch_cache_survives_app_restart(tmp_path, cache_provider, fail_later_batch):
    settings = Settings(database_path=str(tmp_path / "cache-restart.db"), provider="local-demo", _env_file=None)
    with TestClient(create_app(settings)) as first:
        add_messages(first, TARGET, 6)
        enable_remote(first)
        cache_provider["fail_id"] = "m-5" if fail_later_batch else None
        assert process(first)["status"] == ("failed" if fail_later_batch else "completed")
        assert len(cache_rows(first)) == (1 if fail_later_batch else 2)
    cache_provider["fail_id"] = None
    cache_provider["calls"].clear()
    with TestClient(create_app(settings)) as restarted:
        job = process(restarted)
        assert job["status"] == "completed", job
        assert len(cache_provider["calls"]) == (1 if fail_later_batch else 0)
        assert job["progress"]["cached_messages"] == (5 if fail_later_batch else 6)


@pytest.mark.parametrize("change", [{"model": "synthetic-next-model"}, {"base_url": "https://next.example/v1"}, {"api_key": "synthetic-next-key"}])
def test_model_endpoint_or_credential_change_invalidates_batches(client, cache_provider, change):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert process(client)["status"] == "completed"
    check_connection(client, **change)
    response = client.put("/api/model/settings", json=payload(**change))
    assert response.status_code == 200, response.text
    cache_provider["calls"].clear()
    job = process(client)
    assert job["status"] == "completed", job
    assert len(cache_provider["calls"]) == 1 and job["progress"]["cached_messages"] == 0


def test_changed_partial_batch_snapshot_invalidates_only_that_batch(client, cache_provider):
    add_messages(client, TARGET, 6)
    enable_remote(client)
    assert process(client)["status"] == "completed"
    add_messages(client, TARGET, 1, prefix="new")
    cache_provider["calls"].clear()
    job = process(client)
    assert job["status"] == "completed", job
    assert len(cache_provider["calls"]) == 1
    assert len(cache_provider["calls"][0][1]) == 2 and job["progress"]["cached_messages"] == 5


def test_changed_prompt_invalidates_previously_completed_batches(client, cache_provider, monkeypatch):
    from app.agents import prompts
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert process(client)["status"] == "completed"
    monkeypatch.setattr(prompts, "BATCH_EXTRACTION_PROMPT", prompts.BATCH_EXTRACTION_PROMPT + "\nSynthetic new prompt version.")
    cache_provider["calls"].clear()
    job = process(client)
    assert job["status"] == "completed", job
    assert len(cache_provider["calls"]) == 1 and job["progress"]["cached_messages"] == 0


def test_source_deletion_removes_its_cache_and_preserves_other_source_cache(client, cache_provider):
    add_messages(client, TARGET, 5)
    add_messages(client, OTHER, 2)
    enable_remote(client)
    assert process(client)["status"] == "completed"
    assert process(client, OTHER)["status"] == "completed"
    assert {row["source_id"] for row in cache_rows(client).values()} == {TARGET, OTHER}
    preview = client.get("/api/sources/delete-preview", params={"source_id": TARGET}).json()
    response = client.request("DELETE", "/api/sources", params={"source_id": TARGET}, json={"confirmation": TARGET, "expected_messages": preview["messages"], "expected_version": preview["version"]})
    assert response.status_code == 200, response.text
    assert {row["source_id"] for row in cache_rows(client).values()} == {OTHER}
    cache_provider["calls"].clear()
    assert process(client, OTHER)["status"] == "completed"
    assert cache_provider["calls"] == []


@pytest.mark.parametrize("tamper", ["quote", "review"])
def test_forged_cached_evidence_or_review_cannot_enter_graph(client, cache_provider, tamper):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    assert process(client)["status"] == "completed"
    before = graph_snapshot(client)
    rows = cache_rows(client)
    assert len(rows) == 1
    key, cached = next(iter(rows.items()))
    if tamper == "quote":
        cached["facts"][0]["evidence"][0]["quote"] = "Invented quote absent from every original"
    else:
        cached["facts"][0]["review_status"] = "accepted"
    client.app.state.repository.write_state(key, cached)
    # Refuse a replacement result, so a failed cache check cannot hide behind
    # a successful paid retry or commit any previously collected facts.
    cache_provider["fail_id"] = "m-0"
    job = process(client)
    assert job["status"] == "failed", job
    assert graph_snapshot(client) == before


def test_new_batch_with_unsupported_evidence_is_not_cached(client, cache_provider):
    add_messages(client, TARGET, 5)
    enable_remote(client)
    before = graph_snapshot(client)
    cache_provider["invalid"] = True
    job = process(client)
    assert job["status"] == "failed", job
    assert cache_rows(client) == {} and graph_snapshot(client) == before


def test_cancellation_keeps_only_previously_completed_batch_cache(client, cache_provider):
    add_messages(client, TARGET, 7)
    enable_remote(client)
    before = graph_snapshot(client)
    entered, release = threading.Event(), threading.Event()
    cache_provider.update(block_id="m-5", entered=entered, release=release)
    results = []
    worker = threading.Thread(target=lambda: results.append(process(client)), daemon=True)
    worker.start()
    try:
        assert entered.wait(5), "Second synthetic batch did not start"
        running = next(job for job in client.app.state.repository.jobs() if job.status == "running")
        response = client.post(f"/api/jobs/{running.id}/cancel")
        assert response.status_code == 200 and response.json()["cancel_requested"]
    finally:
        release.set()
        worker.join(5)
    assert results and results[0]["status"] == "cancelled", results
    assert graph_snapshot(client) == before and len(cache_rows(client)) == 1
    cache_provider.update(block_id=None, entered=None, release=None)
    cache_provider["calls"].clear()
    retried = process(client)
    assert retried["status"] == "completed" and retried["progress"]["cached_messages"] == 5
    assert len(cache_provider["calls"]) == 1


@pytest.fixture(autouse=True)
def legacy_batch_pipeline_contract(monkeypatch):
    """Keep these historical batch-cache tests on their explicit legacy seam."""
    from app.services.processing import ProcessingService
    monkeypatch.setattr(ProcessingService, "_run", ProcessingService._run_legacy)
