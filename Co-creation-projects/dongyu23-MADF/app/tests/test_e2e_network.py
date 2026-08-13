import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_cors_headers(client):
    # Test that CORS headers are present
    origin = "http://localhost:5173"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    # When allow_credentials=True, Starlette reflects the Origin header instead of returning '*'
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    if response.headers.get("content-type", "").startswith("text/html"):
        assert '<div id="app"></div>' in response.text
    else:
        assert response.json()["message"].startswith("Welcome to MADF API")

def test_global_exception_handler(client):
    # Mocking a call that triggers an exception
    from app.api.v1.endpoints import auth
    # We need to mock the function inside the module where it's used
    import app.api.v1.endpoints.auth as auth_mod
    
    original_get_user = auth_mod.get_user_by_username
    
    def mock_get_user(*args, **kwargs):
        raise ValueError("Unexpected error for testing")
        
    auth_mod.get_user_by_username = mock_get_user
    
    try:
        # Use a real endpoint that calls get_user_by_username
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test", "password": "test"}
        )
        # Global exception handler should catch this and return 500
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == 500
        assert "服务器内部错误" in data["message"]
    finally:
        auth_mod.get_user_by_username = original_get_user

def test_validation_error_handler(client):
    # Missing required fields
    response = client.post(
        "/api/v1/auth/login",
        data={} # Missing username and password
    )
    assert response.status_code == 400
    assert response.json()["message"] == "请求参数验证失败"

def test_404_handler(client):
    response = client.get("/api/v1/not-exists")
    assert response.status_code == 404
    assert response.json()["detail"] in {"Not Found", "API endpoint not found"}
