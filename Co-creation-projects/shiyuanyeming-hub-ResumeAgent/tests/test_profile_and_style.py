from fastapi.testclient import TestClient

from resume_agent.api.app import create_app


def create_version(client: TestClient, *, locale: str = "zh") -> dict:
    base = client.post("/fact-bases", json={}).json()
    base = client.post(
        f"/fact-bases/{base['id']}/experiences",
        json={"organization": "云数科技", "role": "数据分析师"},
    ).json()
    return client.post(
        f"/fact-bases/{base['id']}/versions",
        json={
            "name": "目标岗位版本",
            "locale": locale,
            "selected_experience_ids": [base["experiences"][0]["id"]],
        },
    ).json()


def test_profile_update_increments_revision_and_persists(tmp_path):
    with TestClient(create_app(tmp_path / "resume.db")) as client:
        base = client.post("/fact-bases", json={}).json()
        response = client.patch(
            f"/fact-bases/{base['id']}/profile",
            json={
                "name": "王明",
                "email": "wang@example.com",
                "phone": "138-0000-0000",
                "location": "东京",
                "links": ["https://example.com/wang"],
            },
        )
        fetched = client.get(f"/fact-bases/{base['id']}")

    assert response.status_code == 200
    assert response.json()["revision"] == base["revision"] + 1
    assert response.json()["profile"]["name"] == "王明"
    assert fetched.json()["profile"] == response.json()["profile"]


def test_version_style_is_explicitly_persisted(tmp_path):
    with TestClient(create_app(tmp_path / "resume.db")) as client:
        version = create_version(client, locale="zh")
        response = client.put(
            f"/versions/{version['id']}/style",
            json={"style": "经典墨色"},
        )
        fetched = client.get(f"/versions/{version['id']}")

    assert response.status_code == 200
    assert response.json()["styles"]["zh"] == "经典墨色"
    assert fetched.json()["styles"]["zh"] == "经典墨色"
