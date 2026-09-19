import pytest

# client is provided by conftest.py

@pytest.fixture
def auth_header(client):
    # Create a test user first via API
    client.post("/api/v1/users/", json={"username": "testadmin", "password": "password", "role": "admin"})
    response = client.post("/api/v1/auth/login", data={"username": "testadmin", "password": "password"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_moderator(client, auth_header):
    response = client.post(
        "/api/v1/moderators/",
        json={
            "name": "AI Host",
            "title": "Senior Moderator",
            "bio": "Expert in debate",
            "system_prompt": "You are a host."
        },
        headers=auth_header
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI Host"
    assert "id" in data

def test_get_moderators(client, auth_header):
    # Create one first
    client.post(
        "/api/v1/moderators/",
        json={"name": "Host 1"},
        headers=auth_header
    )
    
    response = client.get("/api/v1/moderators/", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(m["name"] == "Host 1" for m in data)

def test_delete_moderator(client, auth_header):
    # Create
    res = client.post(
        "/api/v1/moderators/",
        json={"name": "Host To Delete"},
        headers=auth_header
    )
    mod_id = res.json()["id"]
    
    # Delete
    del_res = client.delete(f"/api/v1/moderators/{mod_id}", headers=auth_header)
    assert del_res.status_code == 200
    
    # Verify gone
    get_res = client.get(f"/api/v1/moderators/{mod_id}", headers=auth_header)
    assert get_res.status_code == 404
