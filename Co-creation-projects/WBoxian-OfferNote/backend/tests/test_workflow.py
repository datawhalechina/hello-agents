import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import demo
from app.engine import ModelError
from app.main import create_app
from app.store import Conflict


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("OFFERNOTE_API_KEY", raising=False)
    app = create_app(str(tmp_path / "test.sqlite3"))
    with TestClient(app) as value:
        yield value


def prepared(client):
    workspace = client.post("/api/workspaces", json={"name": "测试工作区"}).json()
    client.put(
        f"/api/workspaces/{workspace['id']}/materials",
        json={"resume": demo.RESUME, "job": demo.JOB},
    )
    response = client.post(
        f"/api/workspaces/{workspace['id']}/analyze", json={"mode": "demo"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def session(client, workspace, count=2):
    response = client.post(
        f"/api/workspaces/{workspace['id']}/sessions",
        json={"mode": "demo", "count": count},
    )
    assert response.status_code == 201, response.text
    return response.json()["sessions"][-1]


def submit(client, w, s, index=0):
    response = client.post(
        f"/api/workspaces/{w['id']}/sessions/{s['id']}/answers",
        json={
            "question_id": s["questions"][len(s["turns"])]["id"],
            "answer": "我负责后端接口，使用 pytest 验证缺失字段和异常状态，还需要补充独立评测记录。",
            "request_id": f"answer-request-{index}",
        },
    )
    assert response.status_code == 200, response.text
    return client.get(f"/api/workspaces/{w['id']}").json()["sessions"][-1]


def completed(client, count=4):
    w = prepared(client)
    s = session(client, w, count)
    for index in range(count):
        if s["status"] != "active":
            break
        s = submit(client, w, s, index)
    return w, s


def test_complete_dynamic_workflow_and_retraining(client):
    w = prepared(client)
    s = session(client, w, 4)
    assert len(s["questions"]) == 1  # No pre-generated question list.
    for index in range(4):
        s = submit(client, w, s, index)
    assert s["status"] == "completed"
    assert len(s["questions"]) == len(s["turns"]) == 4
    assert s["questions"][2]["follow_up_depth"] == 2
    assert s["questions"][0]["topic_id"] == s["questions"][2]["topic_id"]
    assert s["questions"][3]["topic_id"] != s["questions"][0]["topic_id"]
    assert s["report"]["answered"] == 4 and s["report"]["total_score"] is None
    assert all("feedback" not in t for t in s["turns"])
    assert s["report"]["weak_topics"]
    response = client.post(
        f"/api/workspaces/{w['id']}/sessions",
        json={
            "mode": "demo",
            "count": 4,
            "focus": "weak",
            "source_session_id": s["id"],
        },
    )
    assert response.status_code == 201
    assert response.json()["sessions"][-1]["source_session_id"] == s["id"]
    exported = client.get(f"/api/workspaces/{w['id']}/sessions/{s['id']}/export")
    assert exported.status_code == 200 and "独立模型评审" in exported.text
    assert "演示" in exported.text and "未评估" in exported.text
    events = client.get(f"/api/workspaces/{w['id']}/events").json()
    assert {e["stage"] for e in events} == {"analysis", "interview", "tool", "judge"}
    assert all(e["mode"] == "demo" and e["tokens"] is None for e in events)


def test_answer_idempotency_and_conflicts(client):
    w = prepared(client)
    s = session(client, w, 4)
    path = f"/api/workspaces/{w['id']}/sessions/{s['id']}/answers"
    body = {
        "question_id": s["questions"][0]["id"],
        "answer": "我负责接口实现和测试。",
        "request_id": "same-request-01",
    }
    first = client.post(path, json=body)
    second = client.post(path, json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["revision"] == second.json()["revision"]
    assert len(second.json()["sessions"][-1]["turns"]) == 1
    assert client.post(path, json={**body, "answer": "另一个回答"}).status_code == 409
    assert (
        client.post(path, json={**body, "request_id": "new-request-02"}).status_code
        == 409
    )


def test_material_edit_invalidates_analysis_but_keeps_session_snapshot(client):
    w = prepared(client)
    s = session(client, w, 4)
    updated = client.put(
        f"/api/workspaces/{w['id']}/materials",
        json={"resume": "新简历材料" * 20, "job": w["job"]},
    ).json()
    assert updated["analysis"] is None
    assert updated["sessions"][-1]["snapshot"]["resume"] == w["resume"]
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/sessions", json={"mode": "demo"}
        ).status_code
        == 409
    )
    following = submit(client, w, s)
    assert following["questions"][-1]["source_quote"] in w["resume"]


def test_early_finish_only_reports_answered_questions(client):
    w = prepared(client)
    s = session(client, w, 12)
    path = f"/api/workspaces/{w['id']}/sessions/{s['id']}"
    assert client.post(path + "/finish").status_code == 409
    assert client.get(path + "/export").status_code == 409
    submit(client, w, s)
    result = client.post(path + "/finish")
    assert (
        result.status_code == 200
        and result.json()["sessions"][-1]["status"] == "awaiting_report"
    )
    current = client.get(f"/api/workspaces/{w['id']}").json()
    finished = current["sessions"][-1]
    assert finished["status"] == "completed" and finished["report"]["answered"] == 1
    assert len(finished["report"]["topics"]) == 1
    assert client.post(path + "/finish").json()["revision"] == current["revision"]


def test_no_weak_session_before_feedback(client):
    w = prepared(client)
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/sessions", json={"focus": "weak"}
        ).status_code
        == 409
    )


