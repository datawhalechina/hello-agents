from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_path=str(tmp_path / "test.db"), provider="local-demo", api_token="", _env_file=None))
    with TestClient(app) as value:
        yield value


@pytest.fixture
def demo(client):
    response = client.post("/api/demo")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["job"]["status"] == "completed", result
    return result
