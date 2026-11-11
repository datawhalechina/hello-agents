import pytest
from fastapi.testclient import TestClient

from app import demo
from app.engine import ModelError
from app.interview import demo_decision
from app.main import create_app


@pytest.fixture
def guided(tmp_path, monkeypatch):
    app = create_app(str(tmp_path / "guided.sqlite3"))
    calls = []

    def model(stage, context, schema):
        calls.append((stage, context))
        if stage == "analysis":
            return demo.analyze(context["resume"], context["job"])
        if stage == "interview":
            return demo_decision(app.state.engine, context["session"])
        if stage == "demonstration_answer":
            return {
                "answer": "我负责本地 FastAPI 接口；字段错误返回 422，缺失文档返回 404。模型调用在数据库写事务外执行，尚未验证线上性能。"
            }
        raise AssertionError(stage)

    monkeypatch.setattr(app.state.engine, "live", model)
    with TestClient(app) as client:
        wid = "demo-development"
        assert (
            client.post(
                f"/api/workspaces/{wid}/analyze", json={"mode": "live"}
            ).status_code
            == 200
        )
        response = client.post(
            f"/api/workspaces/{wid}/sessions",
            json={"mode": "live", "demonstration": True, "count": 4},
        )
        assert response.status_code == 201, response.text
        session = response.json()["sessions"][-1]
        yield client, app, calls, wid, session


def test_model_answer_is_cached_and_submission_is_explicit(guided):
    client, app, calls, wid, session = guided
    base = f"/api/workspaces/{wid}/sessions/{session['id']}"
    question = session["questions"][0]
    first = client.post(
        base + "/demonstration-answer", json={"question_id": question["id"]}
    )
    assert first.status_code == 200
    assert (
        client.post(
            base + "/demonstration-answer", json={"question_id": question["id"]}
        ).json()
        == first.json()
    )
    assert sum(stage == "demonstration_answer" for stage, _ in calls) == 1
    assert app.state.store.get(wid)["sessions"][-1]["turns"] == []
    result = client.post(
        base + "/answers",
        json={
            "question_id": question["id"],
            "answer": first.json()["answer"],
            "request_id": "guided-answer-001",
        },
    )
    assert result.status_code == 200, result.text
    stored = result.json()["sessions"][-1]
    assert stored["turns"][0]["answer_source"] == "model_demonstration"
    assert (
        client.post(
            base + "/demonstration-answer", json={"question_id": question["id"]}
        ).status_code
        == 409
    )
    events = app.state.store.events(wid)
    assert any(
        e["stage"] == "demonstration_answer" and e["mode"] == "live" for e in events
    )
    prompt = next(
        context for stage, context in calls if stage == "demonstration_answer"
    )
    assert (
        "scenario_notes" in prompt and "rubric" not in prompt and "report" not in prompt
    )


def test_demonstration_failure_preserves_question_and_does_not_fake_answer(
    guided, monkeypatch
):
    client, app, _, wid, session = guided
    monkeypatch.setattr(
        app.state.engine,
        "live",
        lambda *_: (_ for _ in ()).throw(ModelError("模拟供应商失败")),
    )
    response = client.post(
        f"/api/workspaces/{wid}/sessions/{session['id']}/demonstration-answer",
        json={"question_id": session["questions"][0]["id"]},
    )
    assert response.status_code == 502
    stored = app.state.store.get(wid)["sessions"][-1]
    assert stored["turns"] == [] and "demonstration_drafts" not in stored
    assert stored["questions"] == session["questions"]


def test_personal_or_offline_sessions_cannot_request_model_demonstration(guided):
    client, _, _, wid, _ = guided
    response = client.post(
        f"/api/workspaces/{wid}/sessions", json={"mode": "demo", "demonstration": True}
    )
    assert response.status_code == 409
    personal = client.post("/api/workspaces", json={"name": "个人练习"}).json()
    personal_id = personal["id"]
    client.put(
        f"/api/workspaces/{personal_id}/materials",
        json={"resume": demo.RESUME, "job": demo.JOB},
    )
    client.post(f"/api/workspaces/{personal_id}/analyze", json={"mode": "live"})
    normal = client.post(
        f"/api/workspaces/{personal_id}/sessions", json={"mode": "live"}
    ).json()["sessions"][-1]
    assert (
        client.post(
            f"/api/workspaces/{personal_id}/sessions/{normal['id']}/demonstration-answer",
            json={"question_id": normal["questions"][0]["id"]},
        ).status_code
        == 409
    )


def test_all_demo_session_entrypoints_enable_model_answers(guided):
    client, _, _, wid, _ = guided
    response = client.post(f"/api/workspaces/{wid}/sessions", json={"mode": "live"})
    assert response.status_code == 201
    assert response.json()["sessions"][-1]["demonstration"] is True


def test_existing_unmarked_demo_session_can_generate_without_losing_answers(guided):
    client, app, _, wid, session = guided
    item = app.state.store.get(wid)
    item["sessions"][-1]["demonstration"] = False
    app.state.store.save(item, item["revision"])
    response = client.post(
        f"/api/workspaces/{wid}/sessions/{session['id']}/demonstration-answer",
        json={"question_id": session["questions"][0]["id"]},
    )
    assert response.status_code == 200
    stored = app.state.store.get(wid)["sessions"][-1]
    assert stored["demonstration"] is True
    assert stored["turns"] == [] and stored["questions"] == session["questions"]
    assert (
        client.put(
            f"/api/workspaces/{wid}/materials",
            json={"resume": demo.RESUME + "\n修改材料", "job": demo.JOB},
        ).status_code
        == 200
    )
    client.post(f"/api/workspaces/{wid}/analyze", json={"mode": "live"})
    assert (
        client.post(
            f"/api/workspaces/{wid}/sessions",
            json={"mode": "live", "demonstration": True},
        ).status_code
        == 409
    )


def test_catalog_migrates_only_builtin_offline_records(tmp_path):
    app = create_app(str(tmp_path / "legacy.sqlite3"))
    store = app.state.store
    personal = store.create("我的产品项目", "Agent 产品经理")
    store.create(
        "旧产品演示", "产品经理", workspace_id="demo-product", demo_role="product"
    )
    store.create(
        "旧算法演示", "算法工程师", workspace_id="demo-algorithm", demo_role="algorithm"
    )
    item = store.get("demo-development")
    item["analysis"] = {"mode": "demo"}
    item["sessions"] = [
        {"id": "offline", "mode": "demo"},
        {"id": "live", "mode": "live"},
    ]
    store.save(item, item["revision"])
    store.ensure_demos()
    store.ensure_demos()
    assert {w["id"] for w in store.list()} == {personal["id"], "demo-development"}
    assert store.get("demo-development")["analysis"] is None
    assert store.get("demo-development")["sessions"] == [{"id": "live", "mode": "live"}]
    assert store.get(personal["id"])["name"] == "我的产品项目"
