from fastapi.testclient import TestClient

from resume_agent.agents.runtime import AgentCapabilityStatus
from resume_agent.api.app import create_app


def test_capabilities_report_configured_mentor_without_secrets(tmp_path):
    status = AgentCapabilityStatus.ready("deepseek-chat")
    with TestClient(
        create_app(tmp_path / "resume.db", agent_capabilities=status)
    ) as client:
        response = client.get("/capabilities")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["mentor"] is True
    assert response.json()["model"] == "deepseek-chat"
    payload = response.text.lower()
    assert "api_key" not in payload
    assert "base_url" not in payload
    assert "sk-" not in payload


def test_default_app_factory_remains_healthy_without_llm_configuration(tmp_path):
    from resume_agent.api.main import create_default_app

    app = create_default_app(
        environ={"RESUME_AGENT_DB": str(tmp_path / "offline.db")}
    )
    with TestClient(app) as client:
        health = client.get("/health")
        capabilities = client.get("/capabilities")

    assert health.json() == {"status": "ok"}
    assert capabilities.status_code == 200
    assert capabilities.json()["status"] == "degraded"
    assert capabilities.json()["mentor"] is False
    assert capabilities.json()["rendering"] is True


def test_injected_agent_gets_observable_capability_status(tmp_path):
    class AuditAgent:
        def propose(self, message, session, base):
            raise AssertionError("not called")

    with TestClient(
        create_app(tmp_path / "resume.db", fact_audit_agent=AuditAgent())
    ) as client:
        capabilities = client.get("/capabilities").json()

    assert capabilities["mentor"] is True
    assert capabilities["fact_audit"] is True
    assert capabilities["framework"] == "injected"


def test_capabilities_are_present_in_openapi(tmp_path):
    with TestClient(create_app(tmp_path / "resume.db")) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/capabilities" in paths
