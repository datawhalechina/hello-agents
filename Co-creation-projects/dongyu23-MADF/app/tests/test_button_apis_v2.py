import pytest
import random
import time
from fastapi.testclient import TestClient

def register_and_login(client):
    """Helper to create a user and get an access token."""
    username = "testuser_" + str(random.randint(10000, 99999))
    password = "password123"
    
    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "role": "user"}
    )
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    
    # 2. Login (This tests the Login Button API)
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    data = login_res.json()
    assert "access_token" in data
    return data["access_token"], username

def test_button_api_workflow(client):
    """
    Test the entire workflow corresponding to main button interactions:
    1. Login (Implicit in setup)
    2. Create Persona (Prerequisite for forum)
    3. Create Forum (Create Button)
    4. Start Forum (Start Button)
    5. Delete Forum (Delete Button)
    """
    # 1. Login
    token, _ = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a Persona (Needed for forum creation)
    persona_res = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={
            "name": "Test Persona",
            "title": "Tester",
            "bio": "A test persona",
            "theories": ["Test Theory"],
            "stance": "Neutral",
            "system_prompt": "You are a test.",
            "is_public": False
        }
    )
    assert persona_res.status_code == 200
    persona_id = persona_res.json()["id"]
    
    # 3. Create Forum (Simulates 'Create Forum' button click)
    forum_res = client.post(
        "/api/v1/forums/",
        headers=headers,
        json={
            "topic": "Button Test Forum",
            "participant_ids": [persona_id],
            "duration_minutes": 30
        }
    )
    assert forum_res.status_code == 200
    forum_data = forum_res.json()
    forum_id = forum_data["id"]
    assert forum_data["topic"] == "Button Test Forum"
    assert forum_data["status"] == "pending"
    
    # 4. Start Forum (Simulates 'Start Forum' button click)
    # Note: Start endpoint might be async or trigger background tasks
    start_res = client.post(
        f"/api/v1/forums/{forum_id}/start",
        headers=headers
    )
    # It might return 200 or 202
    assert start_res.status_code in [200, 202]
    
    # Wait for background task to start
    time.sleep(1)
    
    # Verify status changed to running
    get_res = client.get(f"/api/v1/forums/{forum_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "running"
    
    # 5. Delete Forum (Simulates 'Delete' button click)
    delete_res = client.delete(f"/api/v1/forums/{forum_id}", headers=headers)
    assert delete_res.status_code == 200
    
    # Verify deletion
    get_res_after = client.get(f"/api/v1/forums/{forum_id}", headers=headers)
    assert get_res_after.status_code == 404
