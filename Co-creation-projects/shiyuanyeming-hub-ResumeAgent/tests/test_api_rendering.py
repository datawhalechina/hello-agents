from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from resume_agent.api.app import create_app
from resume_agent.rendering.exporters import PdfExporter, ResumeExporter
from tests.fakes import StubAuditAgent


def create_populated_version(client: TestClient) -> dict:
    base = client.post("/fact-bases", json={}).json()
    base = client.patch(
        f"/fact-bases/{base['id']}/profile",
        json={
            "name": "王明",
            "email": "wang@example.com",
            "phone": "138-0000-0000",
        },
    ).json()
    base = client.post(
        f"/fact-bases/{base['id']}/experiences",
        json={"organization": "云数科技", "role": "数据分析师"},
    ).json()
    experience_id = base["experiences"][0]["id"]
    session = client.post(
        "/sessions",
        json={"fact_base_id": base["id"], "active_experience_id": experience_id},
    ).json()
    turn = client.post(
        f"/sessions/{session['id']}/answers",
        json={"message": "搭建自动化看板，将周报耗时降到三十分钟"},
    ).json()
    client.post(
        f"/sessions/{session['id']}/proposals/{turn['proposal']['id']}/confirm"
    )
    version = client.post(
        f"/fact-bases/{base['id']}/versions",
        json={
            "name": "数据分析师版本",
            "target_role": "高级数据分析师",
            "locale": "zh",
            "selected_experience_ids": [experience_id],
        },
    ).json()
    return version


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(tmp_path / "resume.db", fact_audit_agent=StubAuditAgent())
    ) as test_client:
        yield test_client


def test_preview_is_read_only_and_contains_self_contained_html(client):
    version = create_populated_version(client)
    before = client.get(f"/versions/{version['id']}").json()

    response = client.get(f"/versions/{version['id']}/preview")
    after = client.get(f"/versions/{version['id']}").json()

    assert response.status_code == 200
    assert response.json()["html"].startswith("<!DOCTYPE html>")
    assert "搭建自动化看板" in response.json()["html"]
    assert before == after


@pytest.mark.parametrize(
    ("format_name", "media_type"),
    [
        ("html", "text/html"),
        ("md", "text/markdown"),
        (
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_export_content_types(client, format_name, media_type):
    version = create_populated_version(client)

    response = client.get(
        f"/versions/{version['id']}/export", params={"format": format_name}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert "attachment" in response.headers["content-disposition"]
    if format_name == "docx":
        with ZipFile(BytesIO(response.content)) as archive:
            assert "word/document.xml" in archive.namelist()


def test_rendering_reports_not_found_and_invalid_format(client):
    missing = client.get("/versions/00000000-0000-0000-0000-000000000000/preview")
    invalid = client.get(
        "/versions/00000000-0000-0000-0000-000000000000/export",
        params={"format": "pages"},
    )

    assert missing.status_code == 404
    assert invalid.status_code == 422


def test_pdf_engine_failure_maps_to_503(tmp_path):
    app = create_app(
        tmp_path / "resume.db",
        fact_audit_agent=StubAuditAgent(),
        resume_exporter=ResumeExporter(
            pdf_exporter=PdfExporter(browser_candidates=[])
        ),
    )
    with TestClient(app) as client:
        version = create_populated_version(client)
        response = client.get(
            f"/versions/{version['id']}/export", params={"format": "pdf"}
        )

    assert response.status_code == 503
    assert "browser" in response.json()["detail"]


def test_manual_draft_is_persisted_and_used_for_preview(client):
    version = create_populated_version(client)

    response = client.put(
        f"/versions/{version['id']}/draft",
        json={"markdown": "# 手工稿", "html": "<main>手工稿</main>"},
    )
    preview = client.get(f"/versions/{version['id']}/preview").json()

    assert response.status_code == 200
    assert response.json()["manual_markdown"] == "# 手工稿"
    assert preview["markdown"] == "# 手工稿"
    assert preview["html"] == "<main>手工稿</main>"


def test_empty_manual_draft_restores_generated_preview(client):
    version = create_populated_version(client)
    generated = client.get(f"/versions/{version['id']}/preview").json()
    client.put(
        f"/versions/{version['id']}/draft",
        json={"markdown": "# 手工稿", "html": "<main>手工稿</main>"},
    )

    reset = client.put(
        f"/versions/{version['id']}/draft",
        json={"markdown": "", "html": ""},
    )
    restored = client.get(f"/versions/{version['id']}/preview").json()

    assert reset.status_code == 200
    assert restored["markdown"] == generated["markdown"]
    assert restored["html"] == generated["html"]


def test_manual_draft_rejects_oversized_fields(client):
    version = create_populated_version(client)

    response = client.put(
        f"/versions/{version['id']}/draft",
        json={"markdown": "x" * 500_001, "html": ""},
    )

    assert response.status_code == 422
