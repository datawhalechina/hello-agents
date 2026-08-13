from uuid import UUID

import httpx

from resume_agent.domain.models import CandidateProfile
from resume_agent.ui.client import HttpResumeAgentClient


VERSION_ID = UUID("00000000-0000-0000-0000-000000000321")


def preview_payload():
    return {
        "version_id": str(VERSION_ID),
        "base_revision": 2,
        "version_base_revision": 2,
        "locale": "zh",
        "style": "藏青现代",
        "title": "简历",
        "filename_stem": "数据分析师_zh",
        "candidate_name": "王明",
        "headline": "数据分析师",
        "contact_line": "wang@example.com",
        "summary": "目标岗位：数据分析师。以下内容来自 1 段已确认经历。",
        "experiences": [
            {
                "organization": "云数科技",
                "role": "数据分析师",
                "period": "2023.01 – 2024.01",
                "bullets": ["搭建自动化看板"],
            }
        ],
        "skills": ["SQL"],
        "markdown": "# 王明\n",
        "html": "<!DOCTYPE html><html><body>王明</body></html>",
        "warnings": [],
    }


def client_for(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://resume.test")
    return HttpResumeAgentClient("http://resume.test/", client=http_client)


def test_client_parses_preview_model():
    client = client_for(lambda request: httpx.Response(200, json=preview_payload()))

    result = client.preview_version(VERSION_ID)

    assert result.version_id == VERSION_ID
    assert result.html.startswith("<!DOCTYPE html>")


def test_client_sends_profile_and_style_mutations():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/profile"):
            return httpx.Response(
                200,
                json={
                    "id": "00000000-0000-0000-0000-000000000111",
                    "revision": 1,
                    "profile": {"name": "王明", "email": "wang@example.com"},
                    "target": {},
                    "experiences": [],
                    "confirmed_proposal_ids": [],
                    "created_at": "2026-08-13T00:00:00Z",
                    "updated_at": "2026-08-13T00:00:00Z",
                },
            )
        return httpx.Response(
            200,
            json={
                "id": str(VERSION_ID),
                "fact_base_id": "00000000-0000-0000-0000-000000000111",
                "name": "版本",
                "locale": "zh",
                "styles": {"zh": "经典墨色"},
                "base_revision": 1,
                "created_at": "2026-08-13T00:00:00Z",
                "updated_at": "2026-08-13T00:00:00Z",
            },
        )

    client = client_for(handler)
    client.update_profile(
        "00000000-0000-0000-0000-000000000111",
        CandidateProfile(name="王明", email="wang@example.com"),
    )
    client.set_version_style(VERSION_ID, "经典墨色")

    assert requests[0].method == "PATCH"
    assert requests[0].url.path.endswith("/profile")
    assert requests[1].method == "PUT"
    assert requests[1].content == b'{"style":"\xe7\xbb\x8f\xe5\x85\xb8\xe5\xa2\xa8\xe8\x89\xb2"}'


def test_export_url_is_absolute_and_encoded():
    client = client_for(lambda request: httpx.Response(500))

    assert client.version_export_url(VERSION_ID, "pdf") == (
        f"http://resume.test/versions/{VERSION_ID}/export?format=pdf"
    )
