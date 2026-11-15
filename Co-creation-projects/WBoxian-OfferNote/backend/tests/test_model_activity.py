from fastapi.testclient import TestClient

from app.main import create_app


def test_model_activity_filters_noise_and_preserves_unknown_usage(tmp_path):
    app = create_app(str(tmp_path / "activity.sqlite3"))
    store = app.state.store
    wid = "demo-development"
    examples = [
        ("paid", {"tokens": 120, "model_requests": 2, "usage_complete": True}),
        ("unknown", {"tokens": None, "model_requests": 1}),
        ("partial", {"tokens": 0, "model_requests": 2, "usage_complete": False}),
        ("legacy-paid", {"tokens": 12}),
        ("legacy-unknown", {"tokens": None}),
        ("preflight", {"tokens": None, "model_requests": 0}),
        ("zero", {"tokens": 0, "model_requests": 1, "usage_complete": True}),
        ("offline", {"tokens": 999, "mode": "demo"}),
    ]
    for name, fields in examples:
        store.event(wid, {"mode": "live", "stage": "analysis", "name": name, **fields})
    for _ in range(105):
        store.event(wid, {"mode": "live", "stage": "tool", "tokens": None})
    with TestClient(app) as client:
        assert len(client.get(f"/api/workspaces/{wid}/events").json()) == 100
        result = client.get(f"/api/workspaces/{wid}/events?model_only=true")
        assert result.status_code == 200
        rows = result.json()
        assert {e["name"] for e in rows} == {
            "paid",
            "unknown",
            "partial",
            "legacy-paid",
            "legacy-unknown",
        }
        assert sum(e["tokens"] or 0 for e in rows) == 132


def test_model_activity_limit_is_applied_after_filtering(tmp_path):
    app = create_app(str(tmp_path / "activity.sqlite3"))
    store = app.state.store
    for i in range(110):
        store.event(
            "demo-development", {"mode": "live", "stage": "judge", "tokens": i + 1}
        )
    for _ in range(110):
        store.event(
            "demo-development", {"mode": "live", "stage": "tool", "tokens": None}
        )
    rows = store.events("demo-development", model_only=True)
    assert len(rows) == 100
    assert rows[0]["tokens"] == 110 and rows[-1]["tokens"] == 11
