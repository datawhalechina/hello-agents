import pytest

# client is provided by conftest.py

@pytest.fixture
def auth_header(client):
    client.post("/api/v1/users/", json={"username": "testuser", "password": "password"})
    response = client.post("/api/v1/auth/login", data={"username": "testuser", "password": "password"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_forum_with_moderator(client, auth_header):
    # 1. Create a moderator
    mod_res = client.post(
        "/api/v1/moderators/",
        json={"name": "Custom Host"},
        headers=auth_header
    )
    mod_id = mod_res.json()["id"]
    
    # 2. Create a persona (needed for participant)
    per_res = client.post(
        "/api/v1/personas/",
        json={"name": "Participant 1", "bio": "Bio"},
        headers=auth_header
    )
    per_id = per_res.json()["id"]
    
    # 3. Create forum with moderator_id
    forum_res = client.post(
        "/api/v1/forums/",
        json={
            "topic": "Test Topic",
            "participant_ids": [per_id],
            "moderator_id": mod_id,
            "duration_minutes": 30
        },
        headers=auth_header
    )
    
    assert forum_res.status_code == 200
    data = forum_res.json()
    assert data["topic"] == "Test Topic"
    assert data["moderator_id"] == mod_id
    assert data["moderator"]["name"] == "Custom Host"
    assert data["duration_minutes"] == 30
    assert data["start_time"] is None

def test_create_forum_default_moderator(client, auth_header):
    # Create a persona
    per_res = client.post(
        "/api/v1/personas/",
        json={"name": "Participant 1", "bio": "Bio"},
        headers=auth_header
    )
    per_id = per_res.json()["id"]
    
    # Create forum without moderator_id
    forum_res = client.post(
        "/api/v1/forums/",
        json={
            "topic": "Default Topic",
            "participant_ids": [per_id],
            "duration_minutes": 30
        },
        headers=auth_header
    )
    
    assert forum_res.status_code == 200
    data = forum_res.json()
    assert data["moderator_id"] is None
    assert data["duration_minutes"] == 30
    assert data["start_time"] is None
