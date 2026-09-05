from fastapi.testclient import TestClient

from resume_agent.api.app import create_app


def create_base_with_experience(client):
    base = client.post("/fact-bases", json={}).json()
    return client.post(
        f"/fact-bases/{base['id']}/experiences",
        json={"organization": "Yunshu", "role": "Data Analyst"},
    ).json()


def create_version(client, base, name):
    return client.post(
        f"/fact-bases/{base['id']}/versions",
        json={
            "name": name,
            "target_role": name,
            "selected_experience_ids": [base["experiences"][0]["id"]],
        },
    )


def test_create_and_list_two_versions_from_one_fact_base(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        base = create_base_with_experience(client)
        first = create_version(client, base, "Data Analyst")
        second = create_version(client, base, "Product Analyst")
        listed = client.get(f"/fact-bases/{base['id']}/versions")

    assert first.status_code == 201
    assert second.status_code == 201
    assert {item["name"] for item in listed.json()} == {
        "Data Analyst",
        "Product Analyst",
    }


def test_clone_rename_and_delete_are_isolated(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        base = create_base_with_experience(client)
        original = create_version(client, base, "Original").json()
        clone = client.post(
            f"/versions/{original['id']}/clone",
            json={"name": "Tokyo"},
        ).json()
        renamed = client.patch(
            f"/versions/{clone['id']}",
            json={"name": "Tokyo Senior"},
        )
        deleted = client.delete(f"/versions/{clone['id']}")
        original_after = client.get(f"/versions/{original['id']}")
        clone_after = client.get(f"/versions/{clone['id']}")

    assert renamed.json()["name"] == "Tokyo Senior"
    assert deleted.status_code == 204
    assert original_after.status_code == 200
    assert clone_after.status_code == 404


def test_activate_keeps_exactly_one_active_version(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        base = create_base_with_experience(client)
        first = create_version(client, base, "First").json()
        second = create_version(client, base, "Second").json()
        client.post(f"/versions/{first['id']}/activate")
        activated = client.post(f"/versions/{second['id']}/activate")
        listed = client.get(f"/fact-bases/{base['id']}/versions").json()

    assert activated.status_code == 200
    assert [item["name"] for item in listed if item["is_active"]] == ["Second"]


def test_refresh_marks_versions_stale_after_fact_change(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        base = create_base_with_experience(client)
        version = create_version(client, base, "Analyst").json()
        changed = client.post(
            f"/fact-bases/{base['id']}/experiences",
            json={"organization": "Side Project", "role": "Builder"},
        )
        refreshed = client.post(
            f"/fact-bases/{base['id']}/versions/refresh-staleness"
        )

    assert changed.json()["revision"] == base["revision"] + 1
    assert refreshed.json()[0]["id"] == version["id"]
    assert refreshed.json()[0]["status"] == "stale"


def test_version_rejects_unknown_experience_reference(tmp_path):
    with TestClient(create_app(tmp_path / "resume-agent.db")) as client:
        base = create_base_with_experience(client)
        response = client.post(
            f"/fact-bases/{base['id']}/versions",
            json={
                "name": "Broken",
                "selected_experience_ids": [base["id"]],
            },
        )

    assert response.status_code == 422
