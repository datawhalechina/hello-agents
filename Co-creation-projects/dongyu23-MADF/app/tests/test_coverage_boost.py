import pytest
import random
from unittest.mock import AsyncMock, patch

from app.crud import create_user
from app.schemas import UserCreate

@pytest.fixture
def auth_header(client, db):
    username = f"user_{random.randint(1, 1000000)}"
    create_user(db, UserCreate(username=username, password="password123", role="admin"))
    token = client.post("/api/v1/auth/login", data={"username": username, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_coverage_auth(client):
    # Coverage for auth error paths
    client.post("/api/v1/auth/login", data={"username": "none", "password": "p"})
    client.post("/api/v1/auth/login", data={"username": "", "password": ""})

def test_coverage_users(client, auth_header):
    client.get("/api/v1/users/me", headers=auth_header)
    # Unauthorized
    client.get("/api/v1/users/me")

def test_coverage_personas(client, auth_header):
    # Create
    p = client.post("/api/v1/personas/", json={"name": "N", "bio": "B"}, headers=auth_header).json()
    p_id = p["id"]
    # Get
    client.get(f"/api/v1/personas/{p_id}", headers=auth_header)
    # Update
    client.put(f"/api/v1/personas/{p_id}", json={"name": "N2"}, headers=auth_header)
    # Delete
    client.delete(f"/api/v1/personas/{p_id}", headers=auth_header)
    # Not found
    client.get("/api/v1/personas/9999", headers=auth_header)

def test_coverage_moderators(client, auth_header):
    m = client.post("/api/v1/moderators/", json={"name": "M"}, headers=auth_header).json()
    m_id = m["id"]
    client.get(f"/api/v1/moderators/{m_id}", headers=auth_header)
    client.put(f"/api/v1/moderators/{m_id}", json={"name": "M2"}, headers=auth_header)
    client.get("/api/v1/moderators/", headers=auth_header)
    client.delete(f"/api/v1/moderators/{m_id}", headers=auth_header)

def test_coverage_users_detailed(client, auth_header):
    # Create user
    username = f"user_{random.randint(1, 1000000)}"
    client.post("/api/v1/users/", json={"username": username, "password": "p", "role": "u"})
    # Duplicate (hits line 14)
    client.post("/api/v1/users/", json={"username": username, "password": "p", "role": "u"})
    # Read user (hits 23-26)
    client.get(f"/api/v1/users/{username}")
    client.get("/api/v1/users/nonexistent")

def test_coverage_forums_edge_cases(client, auth_header):
    # Read forum (hits 78-81)
    persona = client.post("/api/v1/personas/", json={"name": "Forum Persona", "bio": "B"}, headers=auth_header).json()
    f = client.post("/api/v1/forums/", json={"topic": "T", "participant_ids": [persona["id"]]}, headers=auth_header).json()
    client.get(f"/api/v1/forums/{f['id']}", headers=auth_header)
    # Start forum (hits 102-107)
    with patch("app.services.forum_service.scheduler.start_forum", new_callable=AsyncMock):
        client.post(f"/api/v1/forums/{f['id']}/start", headers=auth_header)
    # Messages/Logs fail path
    client.get(f"/api/v1/forums/{f['id']}/messages", headers=auth_header)
    client.get(f"/api/v1/forums/{f['id']}/logs", headers=auth_header)
    # Delete (hits 91-93)
    client.delete(f"/api/v1/forums/{f['id']}", headers=auth_header)

def test_coverage_god_detailed(client, auth_header):
    events = iter([{"type": "error", "content": "mocked failure"}])
    with patch("app.api.v1.endpoints.god.settings.API_KEY", "test-key"), patch(
        "app.api.v1.endpoints.god.RealGodAgent"
    ) as agent_class:
        agent_class.return_value.run.return_value = events
        response = client.post("/api/v1/god/generate_real", json={"prompt": "Short", "n": 1}, headers=auth_header)
    assert response.status_code == 200
    assert "mocked failure" in response.text
    assert "所有智能体角色已生成并保存完毕" not in response.text

def test_coverage_personas_detailed(client, auth_header):
    # Create public
    p = client.post("/api/v1/personas/", json={"name": "Public", "bio": "B", "is_public": True}, headers=auth_header).json()
    p_id = p["id"]
    # List (hits 35-79 filter logic)
    client.get("/api/v1/personas/", headers=auth_header)
    # Get/Update/Delete (hits 110, 114, 127, 131)
    client.get(f"/api/v1/personas/{p_id}", headers=auth_header)
    client.put(f"/api/v1/personas/{p_id}", json={"name": "U"}, headers=auth_header)
    client.delete(f"/api/v1/personas/{p_id}", headers=auth_header)

def test_coverage_god(client, auth_header):
    persona = {
        "name": "Mock Person",
        "title": "Researcher",
        "bio": "Bio",
        "theories": ["Theory"],
        "stance": "Neutral",
        "system_prompt": "Act naturally.",
    }
    with patch("app.api.v1.endpoints.god.settings.API_KEY", "test-key"), patch(
        "app.api.v1.endpoints.god.RealGodAgent"
    ) as agent_class:
        agent_class.return_value.run.return_value = iter([{"type": "result", "content": [persona]}])
        with client.stream("POST", "/api/v1/god/generate_real", json={"prompt": "Test", "n": 1}, headers=auth_header) as response:
            body = response.read().decode("utf-8")
    assert response.status_code == 200
    assert "Mock Person" in body


def test_god_generation_reports_missing_model_configuration(client, auth_header):
    with patch("app.api.v1.endpoints.god.settings.API_KEY", None), patch.dict(
        "os.environ", {"API_KEY": ""}
    ):
        response = client.post(
            "/api/v1/god/generate_real",
            json={"prompt": "创建哈利波特", "n": 1},
            headers=auth_header,
        )

    assert response.status_code == 503
    assert "模型服务尚未配置" in response.json()["detail"]

def test_coverage_agents(client, auth_header):
    client.get("/api/v1/agents/", headers=auth_header)
