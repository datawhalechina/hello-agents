import pytest
from fastapi.testclient import TestClient

from app.db.client import db_manager, get_db
from app.main import app as fastapi_app


@pytest.fixture(autouse=True)
def helloagents_test_config(monkeypatch):
    """Give directly constructed HelloAgents agents an inert test configuration."""
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("BASE_URL", "https://example.test/v1/")


@pytest.fixture(scope="function")
def test_database(tmp_path):
    """Point the global database manager at an isolated database per test."""
    original_state = {
        "url": db_manager.url,
        "is_remote": db_manager.is_remote,
        "is_postgres": db_manager.is_postgres,
        "auth_token": db_manager.auth_token,
    }
    database_path = (tmp_path / "madf.db").resolve().as_posix()
    db_manager.url = f"file:{database_path}"
    db_manager.is_remote = False
    db_manager.is_postgres = False
    db_manager.auth_token = None
    db_manager.init_db()

    yield

    for name, value in original_state.items():
        setattr(db_manager, name, value)


@pytest.fixture(scope="function")
def db(test_database):
    connection = db_manager.get_connection()
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture(scope="function")
def client(test_database):
    def override_get_db():
        connection = db_manager.get_connection()
        try:
            yield connection
        finally:
            connection.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()
