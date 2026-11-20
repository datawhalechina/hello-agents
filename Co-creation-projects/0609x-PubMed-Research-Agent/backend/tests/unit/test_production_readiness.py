from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.main import app


def test_production_settings_accept_explicit_secure_values():
    settings = Settings(
        _env_file=None,
        app_env="production",
        debug=False,
        database_url="postgresql+asyncpg://app:strong-pass@db:5432/pubmed",
        cors_origins="https://research.example.com",
        trusted_hosts="research.example.com",
    )

    assert settings.is_production is True
    assert settings.cors_origin_list == ["https://research.example.com"]


def test_production_settings_reject_insecure_defaults():
    try:
        Settings(
            _env_file=None,
            app_env="production",
            debug=True,
            database_url="sqlite+aiosqlite:///./data/test.db",
            cors_origins="*",
            trusted_hosts="*",
        )
    except ValidationError as exc:
        message = str(exc)
        assert "DEBUG must be false" in message
        assert "DATABASE_URL must use PostgreSQL" in message
        assert "CORS_ORIGINS cannot contain '*'" in message
        assert "TRUSTED_HOSTS must list explicit production hosts" in message
    else:
        raise AssertionError("insecure production settings must fail fast")


def test_stale_job_threshold_must_exceed_worker_time_limit():
    try:
        Settings(
            _env_file=None,
            celery_task_time_limit=1800,
            search_job_stale_after_seconds=1800,
        )
    except ValidationError as exc:
        assert "must exceed CELERY_TASK_TIME_LIMIT" in str(exc)
    else:
        raise AssertionError("unsafe stale-job threshold must fail fast")


def test_liveness_and_security_headers():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "test-request-123"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"] == "test-request-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_readiness_reports_dependency_failure(monkeypatch):
    async def available():
        return True

    async def unavailable():
        return False

    monkeypatch.setattr("backend.app.api.v1.health._check_database", available)
    monkeypatch.setattr("backend.app.api.v1.health._check_redis", unavailable)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["components"] == {
        "database": "ok",
        "redis": "unavailable",
    }


def test_readiness_succeeds_when_dependencies_are_available(monkeypatch):
    async def available():
        return True

    monkeypatch.setattr("backend.app.api.v1.health._check_database", available)
    monkeypatch.setattr("backend.app.api.v1.health._check_redis", available)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
