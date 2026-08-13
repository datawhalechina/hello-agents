from uuid import uuid4

import pytest

from resume_agent.domain.models import (
    CandidateProfile,
    CareerFactBase,
    ConfidenceStatus,
    FactValue,
    QualityDimension,
    ResumeVersion,
)
from resume_agent.rendering.renderer import ResumeRenderer


def evidence_fixture():
    base = CareerFactBase(
        profile=CandidateProfile(
            name="王明",
            email="wang@example.com",
            phone="138-0000-0000",
            location="东京",
        )
    )
    first = base.add_experience("第一家公司", "数据分析师")
    first.start = "2023-01"
    first.end = "2024-03"
    first.linked_skills = ["SQL", "Python"]
    first.statements[QualityDimension.ACTION] = [
        FactValue(text="搭建用户留存看板", confidence=ConfidenceStatus.CONFIRMED),
        FactValue(text="未确认内容", confidence=ConfidenceStatus.UNVERIFIED),
    ]
    first.statements[QualityDimension.RESULT] = [
        FactValue(text="将周报耗时从四小时降到三十分钟", confidence=ConfidenceStatus.ESTIMATED)
    ]
    second = base.add_experience("第二家公司", "产品分析师")
    second.statements[QualityDimension.METHOD] = [
        FactValue(text="使用漏斗分析定位流失环节", confidence=ConfidenceStatus.CONFIRMED)
    ]
    base.revision = 3
    return base, first, second


def make_version(base, experiences, *, locale="zh", style=None, base_revision=None):
    styles = {locale: style} if style else {}
    ids = [experience.id for experience in experiences]
    return ResumeVersion(
        fact_base_id=base.id,
        name="目标岗位版本",
        target_role="高级数据分析师",
        company="目标公司",
        locale=locale,
        selected_experience_ids=ids,
        ordering=ids,
        styles=styles,
        base_revision=base.revision if base_revision is None else base_revision,
    )


def test_renderer_uses_selected_order_and_excludes_unverified():
    base, first, second = evidence_fixture()
    version = make_version(base, [first, second])
    version.ordering = [second.id, first.id]

    result = ResumeRenderer().render(base, version)

    assert [item.organization for item in result.experiences] == [
        "第二家公司",
        "第一家公司",
    ]
    assert "未确认内容" not in result.markdown
    assert "将周报耗时从四小时降到三十分钟" in result.markdown


def test_renderer_only_includes_selected_experiences():
    base, first, second = evidence_fixture()
    version = make_version(base, [second])

    result = ResumeRenderer().render(base, version)

    assert [item.organization for item in result.experiences] == ["第二家公司"]
    assert "第一家公司" not in result.html


def test_renderer_escapes_profile_and_fact_html():
    base, first, _ = evidence_fixture()
    base.profile.name = "<script>alert(1)</script>"
    first.statements[QualityDimension.ACTION][0].text = '<img src=x onerror="alert(2)">'
    version = make_version(base, [first])

    result = ResumeRenderer().render(base, version)

    assert "<script>" not in result.html
    assert "<img src=x" not in result.html
    assert "&lt;script&gt;" in result.html
    assert "&lt;img src=x" in result.html


@pytest.mark.parametrize(
    ("locale", "heading", "title"),
    [
        ("zh", "工作经历", "简历"),
        ("en", "Experience", "Resume"),
        ("ja", "職務経歴", "職務経歴書"),
    ],
)
def test_renderer_localizes_headings_without_translating_facts(locale, heading, title):
    base, first, _ = evidence_fixture()
    version = make_version(base, [first], locale=locale)

    result = ResumeRenderer().render(base, version)

    assert result.title == title
    assert heading in result.html
    assert "搭建用户留存看板" in result.html


def test_renderer_warns_about_estimates_staleness_and_missing_profile():
    base, first, _ = evidence_fixture()
    base.profile = CandidateProfile()
    version = make_version(base, [first], base_revision=base.revision - 1)

    result = ResumeRenderer().render(base, version)

    assert {warning.code for warning in result.warnings} >= {
        "missing_profile",
        "estimated_evidence",
        "stale_version",
    }


def test_renderer_collects_skills_once_and_is_deterministic():
    base, first, second = evidence_fixture()
    second.linked_skills = ["SQL", "Tableau"]
    version = make_version(base, [first, second])
    renderer = ResumeRenderer()

    first_result = renderer.render(base, version)
    second_result = renderer.render(base, version)

    assert first_result.skills == ["SQL", "Python", "Tableau"]
    assert first_result == second_result


def test_renderer_rejects_invalid_locale_style_and_selected_reference():
    base, first, _ = evidence_fixture()
    invalid_locale = make_version(base, [first])
    invalid_locale.locale = "fr"
    invalid_style = make_version(base, [first], style="不存在")
    invalid_reference = make_version(base, [first])
    invalid_reference.selected_experience_ids = [uuid4()]
    renderer = ResumeRenderer()

    with pytest.raises(ValueError, match="unsupported locale"):
        renderer.render(base, invalid_locale)
    with pytest.raises(ValueError, match="unsupported style"):
        renderer.render(base, invalid_style)
    with pytest.raises(ValueError, match="unknown experience"):
        renderer.render(base, invalid_reference)
