from fastapi.testclient import TestClient

from resume_agent.api.app import create_app
from tests.fakes import StubAuditAgent, StubQuestionWriter


def seed(client):
    base = client.post(
        "/fact-bases", json={"target": {"role": "Data Analyst"}}
    ).json()
    base = client.post(
        f"/fact-bases/{base['id']}/experiences",
        json={"organization": "Yunshu", "role": "Analyst"},
    ).json()
    experience = base["experiences"][0]
    session = client.post(
        "/sessions",
        json={
            "fact_base_id": base["id"],
            "active_experience_id": experience["id"],
        },
    ).json()
    return base, experience, session


def test_lists_fact_bases_for_browser_recovery(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        first = client.post("/fact-bases", json={}).json()
        second = client.post("/fact-bases", json={}).json()
        listed = client.get("/fact-bases")

    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {first["id"], second["id"]}


def test_recovers_session_by_fact_base_and_experience(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        base, experience, session = seed(client)
        listed = client.get(
            f"/fact-bases/{base['id']}/sessions",
            params={"experience_id": experience["id"]},
        )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [session["id"]]


def test_quality_report_is_computed_by_server(tmp_path):
    with TestClient(create_app(tmp_path / "app.db")) as client:
        base, experience, session = seed(client)
        response = client.get(
            f"/fact-bases/{base['id']}/experiences/{experience['id']}/quality"
        )

    assert response.status_code == 200
    assert response.json()["passes_gate"] is False
    assert response.json()["scores"]["action"] == 0


def test_current_question_is_idempotent_across_reruns(tmp_path):
    app = create_app(
        tmp_path / "app.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, session = seed(client)
        first = client.get(f"/sessions/{session['id']}/current-question")
        second = client.get(f"/sessions/{session['id']}/current-question")
        loaded = client.get(f"/sessions/{session['id']}").json()

    assert first.status_code == 200
    assert first.json() == second.json()
    assistant_messages = [m for m in loaded["messages"] if m["role"] == "assistant"]
    assert len(assistant_messages) == 1


def test_reject_removes_pending_proposal_without_changing_facts(tmp_path):
    app = create_app(
        tmp_path / "app.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, session = seed(client)
        proposal = client.post(
            f"/sessions/{session['id']}/answers",
            json={"message": "Built a dashboard"},
        ).json()["proposal"]
        rejected = client.post(
            f"/sessions/{session['id']}/proposals/{proposal['id']}/reject"
        )
        loaded_base = client.get(f"/fact-bases/{base['id']}").json()

    assert rejected.status_code == 200
    assert proposal["id"] not in rejected.json()["pending_proposals"]
    assert loaded_base["revision"] == base["revision"]
