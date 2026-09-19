import pytest

def get_auth_headers(client, username="testuser", password="password123"):
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"username": "testuser", "password": "password123", "role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

def test_login(client):
    client.post("/api/v1/users/", json={"username": "testuser", "password": "password123", "role": "user"})
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_persona(client):
    # Register and login
    headers = get_auth_headers(client)
    
    # We still need owner_id in API, but current_user is inferred from token.
    # Actually, API ignores owner_id in body if we use current_user.id, 
    # but the schema might require it?
    # Checking endpoints/personas.py: create_new_persona takes owner_id param?
    # No, we updated it to use current_user.id.
    # BUT, the function signature `create_new_persona(persona, current_user, db)` 
    # means `owner_id` is NOT a query param anymore in our update?
    # Wait, in endpoints/personas.py I wrote:
    # def create_new_persona(persona: PersonaCreate, current_user: ..., db: ...):
    #     return create_persona(db=db, persona=persona, owner_id=current_user.id)
    # So `owner_id` query param is GONE.
    
    response = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={
            "name": "Socrates",
            "bio": "Greek philosopher",
            "theories": ["Method", "Ethics"],
            "is_public": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Socrates"
    # Ensure owner_id matches the user from token (which is created first, likely id=1)
    assert data["owner_id"] == 1

def test_persona_name_is_trimmed_and_blank_name_is_rejected(client):
    headers = get_auth_headers(client, username="persona-validation")

    created = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={"name": "  Trimmed Persona  "},
    )
    assert created.status_code == 200
    assert created.json()["name"] == "Trimmed Persona"

    blank = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={"name": "   "},
    )
    assert blank.status_code == 400
    assert blank.json()["message"] == "请求参数验证失败"

    update = client.put(
        f"/api/v1/personas/{created.json()['id']}",
        headers=headers,
        json={"name": "\t"},
    )
    assert update.status_code == 400

def test_database_startup_repairs_legacy_blank_persona_name(db):
    from app.db.client import db_manager, fetch_one

    db.execute(
        "INSERT INTO personas (owner_id, name, theories, is_public) VALUES (?, ?, ?, ?)",
        [1, "   ", "[]", 0],
    )
    row = fetch_one(db.execute("SELECT MAX(id) AS id FROM personas"))
    persona_id = row.id
    db.close()

    db_manager.init_db()
    repaired_db = db_manager.get_connection()
    try:
        repaired = fetch_one(
            repaired_db.execute("SELECT name FROM personas WHERE id = ?", [persona_id])
        )
        assert repaired.name == f"未命名智能体 #{persona_id}"

        db_manager.init_db()
        unchanged = fetch_one(
            repaired_db.execute("SELECT name FROM personas WHERE id = ?", [persona_id])
        )
        assert unchanged.name == repaired.name
    finally:
        repaired_db.close()

def test_create_forum(client):
    headers = get_auth_headers(client)
    
    # Create personas first
    p1 = client.post("/api/v1/personas/", headers=headers, json={"name": "P1"}).json()
    p2 = client.post("/api/v1/personas/", headers=headers, json={"name": "P2"}).json()
    
    # Create forum (creator_id inferred from token)
    response = client.post(
        "/api/v1/forums/",
        headers=headers,
        json={
            "topic": "Philosophy",
            "participant_ids": [p1["id"], p2["id"]]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "Philosophy"
    assert data["creator_id"] == 1

def test_post_message(client):
    headers = get_auth_headers(client)
    
    # Setup
    p1 = client.post("/api/v1/personas/", headers=headers, json={"name": "P1"}).json()
    f = client.post("/api/v1/forums/", headers=headers, json={"topic": "T", "participant_ids": [p1["id"]]}).json()
    
    response = client.post(
        f"/api/v1/forums/{f['id']}/messages",
        headers=headers,
        json={
            "forum_id": f['id'],
            "persona_id": p1['id'],
            "speaker_name": "P1",
            "content": "Know thyself",
            "turn_count": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Know thyself"

def test_get_messages(client):
    headers = get_auth_headers(client)
    p1 = client.post("/api/v1/personas/", headers=headers, json={"name": "P1"}).json()
    f = client.post("/api/v1/forums/", headers=headers, json={"topic": "T", "participant_ids": [p1["id"]]}).json()
    
    client.post(f"/api/v1/forums/{f['id']}/messages", headers=headers, json={
        "forum_id": f['id'], "persona_id": p1['id'], "speaker_name": "P1", "content": "Msg1", "turn_count": 1
    })
    
    response = client.get(f"/api/v1/forums/{f['id']}/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["content"] == "Msg1"

def test_chat_with_agent(client):
    response = client.post(
        "/api/v1/agents/chat",
        json={
            "agent_name": "TestAgent",
            "persona_json": {
                "name": "TestAgent",
                "title": "Tester",
                "bio": "A test agent",
                "theories": ["Testing"],
                "system_prompt": "You are a test agent."
            },
            "context_messages": [
                {"speaker": "User", "content": "Hello"}
            ]
        }
    )
    assert response.status_code != 404
    assert response.status_code != 422
