import importlib
import sys

from fastapi.testclient import TestClient

from resume_agent.api.app import create_app


def test_openapi_contains_product_resources(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        schema = client.get("/openapi.json").json()

    assert "/fact-bases" in schema["paths"]
    assert "/sessions/{session_id}/answers" in schema["paths"]
    assert "/fact-bases/{fact_base_id}/versions" in schema["paths"]
    operation_tags = {
        tag
        for path in schema["paths"].values()
        for operation in path.values()
        for tag in operation.get("tags", [])
    }
    assert {"fact-bases", "interviews", "versions"} <= operation_tags


def test_default_entry_point_honors_database_environment(tmp_path, monkeypatch):
    database = tmp_path / "custom.db"
    monkeypatch.setenv("RESUME_AGENT_DB", str(database))
    sys.modules.pop("resume_agent.api.main", None)

    module = importlib.import_module("resume_agent.api.main")

    assert module.app.title == "ResumeAgent API"
    assert module.DATABASE_PATH == database
    assert database.exists()


def test_create_app_is_part_of_public_api():
    from resume_agent import create_app as public_create_app

    assert public_create_app is create_app
