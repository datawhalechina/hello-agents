from fastapi.testclient import TestClient

from resume_agent.api.app import create_app
from tests.fakes import StubAuditAgent, StubQuestionWriter


def create_interview(client):
    base = client.post(
        "/fact-bases",
        json={"target": {"role": "Data Analyst"}},
    ).json()
    base = client.post(
        f"/fact-bases/{base['id']}/experiences",
        json={"organization": "Yunshu", "role": "Data Analyst"},
    ).json()
    experience = base["experiences"][0]
    session_response = client.post(
        "/sessions",
        json={
            "fact_base_id": base["id"],
            "active_experience_id": experience["id"],
        },
    )
    return base, experience, session_response


def test_create_interview_session(tmp_path):
    app = create_app(
        tmp_path / "resume-agent.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, response = create_interview(client)

    assert response.status_code == 201
    assert response.json()["fact_base_id"] == base["id"]
    assert response.json()["active_experience_id"] == experience["id"]


def test_answer_proposes_fact_without_mutating_base(tmp_path):
    app = create_app(
        tmp_path / "resume-agent.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, session_response = create_interview(client)
        session = session_response.json()
        answer = client.post(
            f"/sessions/{session['id']}/answers",
            json={"message": "Built the weekly dashboard"},
        )
        fetched = client.get(f"/fact-bases/{base['id']}")

    assert answer.status_code == 200
    assert answer.json()["proposal"]["dimension"] == "action"
    assert fetched.json()["experiences"][0]["statements"]["action"] == []


def test_confirmation_updates_base_and_returns_one_question(tmp_path):
    app = create_app(
        tmp_path / "resume-agent.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, session_response = create_interview(client)
        session = session_response.json()
        proposal = client.post(
            f"/sessions/{session['id']}/answers",
            json={"message": "Built the weekly dashboard"},
        ).json()["proposal"]
        confirmed = client.post(
            f"/sessions/{session['id']}/proposals/{proposal['id']}/confirm"
        )
        fetched = client.get(f"/fact-bases/{base['id']}")

    assert confirmed.status_code == 200
    assert len(confirmed.json()["questions"]) == 1
    assert fetched.json()["revision"] == 2
    assert fetched.json()["experiences"][0]["statements"]["action"]


def test_two_unknown_answers_skip_dimension(tmp_path):
    app = create_app(
        tmp_path / "resume-agent.db",
        fact_audit_agent=StubAuditAgent(),
        question_writer=StubQuestionWriter(),
    )
    with TestClient(app) as client:
        base, experience, session_response = create_interview(client)
        session = session_response.json()
        first = client.post(
            f"/sessions/{session['id']}/unknown",
            json={"dimension": "result"},
        )
        second = client.post(
            f"/sessions/{session['id']}/unknown",
            json={"dimension": "result"},
        )
        question = client.get(f"/sessions/{session['id']}/next-question")

    assert first.json()["skipped"] is False
    assert second.json()["skipped"] is True
    assert question.json()["dimension"] != "result"


def test_missing_llm_agent_returns_503_and_preserves_user_message(tmp_path):
    app = create_app(tmp_path / "resume-agent.db")
    with TestClient(app) as client:
        base, experience, session_response = create_interview(client)
        session = session_response.json()
        answer = client.post(
            f"/sessions/{session['id']}/answers",
            json={"message": "Please do not lose this answer"},
        )
        fetched_session = client.get(f"/sessions/{session['id']}")

    assert answer.status_code == 503
    assert fetched_session.status_code == 200
    assert fetched_session.json()["messages"][-1]["content"] == (
        "Please do not lose this answer"
    )


def test_session_rejects_experience_from_another_fact_base(tmp_path):
    app = create_app(
        tmp_path / "resume-agent.db",
        fact_audit_agent=StubAuditAgent(),
    )
    with TestClient(app) as client:
        first_base, first_experience, first_session = create_interview(client)
        second_base = client.post("/fact-bases", json={}).json()
        response = client.post(
            "/sessions",
            json={
                "fact_base_id": second_base["id"],
                "active_experience_id": first_experience["id"],
            },
        )

    assert response.status_code == 422
