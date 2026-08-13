from uuid import uuid4

from streamlit.testing.v1 import AppTest

from resume_agent.domain.models import CareerFactBase, CareerTarget


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


def test_preview_workspace_is_honest_empty_state():
    base = CareerFactBase(target=CareerTarget(role="Data Analyst"))
    test = AppTest.from_function(
        run_app,
        args=(OnlineDemoClient([base]),),
    ).run()
    test.sidebar.radio[0].set_value("预览评审").run()

    assert not test.exception
    assert any("渲染服务尚未接入" in item.value for item in test.info)


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
