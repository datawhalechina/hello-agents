def _auth_headers(client, username):
    client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    token = client.post("/api/v1/auth/login", data={"username": username, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_regular_user_cannot_assign_persona_to_another_owner(client):
    # Public personas are allowed, but ownership must come from the token.
    u = client.post("/api/v1/auth/register", json={"username": "err_user1", "password": "password123", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "err_user1", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        "/api/v1/personas/",
        params={"owner_id": 999},
        json={"name": "P", "bio": "B", "theories": [], "is_public": True},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["owner_id"] == u["id"]

def test_create_forum_rejects_empty_participants_before_legacy_creator_param(client):
    u = client.post("/api/v1/auth/register", json={"username": "err_user2", "password": "password123", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "err_user2", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        "/api/v1/forums/",
        params={"creator_id": 999},
        json={"topic": "T", "participant_ids": []},
        headers=headers
    )
    assert response.status_code == 400
    assert any("请至少选择一位智能体" in item["msg"] for item in response.json()["detail"])

def test_get_forum_not_found(client):
    assert client.get("/api/v1/forums/999/messages").status_code == 401
    response = client.get("/api/v1/forums/999/messages", headers=_auth_headers(client, "missing-reader"))
    assert response.status_code == 404
    assert "Forum not found" in response.json()["detail"]

def test_post_message_forum_not_found(client):
    assert client.post(
        "/api/v1/forums/999/messages",
        json={"forum_id": 999, "persona_id": 1, "speaker_name": "S", "content": "C", "turn_count": 1}
    ).status_code == 401
    response = client.post(
        "/api/v1/forums/999/messages",
        json={"forum_id": 999, "persona_id": 1, "speaker_name": "S", "content": "C", "turn_count": 1},
        headers=_auth_headers(client, "missing-writer"),
    )
    assert response.status_code == 404
    assert "Forum not found" in response.json()["detail"]
    
def test_post_message_persona_not_found(client):
    # Register and login
    u = client.post("/api/v1/auth/register", json={"username": "msg_user", "password": "password123", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "msg_user", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create forum
    persona = client.post("/api/v1/personas/", json={"name": "Message Persona", "bio": "B"}, headers=headers).json()
    f = client.post("/api/v1/forums/", json={"topic": "T", "participant_ids": [persona["id"]]}, headers=headers).json()

    response = client.post(
        f"/api/v1/forums/{f['id']}/messages",
        json={"forum_id": f['id'], "persona_id": 999, "speaker_name": "S", "content": "C", "turn_count": 1},
        headers=headers
    )
    assert response.status_code == 404

def test_chat_agent_invalid_initialization(client):
    # Mocking failure during agent init inside endpoint
    from unittest.mock import patch
    with patch("app.api.v1.endpoints.agents.ParticipantAgent", side_effect=Exception("Init Failed")):
        response = client.post(
            "/api/v1/agents/chat",
            json={
                "agent_name": "FailAgent",
                "persona_json": {"name": "Fail"},
                "context_messages": []
            }
        )
        assert response.status_code == 400
        assert "Failed to initialize agent" in response.json()["detail"]
