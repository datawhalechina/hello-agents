"""Malformed model settings must never echo submitted credential material."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize("method,path", [("POST", "/api/model/test"), ("PUT", "/api/model/settings")])
def test_invalid_model_request_does_not_echo_secret(method, path):
    marker = "synthetic-secret-invalid-request-1937"
    app = create_app(Settings(database_path=":memory:", _env_file=None))
    with TestClient(app) as client:
        response = client.request(method, path, json={"model": "synthetic", "base_url": "https://synthetic.invalid/v1", "api_key": {"invalid": marker}, "unexpected": marker})
        assert response.status_code == 422
        assert marker not in response.text
        assert all("input" not in item and "ctx" not in item for item in response.json()["detail"])
        assert not client.get("/api/model/settings").json()["api_key_configured"]
