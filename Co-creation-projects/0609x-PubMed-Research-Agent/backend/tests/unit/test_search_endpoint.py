# -*- coding: utf-8 -*-
"""Tests for durable search-job API wiring and worker persistence."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import backend.app.models.analysis  # noqa: F401
import backend.app.models.article  # noqa: F401
import backend.app.models.search  # noqa: F401
from backend.agents.research_agent import ResearchReport
from backend.app.main import app
from backend.app.models.database import Base, get_db
from backend.app.models.search import Search

test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


class FakeAgent:
    def __init__(self, report=None, error=None):
        self.report = report
        self.error = error

    def research(self, *args, **kwargs):
        if self.error:
            raise self.error
        callback = kwargs.get("progress_callback")
        if callback:
            callback("summarizing", 85, "正在生成结构化研究综述")
        return self.report


class FakeRedis:
    def __init__(self):
        self.events = []

    async def publish(self, channel, payload):
        self.events.append((channel, payload))

    async def aclose(self):
        return None


def _report() -> ResearchReport:
    return ResearchReport(
        query="SEC61G in lung cancer",
        rewritten_query="SEC61G[Title/Abstract] AND lung cancer",
        model_used="deepseek-v4-flash",
        language="en",
        total_pubmed_hits=2,
        status="completed",
        articles=[
            {
                "pmid": "100",
                "title": "SEC61G in lung cancer",
                "abstract": "We studied SEC61G.",
                "doi": "10.1/x",
                "authors": [{"last_name": "Smith", "fore_name": "J"}],
                "journal": "Cancer Res",
                "publish_date": "2024",
                "publication_type": "Journal Article",
            }
        ],
        research_background="Background text",
        current_hotspots=[{"name": "hotspot", "evidence": "evidence"}],
        main_findings=["finding"],
        experimental_methods=[{"name": "method", "papers": ["100"]}],
        future_directions=[{"topic": "topic", "rationale": "rationale"}],
    )


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch):
    async def _reset():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        "backend.services.search_jobs.create_progress_redis", FakeRedis
    )
    monkeypatch.setattr("backend.app.api.v1.search.AsyncSessionLocal", TestSession)
    yield
    app.dependency_overrides.pop(get_db, None)
    asyncio.run(_reset())


def test_post_search_job_enqueues_and_exposes_status(monkeypatch):
    dispatched = {}

    def fake_apply_async(*, args, task_id):
        dispatched.update(args=args, task_id=task_id)

    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", fake_apply_async
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/search/jobs",
            json={
                "query": "SEC61G in lung cancer",
                "max_results": 20,
                "language": "zh",
                "search_mode": "keyword",
                "sort_by": "date_desc",
                "min_year": 2020,
                "max_year": 2025,
                "min_impact_factor": 5.5,
            },
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "queued"
        assert body["progress_percent"] == 0
        assert body["progress_stage"] == "queued"
        assert dispatched == {"args": [body["search_id"]], "task_id": body["job_id"]}

        status_resp = client.get(f"/api/v1/search/jobs/{body['job_id']}")
        detail = client.get(f"/api/v1/search/{body['search_id']}")

    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == body["job_id"]
    assert detail.status_code == 200
    assert detail.json()["language"] == "zh"
    assert detail.json()["min_impact_factor"] == 5.5


def test_cancel_search_job_is_persisted_and_revoked(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", lambda **kwargs: None
    )
    revoked = []
    monkeypatch.setattr(
        "backend.app.api.v1.search.celery_app.control.revoke",
        lambda job_id, terminate=False: revoked.append((job_id, terminate)),
    )
    with TestClient(app) as client:
        created = client.post("/api/v1/search/jobs", json={"query": "cancel me"}).json()
        resp = client.post(f"/api/v1/search/jobs/{created['job_id']}/cancel")
        status_resp = client.get(f"/api/v1/search/jobs/{created['job_id']}")

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["progress_percent"] == 100
    assert resp.json()["cancel_requested"] is True
    assert status_resp.json()["completed_at"] is not None
    assert revoked == [(created["job_id"], False)]


def test_enqueue_failure_returns_service_unavailable(monkeypatch):
    def fail_enqueue(**kwargs):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", fail_enqueue
    )
    with TestClient(app) as client:
        resp = client.post("/api/v1/search/jobs", json={"query": "SEC61G"})
        history = client.get("/api/v1/search/history").json()

    assert resp.status_code == 503
    assert history[0]["status"] == "failed"


def test_worker_executes_pipeline_and_persists_report(monkeypatch):
    monkeypatch.setattr("backend.services.search_jobs.AsyncSessionLocal", TestSession)
    monkeypatch.setattr(
        "backend.services.search_jobs.build_agent",
        lambda settings: FakeAgent(report=_report()),
    )

    async def seed_and_run() -> int:
        async with TestSession() as db:
            search = Search(
                job_id="job-worker-test",
                query_text="SEC61G",
                status="queued",
            )
            db.add(search)
            await db.commit()
            await db.refresh(search)
            search_id = search.id
        from backend.services.search_jobs import execute_search_job

        await execute_search_job(search_id)
        return search_id

    search_id = asyncio.run(seed_and_run())
    with TestClient(app) as client:
        detail = client.get(f"/api/v1/search/{search_id}")

    assert detail.status_code == 200
    data = detail.json()
    assert data["status"] == "completed"
    assert data["job_id"] == "job-worker-test"
    assert data["total_found"] == 2
    assert data["articles"][0]["pmid"] == "100"
    assert data["analysis"]["main_findings"] == ["finding"]


def test_terminal_job_sse_emits_snapshot_and_closes(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", lambda **kwargs: None
    )
    monkeypatch.setattr(
        "backend.app.api.v1.search.celery_app.control.revoke", lambda *args, **kwargs: None
    )
    with TestClient(app) as client:
        created = client.post("/api/v1/search/jobs", json={"query": "stream me"}).json()
        client.post(f"/api/v1/search/jobs/{created['job_id']}/cancel")
        response = client.get(f"/api/v1/search/jobs/{created['job_id']}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"status": "cancelled"' in response.text
    assert '"progress_percent": 100' in response.text


def test_history_lists_recent_queued_searches(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", lambda **kwargs: None
    )
    with TestClient(app) as client:
        client.post("/api/v1/search/jobs", json={"query": "first query"})
        client.post("/api/v1/search/jobs", json={"query": "second query"})
        history = client.get("/api/v1/search/history")

    assert history.status_code == 200
    items = history.json()
    assert len(items) == 2
    assert items[0]["query_text"] == "second query"
    assert items[1]["query_text"] == "first query"


def test_metrics_exposes_normalized_requests_and_durable_job_counts(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.v1.search.run_search_task.apply_async", lambda **kwargs: None
    )
    with TestClient(app) as client:
        client.post("/api/v1/search/jobs", json={"query": "observe me"})
        response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'pubmed_search_jobs_current{status="queued"} 1' in response.text
    assert 'route="/api/v1/search/jobs"' in response.text
