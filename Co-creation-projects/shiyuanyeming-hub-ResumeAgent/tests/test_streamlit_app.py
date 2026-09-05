from uuid import uuid4

from streamlit.testing.v1 import AppTest

from resume_agent.domain.models import (
    CandidateProfile,
    CareerFactBase,
    CareerTarget,
    ResumeVersion,
)
from resume_agent.agents.runtime import AgentCapabilityStatus
from resume_agent.rendering.models import RenderedResume, RenderWarning


class OnlineDemoClient:
    def __init__(self, bases=None):
        self.bases = list(bases or [])

    def health(self):
        return True

    def list_fact_bases(self):
        return self.bases

    def create_fact_base(self, target=None):
        base = CareerFactBase(target=target or CareerTarget())
        self.bases.append(base)
        return base

    def add_experience(self, fact_base_id, *, organization, role):
        base = next(item for item in self.bases if item.id == fact_base_id)
        base.add_experience(organization, role)
        base.revision += 1
        return base

    def list_sessions(self, fact_base_id, experience_id=None):
        return []

    def list_versions(self, fact_base_id):
        return []

    def get_experience_quality(self, fact_base_id, experience_id):
        raise AssertionError("no experience in this fixture")


class OfflineClient:
    def health(self):
        raise RuntimeError("connection refused")


def run_app(client):
    from resume_agent.ui.app import render_app

    render_app(client)


def test_app_shows_title_four_workspaces_and_onboarding():
    test = AppTest.from_function(run_app, args=(OnlineDemoClient(),)).run()

    assert not test.exception
    assert test.title[0].value == "ResumeAgent"
    assert test.sidebar.radio[0].options == [
        "导师对话",
        "证据档案",
        "投递版本",
        "预览评审",
    ]
    assert any("先认识一下你" in item.value for item in test.subheader)
    assert any(button.label == "创建档案并开始" for button in test.button)


def test_app_shows_actionable_offline_state():
    test = AppTest.from_function(run_app, args=(OfflineClient(),)).run()

    assert not test.exception
    assert any("无法连接" in item.value for item in test.error)
    assert any("uvicorn" in item.value for item in test.code)


def test_preview_workspace_asks_for_a_version_when_none_exists():
    base = CareerFactBase(target=CareerTarget(role="Data Analyst"))
    test = AppTest.from_function(
        run_app,
        args=(OnlineDemoClient([base]),),
    ).run()
    test.sidebar.radio[0].set_value("预览评审").run()

    assert not test.exception
    assert any("投递版本" in item.value for item in test.info)


def test_onboarding_creates_fact_base_and_first_experience():
    client = OnlineDemoClient()
    test = AppTest.from_function(run_app, args=(client,)).run()
    test.text_input(key="onboard_role").set_value("产品经理")
    test.text_input(key="onboard_org").set_value("校园项目")
    test.text_input(key="onboard_experience_role").set_value("项目负责人")
    test.button(key="onboard_submit").click().run()

    assert not test.exception
    assert len(client.bases) == 1
    assert client.bases[0].experiences[0].role == "项目负责人"


class PreviewDemoClient(OnlineDemoClient):
    def __init__(self):
        base = CareerFactBase(
            profile=CandidateProfile(
                name="王明",
                email="wang@example.com",
                phone="138-0000-0000",
            ),
            target=CareerTarget(role="数据分析师"),
        )
        experience = base.add_experience("云数科技", "数据分析师")
        base.revision = 2
        super().__init__([base])
        self.version = ResumeVersion(
            fact_base_id=base.id,
            name="目标公司版本",
            target_role="高级数据分析师",
            locale="zh",
            selected_experience_ids=[experience.id],
            ordering=[experience.id],
            base_revision=1,
        )
        self.saved_styles = []

    def list_versions(self, fact_base_id):
        return [self.version]

    def preview_version(self, version_id):
        return RenderedResume(
            version_id=self.version.id,
            base_revision=2,
            version_base_revision=1,
            locale="zh",
            style=self.version.styles.get("zh", "藏青现代"),
            title="简历",
            filename_stem="目标公司版本_zh",
            candidate_name="王明",
            headline="高级数据分析师",
            contact_line="wang@example.com",
            summary="以下内容来自一段已确认经历。",
            experiences=[],
            skills=[],
            markdown="# 王明\n",
            html="<!DOCTYPE html><html><body>王明</body></html>",
            warnings=[RenderWarning(code="stale_version", message="证据档案已有更新")],
        )

    def version_export_url(self, version_id, format_name):
        return f"http://resume.test/versions/{version_id}/export?format={format_name}"

    def set_version_style(self, version_id, style):
        self.version.styles["zh"] = style
        self.saved_styles.append(style)
        return self.version


def test_preview_workspace_shows_live_resume_and_downloads():
    test = AppTest.from_function(run_app, args=(PreviewDemoClient(),)).run()
    test.sidebar.radio[0].set_value("预览评审").run()

    assert not test.exception
    assert not any("渲染服务尚未接入" in item.value for item in test.info)
    assert any("证据档案已有更新" in item.value for item in test.warning)
    assert any(
        button.label == "下载 HTML" for button in test.get("download_button")
    )
    assert any(
        button.label == "下载 Markdown" for button in test.get("download_button")
    )


class ProfileDemoClient(OnlineDemoClient):
    def __init__(self):
        super().__init__([CareerFactBase(target=CareerTarget(role="产品经理"))])
        self.updated_profiles = []

    def update_profile(self, fact_base_id, profile):
        self.bases[0].profile = profile
        self.bases[0].revision += 1
        self.updated_profiles.append(profile)
        return self.bases[0]


def test_evidence_workspace_saves_candidate_profile_explicitly():
    client = ProfileDemoClient()
    test = AppTest.from_function(run_app, args=(client,)).run()
    test.sidebar.radio[0].set_value("证据档案").run()
    test.text_input(key="profile_name").set_value("王明")
    test.text_input(key="profile_email").set_value("wang@example.com")
    test.button(key="profile_submit").click().run()

    assert not test.exception
    assert client.updated_profiles[0].name == "王明"


class CapabilityDemoClient(OnlineDemoClient):
    def __init__(self, capabilities):
        super().__init__([CareerFactBase(target=CareerTarget(role="产品经理"))])
        self.agent_capabilities = capabilities

    def capabilities(self):
        return self.agent_capabilities


def test_sidebar_shows_ready_mentor_model():
    client = CapabilityDemoClient(AgentCapabilityStatus.ready("deepseek-chat"))

    test = AppTest.from_function(run_app, args=(client,)).run()

    assert not test.exception
    assert any("导师 Agent 已启用" in item.value for item in test.sidebar.success)
    assert any("deepseek-chat" in item.value for item in test.sidebar.caption)


def test_mentor_warns_before_answer_when_agent_is_degraded():
    client = CapabilityDemoClient(
        AgentCapabilityStatus.offline("LLM_API_KEY is required")
    )

    test = AppTest.from_function(run_app, args=(client,)).run()

    assert not test.exception
    assert any("导师 Agent 未启用" in item.value for item in test.sidebar.warning)
    assert any("暂时不能提炼" in item.value for item in test.warning)
    assert not any("无法连接 ResumeAgent API" in item.value for item in test.error)