def test_retraining_uses_selected_report(client):
    w, first = completed(client, 2)
    second = session(client, w, 2)
    for index in range(2):
        second = submit(client, w, second, index)
    item = client.app.state.store.get(w["id"])
    titles = list(dict.fromkeys(c["topic"] for c in item["analysis"]["claims"]))
    assert len(titles) >= 2
    item["sessions"][0]["report"]["weak_topics"] = [titles[0]]
    item["sessions"][1]["report"]["weak_topics"] = [titles[1]]
    client.app.state.store.save(item, item["revision"])
    result = client.post(
        f"/api/workspaces/{w['id']}/sessions",
        json={
            "mode": "demo",
            "count": 4,
            "focus": "weak",
            "source_session_id": first["id"],
        },
    )
    assert result.status_code == 201
    assert [t["title"] for t in result.json()["sessions"][-1]["topics"]] == [titles[0]]


def test_live_failure_never_falls_back_or_saves(client):
    w = prepared(client)
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/analyze", json={"mode": "live"}
        ).status_code
        == 502
    )
    assert client.get(f"/api/workspaces/{w['id']}").json()["revision"] == w["revision"]
    assert client.post("/api/model-check").status_code == 502


def test_hallucinated_analysis_quotes_are_rejected(client, monkeypatch):
    w = client.post("/api/workspaces/demo").json()
    output = demo.analyze(w["resume"], w["job"])
    output["requirements"][0].update(status="supported", evidence_quote="不存在的证据")
    monkeypatch.setattr(client.app.state.engine, "live", lambda *_: output)
    result = client.post(f"/api/workspaces/{w['id']}/analyze", json={"mode": "live"})
    assert result.json()["analysis"]["requirements"][0]["status"] == "needs_review"
    output["claims"] = [{**output["claims"][0], "quote": "另一段虚构经历"}]
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/analyze", json={"mode": "live"}
        ).status_code
        == 502
    )


def test_scoring_failure_preserves_last_answer_and_can_retry(client, monkeypatch):
    from app import main

    original = main.judge
    monkeypatch.setattr(
        main, "judge", lambda *_: (_ for _ in ()).throw(ModelError("模拟评分服务失败"))
    )
    w = prepared(client)
    s = session(client, w)
    s = submit(client, w, s, 0)
    s = submit(client, w, s, 1)
    assert s["status"] == "awaiting_report" and len(s["turns"]) == 2
    assert s["report_error"] == "模拟评分服务失败"
    monkeypatch.setattr(main, "judge", original)
    client.post(f"/api/workspaces/{w['id']}/sessions/{s['id']}/finish")
    recovered = client.get(f"/api/workspaces/{w['id']}").json()["sessions"][-1]
    assert recovered["status"] == "completed" and len(recovered["turns"]) == 2


