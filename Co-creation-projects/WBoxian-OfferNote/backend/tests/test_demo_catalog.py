from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.demo import PROFILES
from app.main import create_app


def test_catalog_contains_one_role_and_reopening_keeps_live_progress(tmp_path):
    app = create_app(str(tmp_path / "catalog.sqlite3"))
    app.state.engine.live = lambda stage, context, schema: __import__(
        "app.demo", fromlist=["analyze"]
    ).analyze(context["resume"], context["job"])
    with TestClient(app) as client:
        items = client.get("/api/workspaces").json()
        assert {w["name"] for w in items} == {"Agent 开发"}
        for role in PROFILES:
            item = client.post("/api/workspaces/demo", params={"role": role}).json()
            assert (
                item["demo_role"] == role and item["resume"] == PROFILES[role]["resume"]
            )
            response = client.post(
                f"/api/workspaces/{item['id']}/analyze", json={"mode": "live"}
            )
            assert response.status_code == 200
            reopened = client.post("/api/workspaces/demo", params={"role": role}).json()
            assert (
                reopened["id"] == item["id"]
                and reopened["analysis"] == response.json()["analysis"]
            )
        assert len(client.get("/api/workspaces").json()) == 1
        assert client.post("/api/workspaces/demo?role=unknown").status_code == 422


def test_catalog_creation_is_concurrent_and_does_not_replace_personal_workspaces(
    tmp_path,
):
    app = create_app(str(tmp_path / "catalog.sqlite3"))
    store = app.state.store
    personal = store.create("个人工作区", "产品经理")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: store.ensure_demos(), range(8)))
    assert len(store.list()) == 2
    assert store.get(personal["id"])["name"] == "个人工作区"
