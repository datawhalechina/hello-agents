from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def assert_ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def main() -> None:
    assert_ok(client.get("/health"))
    frontend = client.get("/app/")
    assert frontend.status_code == 200
    assert "智能体平台" in frontend.text

    agents = assert_ok(client.get("/agents"))
    agent_ids = {agent["agent_id"] for agent in agents["agents"]}
    assert agents["total"] == 2
    assert "planner" not in agent_ids
    assert {"deep_research", "rss_digest"} <= agent_ids

    task = assert_ok(
        client.post(
            "/tasks",
            json={
                "title": "Research adapter test",
                "input": "agent platform architecture",
                "agent_id": "deep_research",
                "metadata": {"dry_run": True},
            },
        )
    )
    completed = assert_ok(client.post(f"/tasks/{task['task_id']}/run?background=false"))
    assert completed["status"] == "completed"

    batch = assert_ok(
        client.post(
            "/batch/run",
            json={
                "requests": {
                    "deep_research": {
                        "input": "ship v1",
                        "context": {"mode": "group_chat"},
                    },
                    "rss_digest": {
                        "input": "latest rss",
                        "context": {"mode": "group_chat"},
                    },
                }
            },
        )
    )
    assert "deep_research" in batch["responses"]
    assert "rss_digest" in batch["responses"]
    assert_ok(client.get("/events"))

    print("chapter16 platform smoke test passed")


if __name__ == "__main__":
    main()