def test_topic_budget_and_duplicate_question_guard(client, monkeypatch):
    from app.interview import decide, demo_decision

    w = prepared(client)
    response = client.post(
        f"/api/workspaces/{w['id']}/sessions",
        json={"mode": "demo", "count": 8, "max_topic_turns": 2},
    )
    s = response.json()["sessions"][-1]
    s = submit(client, w, s, 0)
    s = submit(client, w, s, 1)
    assert s["questions"][2]["topic_id"] != s["questions"][0]["topic_id"]
    s["mode"] = "live"
    s["turns"].append(
        {
            "id": "next-topic-answer",
            "question": s["questions"][-1],
            "answer": "我负责新主题的具体实现。",
        }
    )
    engine = client.app.state.engine
    raw = demo_decision(engine, s)
    raw["question"]["text"] = s["questions"][0]["text"]
    monkeypatch.setattr(engine, "live", lambda *_: raw)
    with pytest.raises(ModelError, match="重复"):
        decide(engine, s)


def valid_judge(session):
    from app.interview import demo_judgement

    raw = demo_judgement(session)
    reference = {
        "turn_id": session["turns"][0]["id"],
        "quote": session["turns"][0]["answer"][:30],
    }
    for score in raw["scores"]:
        score.update(score=3, reason="有具体回答依据。", evidence=[reference])
    for topic in raw["topics"]:
        turn = next(
            t
            for t in session["turns"]
            if t["question"]["topic_id"] == topic["topic_id"]
        )
        topic.update(
            score=2, evidence=[{"turn_id": turn["id"], "quote": turn["answer"][:30]}]
        )
    return raw


def test_model_scores_use_fixed_weights_and_verified_quotes(client, monkeypatch):
    from app.interview import judge

    _, s = completed(client, 2)
    s["mode"] = "live"
    raw = valid_judge(s)
    monkeypatch.setattr(client.app.state.engine, "live", lambda *_: raw)
    result = judge(client.app.state.engine, s)
    assert result["total_score"] == 75 and result["covered_weight"] == 100
    for score in raw["scores"][:2]:
        score["evidence"] = [
            {"turn_id": s["turns"][0]["id"], "quote": "候选人从未说过的话"}
        ]
    raw["strengths"] = [
        {
            "text": "编造的优点。",
            "evidence": [{"turn_id": "fake-turn", "quote": "虚构内容"}],
        }
    ]
    result = judge(client.app.state.engine, s)
    assert result["total_score"] is None and result["covered_weight"] == 50
    assert result["scores"][0]["score"] is None and result["strengths"] == []
    assert result["warnings"]


def test_judge_repairs_nonliteral_quotes_before_discarding_scores(client, monkeypatch):
    import copy
    from app.interview import judge

    _, s = completed(client, 2)
    s["mode"] = "live"
    valid = valid_judge(s)
    invalid = copy.deepcopy(valid)
    for score in invalid["scores"]:
        score["evidence"][0]["quote"] = "我负责……并验证。"
    judge_contexts = []

    def respond(stage, context, _schema):
        if stage == "judge":
            judge_contexts.append(context)
            return copy.deepcopy(
                valid if context.get("evidence_corrections") else invalid
            )
        return {
            "answers": [
                {
                    "turn_id": t["turn_id"],
                    "answer": "学习示范：说明接口输入输出，并用失败场景和状态断言验证实现是否符合预期。",
                    "key_points": ["明确契约"],
                    "pitfalls": [],
                }
                for t in context["turns"]
            ]
        }

    monkeypatch.setattr(client.app.state.engine, "live", respond)
    result = judge(client.app.state.engine, s)
    assert result["total_score"] == 75 and result["covered_weight"] == 100
    assert len(judge_contexts) == 2
    assert judge_contexts[1]["evidence_corrections"]
    assert result["evidence_repaired"]


def test_judge_rejects_duplicate_dimensions_and_unasked_topics(client, monkeypatch):
    from app.interview import judge

    _, s = completed(client, 2)
    s["mode"] = "live"
    raw = valid_judge(s)
    monkeypatch.setattr(client.app.state.engine, "live", lambda *_: raw)
    raw["scores"][1]["dimension"] = raw["scores"][0]["dimension"]
    with pytest.raises(ModelError, match="维度"):
        judge(client.app.state.engine, s)
    raw["scores"][1]["dimension"] = "implementation"
    raw["topics"][0]["topic_id"] = "unasked-topic"
    with pytest.raises(ModelError, match="未作答"):
        judge(client.app.state.engine, s)


def test_tools_cannot_read_other_sessions_and_do_not_log_answers(client):
    from app.agent_tools import InterviewTools

    w = prepared(client)
    first = session(client, w, 4)
    second = session(client, w, 4)
    tools = InterviewTools(client.app.state.engine, first)
    output = tools.invoke(
        "read_material_evidence", {"topic_id": second["topics"][0]["id"]}
    )
    assert "error" in output and tools.events[-1]["status"] == "error"
    assert "answer" not in client.get(f"/api/workspaces/{w['id']}/events").text


