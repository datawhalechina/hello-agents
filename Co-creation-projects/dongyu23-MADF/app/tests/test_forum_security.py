from unittest.mock import AsyncMock, patch

from app.crud import create_user
from app.schemas import UserCreate
from starlette.websockets import WebSocketDisconnect


def _login(client, username, password="password"):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _register(client, username):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password", "role": "admin"},
    )
    assert response.status_code == 200
    return response.json()


def _create_forum(client, headers):
    persona = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={"name": "Security Persona"},
    )
    assert persona.status_code == 200
    forum = client.post(
        "/api/v1/forums/",
        headers=headers,
        json={"topic": "Security Forum", "participant_ids": [persona.json()["id"]]},
    )
    assert forum.status_code == 200
    return forum.json()["id"]


def test_public_registration_cannot_grant_admin(client):
    user = _register(client, "role-escalation")
    assert user["role"] == "user"


def test_forum_resources_require_owner_or_admin(client, db):
    _register(client, "owner")
    _register(client, "intruder")
    owner_headers = _login(client, "owner")
    intruder_headers = _login(client, "intruder")
    forum_id = _create_forum(client, owner_headers)

    assert client.get(f"/api/v1/forums/{forum_id}").status_code == 401
    assert client.get(f"/api/v1/forums/{forum_id}/messages", headers=intruder_headers).status_code == 403
    assert client.get(f"/api/v1/forums/{forum_id}/logs", headers=intruder_headers).status_code == 403
    assert client.post(
        f"/api/v1/forums/{forum_id}/chat",
        headers=intruder_headers,
        json={"content": "unauthorized"},
    ).status_code == 403

    admin = create_user(db, UserCreate(username="admin", password="password", role="admin"))
    assert admin.role == "admin"
    admin_headers = _login(client, "admin")
    assert client.get(f"/api/v1/forums/{forum_id}", headers=admin_headers).status_code == 200


def test_stop_forum_checks_ownership(client):
    _register(client, "stop-owner")
    _register(client, "stop-intruder")
    owner_headers = _login(client, "stop-owner")
    intruder_headers = _login(client, "stop-intruder")
    forum_id = _create_forum(client, owner_headers)

    assert client.post(f"/api/v1/forums/{forum_id}/stop", headers=intruder_headers).status_code == 403
    response = client.post(f"/api/v1/forums/{forum_id}/stop", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "closed"}
    assert client.get(f"/api/v1/forums/{forum_id}", headers=owner_headers).json()["status"] == "closed"


def test_forum_chat_rejects_blank_content(client):
    _register(client, "chat-owner")
    owner_headers = _login(client, "chat-owner")
    forum_id = _create_forum(client, owner_headers)

    response = client.post(
        f"/api/v1/forums/{forum_id}/chat",
        headers=owner_headers,
        json={"content": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Content is required"


def test_websocket_requires_valid_owner_token(client):
    _register(client, "ws-owner")
    _register(client, "ws-intruder")
    owner_headers = _login(client, "ws-owner")
    intruder_headers = _login(client, "ws-intruder")
    forum_id = _create_forum(client, owner_headers)
    owner_token = owner_headers["Authorization"].removeprefix("Bearer ")
    intruder_token = intruder_headers["Authorization"].removeprefix("Bearer ")

    for path in (
        f"/api/v1/forums/{forum_id}/ws",
        f"/api/v1/forums/{forum_id}/ws?token=invalid",
        f"/api/v1/forums/{forum_id}/ws?token={intruder_token}",
    ):
        try:
            with client.websocket_connect(path) as websocket:
                websocket.receive_text()
                raise AssertionError("unauthorized websocket remained open")
        except WebSocketDisconnect as exc:
            assert exc.code == 1008

    with client.websocket_connect(f"/api/v1/forums/{forum_id}/ws?token={owner_token}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"