def test_optimistic_revision_prevents_lost_updates(client):
    store = client.app.state.store
    w = store.create("测试", "开发")
    first, stale = store.get(w["id"]), store.get(w["id"])
    first["resume"] = "first update"
    store.save(first, first["revision"])
    stale["resume"] = "lost update"
    with pytest.raises(Conflict):
        store.save(stale, stale["revision"])
    assert store.get(w["id"])["resume"] == "first update"


def test_workspace_isolation_and_delete(client):
    first, second = prepared(client), prepared(client)
    claim = first["analysis"]["claims"][0]
    assert (
        client.put(
            f"/api/workspaces/{second['id']}/claims/{claim['id']}",
            json={"confirmed": True},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/workspaces/{first['id']}").status_code == 204
    assert client.get(f"/api/workspaces/{first['id']}").status_code == 404
    assert client.get(f"/api/workspaces/{second['id']}").status_code == 200
    with client.app.state.store.connect() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM events WHERE workspace_id=?", (first["id"],)
            ).fetchone()[0]
            == 0
        )


def test_claim_confirmation_and_material_noop(client):
    w = prepared(client)
    response = client.put(
        f"/api/workspaces/{w['id']}/materials",
        json={"resume": w["resume"], "job": w["job"]},
    )
    assert response.json()["revision"] == w["revision"]
    claim = w["analysis"]["claims"][0]
    confirmed = client.put(
        f"/api/workspaces/{w['id']}/claims/{claim['id']}", json={"confirmed": True}
    ).json()
    assert confirmed["analysis"]["claims"][0]["confirmed"] is True


@pytest.mark.parametrize("payload", [{"name": " "}, {"name": ""}, {"name": "x" * 81}])
def test_invalid_workspace_names(client, payload):
    assert client.post("/api/workspaces", json=payload).status_code == 422


def test_limits_and_invalid_state(client):
    w = client.post("/api/workspaces", json={"name": "新目标"}).json()
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/analyze", json={"mode": "demo"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/workspaces/{w['id']}/sessions", json={"count": 25}
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/workspaces/{w['id']}/materials",
            json={"resume": "x" * 24001, "job": ""},
        ).status_code
        == 422
    )
    assert client.get("/api/workspaces/not-a-workspace").status_code == 404


def test_text_and_docx_extraction(client):
    text = "项目经历：我使用 Python 开发后端接口，并维护自动化测试。"
    result = client.post(
        "/api/extract", files={"file": ("简历.md", text.encode(), "text/markdown")}
    )
    assert result.status_code == 200 and result.json()["text"] == text
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>',
        )
    result = client.post(
        "/api/extract", files={"file": ("resume.docx", data.getvalue())}
    )
    assert result.status_code == 200 and text in result.json()["text"]


@pytest.mark.parametrize(
    "name,content",
    [
        ("scan.pdf", b"invalid pdf"),
        ("image.png", b"not supported"),
        ("empty.txt", b""),
        ("short.txt", b"abc"),
        ("huge.txt", b"x" * (5 * 1024 * 1024 + 1)),
    ],
    ids=["invalid-pdf", "unsupported", "empty", "short", "oversized"],
)
def test_invalid_uploads(client, name, content):
    assert (
        client.post("/api/extract", files={"file": (name, content)}).status_code == 422
    )


def test_data_survives_application_restart(tmp_path):
    path = str(tmp_path / "persistent.sqlite3")
    with TestClient(create_app(path)) as first:
        w = prepared(first)
    with TestClient(create_app(path)) as second:
        assert (
            second.get(f"/api/workspaces/{w['id']}").json()["analysis"] == w["analysis"]
        )


def test_provider_failure_does_not_advance_question(client, monkeypatch):
    w = prepared(client)
    s = session(client, w)

    def fail(*_):
        raise ModelError("模拟供应商不可用")

    monkeypatch.setattr("app.interview.decide", fail)
    result = client.post(
        f"/api/workspaces/{w['id']}/sessions/{s['id']}/answers",
        json={
            "question_id": s["questions"][0]["id"],
            "answer": "这是我的回答内容。",
            "request_id": "provider-failed",
        },
    )
    assert result.status_code == 502
    stored = client.get(f"/api/workspaces/{w['id']}").json()["sessions"][-1]
    assert stored["turns"] == [] and stored["status"] == "active"


@pytest.mark.parametrize(
    "fault", ["unknown_topic", "missing_tool", "fake_progress", "wrong_action"]
)
def test_invalid_agent_decisions_never_commit_answers(client, monkeypatch, fault):
    from app.interview import demo_decision

    w = prepared(client)
    s = session(client, w, 8)
    engine = client.app.state.engine
    item = client.app.state.store.get(w["id"])
    item["sessions"][-1]["mode"] = "live"
    client.app.state.store.save(item, item["revision"])

    def decision(_stage, context, _schema):
        current = context["session"]
        raw = demo_decision(engine, current)
        if fault == "unknown_topic":
            raw["topic_id"] = "outside-session"
        elif fault == "fake_progress":
            raw["progress"]["evidence"][0]["quote"] = "不存在的回答引文"
        elif fault == "wrong_action":
            raw.update(action="finish", question=None, closure="sufficient")
        else:
            other = next(t for t in current["topics"] if t["status"] == "unvisited")
            raw.update(
                action="switch_topic",
                topic_id=other["id"],
                closure="knowledge_boundary",
            )
            current["_step_tool_events"] = []
        return raw

    monkeypatch.setattr(engine, "live", decision)
    result = client.post(
        f"/api/workspaces/{w['id']}/sessions/{s['id']}/answers",
        json={
            "question_id": s["questions"][0]["id"],
            "request_id": "invalid-agent-decision",
            "answer": "我负责具体实现，但有些指标尚未验证。",
        },
    )
    assert result.status_code == 502
    stored = client.get(f"/api/workspaces/{w['id']}").json()["sessions"][-1]
    assert stored["turns"] == [] and len(stored["questions"]) == 1


def test_judge_does_not_receive_interviewer_progress_or_decisions(client, monkeypatch):
    from app.interview import judge

    _, s = completed(client, 2)
    s["mode"] = "live"
    s["demonstration"] = True
    s["demonstration_drafts"] = {"private": "candidate-only scenario"}
    captured = {}

    def evaluate(_stage, context, _schema):
        captured.update(context)
        return valid_judge(s)

    monkeypatch.setattr(client.app.state.engine, "live", evaluate)
    judge(client.app.state.engine, s)
    assert "demonstration" not in captured and "demonstration_drafts" not in captured
    assert "trace" not in captured and "current_topic_id" not in captured
    assert all(set(topic) == {"id", "title"} for topic in captured["topics"])
    assert all("feedback" not in turn for turn in captured["turns"])
    assert all("id" not in turn["question"] for turn in captured["turns"])


def test_legacy_history_remains_readable_and_can_be_closed(client):
    from app.store import now

    w = prepared(client)
    legacy = {
        "id": "legacy-session",
        "analysis_id": w["analysis"]["id"],
        "status": "active",
        "mode": "demo",
        "created_at": now(),
        "questions": [
            {
                "id": "legacy-q",
                "text": "请解释旧项目中你负责的实现。",
                "topic": "旧主题",
            }
        ],
        "turns": [
            {
                "request_id": "legacy-request",
                "question": {"id": "legacy-q", "text": "旧问题", "topic": "旧主题"},
                "answer": "旧回答保持原样",
                "feedback": {
                    "verdict": "partial",
                    "gaps": ["待核实"],
                    "next_step": "补充证据",
                },
            }
        ],
        "report": None,
    }
    item = client.app.state.store.get(w["id"])
    item["sessions"].append(legacy)
    client.app.state.store.save(item, item["revision"])
    path = f"/api/workspaces/{w['id']}/sessions/legacy-session"
    assert (
        client.post(
            path + "/answers",
            json={
                "question_id": "legacy-q",
                "answer": "新回答",
                "request_id": "new-legacy-request",
            },
        ).status_code
        == 409
    )
    result = client.post(path + "/finish")
    assert result.status_code == 200
    assert result.json()["sessions"][-1]["turns"] == legacy["turns"]
    assert client.get(path + "/export").status_code == 200


def test_deleted_workspace_does_not_gain_late_background_events(client):
    w = prepared(client)
    store = client.app.state.store
    store.delete(w["id"])
    store.event(w["id"], {"stage": "judge", "status": "error"})
    with store.connect() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM events WHERE workspace_id=?", (w["id"],)
            ).fetchone()[0]
            == 0
        )
