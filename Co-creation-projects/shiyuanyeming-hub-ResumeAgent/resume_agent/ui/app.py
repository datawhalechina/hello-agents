"""Streamlit product workspace for ResumeAgent."""

from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

import streamlit as st

from resume_agent.agents.runtime import AgentCapabilityStatus
from resume_agent.domain.models import (
    CandidateProfile,
    CareerFactBase,
    CareerTarget,
    QualityDimension,
)
from resume_agent.rendering.styles import STYLE_CATALOG
from resume_agent.ui.client import (
    AgentUnavailable,
    ApiConflict,
    ApiNotFound,
    ApiTransportError,
    ApiValidationError,
    HttpResumeAgentClient,
    InvalidAgentOutput,
    ResumeApiError,
)
from resume_agent.ui.components import (
    DIMENSION_LABELS,
    experience_label,
    render_fact,
    render_quality_strip,
)
from resume_agent.ui.state import Workspace, WorkspaceState
from resume_agent.ui.theme import APP_CSS


WORKSPACE_LABELS = {
    Workspace.MENTOR: "导师对话",
    Workspace.EVIDENCE: "证据档案",
    Workspace.VERSIONS: "投递版本",
    Workspace.PREVIEW: "预览评审",
}
LABEL_TO_WORKSPACE = {label: key for key, label in WORKSPACE_LABELS.items()}


def get_state() -> WorkspaceState:
    if "workspace_state" not in st.session_state:
        st.session_state.workspace_state = WorkspaceState.from_query_params(
            st.query_params
        )
    return st.session_state.workspace_state


def sync_query_params(state: WorkspaceState) -> None:
    st.query_params.from_dict(state.to_query_params())


def show_error(error: Exception) -> None:
    if isinstance(error, AgentUnavailable):
        st.warning("回答已经保存，但事实审计 Agent 尚未配置。请启动带 LLM 的 API 后再分析。")
    elif isinstance(error, InvalidAgentOutput):
        st.error("模型返回内容未通过事实校验。你可以稍后重新分析，原回答不会丢失。")
    elif isinstance(error, ApiConflict):
        st.warning("证据档案已在别处更新，请刷新页面后重新确认。")
    elif isinstance(error, (ApiValidationError, ApiNotFound)):
        st.error(str(error))
    else:
        st.error(f"操作失败：{error}")


def render_header() -> None:
    st.markdown(
        """
        <div class="resume-hero">
          <div class="resume-eyebrow">Evidence-first career mentor</div>
          <h2>把做过的事，讲成有证据的职业故事</h2>
          <div>不用先学会写简历。导师会一次问一个问题，帮你把经历慢慢挖出来。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(
    client,
    state: WorkspaceState,
    bases: list[CareerFactBase],
    capabilities: AgentCapabilityStatus,
) -> None:
    with st.sidebar:
        st.markdown("## ResumeAgent")
        selected_label = st.radio(
            "工作区",
            list(LABEL_TO_WORKSPACE),
            index=list(WORKSPACE_LABELS).index(state.workspace),
            key="workspace_radio",
        )
        state.workspace = LABEL_TO_WORKSPACE[selected_label]

        if bases:
            by_id = {base.id: base for base in bases}
            ids = list(by_id)
            if state.fact_base_id not in by_id:
                state.fact_base_id = ids[-1]
            selected = st.selectbox(
                "当前档案",
                ids,
                index=ids.index(state.fact_base_id),
                format_func=lambda item: by_id[item].target.role or "未命名求职方向",
                key="fact_base_selector",
            )
            if selected != state.fact_base_id:
                state.fact_base_id = selected
                state.active_experience_id = None
                state.selected_version_id = None
            base = by_id[state.fact_base_id]
            st.caption(f"目标：{base.target.role or '待确认'}")
            st.caption(f"事实库修订：{base.revision}")
        else:
            st.caption("尚未创建求职档案")
        st.success("API 已连接")
        if capabilities.mentor:
            st.success("导师 Agent 已启用")
            st.caption(
                f"{capabilities.framework} · {capabilities.model or '已配置模型'}"
            )
        else:
            st.warning("导师 Agent 未启用")
            st.caption(capabilities.reason or "请配置 LLM 运行环境")
    sync_query_params(state)


def render_onboarding(client, state: WorkspaceState) -> None:
    render_header()
    st.subheader("先认识一下你")
    st.write("只填三项就能开始。后面的内容由导师陪你一步步补全。")
    with st.form("onboarding"):
        role = st.text_input("你想找什么岗位？", key="onboard_role")
        country = st.text_input("目标国家或地区（可选）", key="onboard_country")
        organization = st.text_input(
            "先从哪段经历聊起？填写公司、学校或项目名",
            key="onboard_org",
        )
        experience_role = st.text_input(
            "你当时的角色是什么？",
            key="onboard_experience_role",
        )
        submitted = st.form_submit_button(
            "创建档案并开始",
            type="primary",
            key="onboard_submit",
        )
    if submitted:
        if not role.strip() or not organization.strip() or not experience_role.strip():
            st.error("岗位、经历名称和角色需要填写。")
            return
        try:
            base = client.create_fact_base(
                CareerTarget(role=role.strip(), country=country.strip())
            )
            base = client.add_experience(
                base.id,
                organization=organization.strip(),
                role=experience_role.strip(),
            )
        except Exception as error:
            show_error(error)
            return
        state.fact_base_id = base.id
        state.active_experience_id = base.experiences[-1].id
        state.workspace = Workspace.MENTOR
        sync_query_params(state)
        st.rerun()


def active_experience_selector(base: CareerFactBase, state: WorkspaceState):
    if not base.experiences:
        return None
    ids = [experience.id for experience in base.experiences]
    if state.active_experience_id not in ids:
        state.active_experience_id = ids[0]
    selected = st.selectbox(
        "当前深挖经历",
        ids,
        index=ids.index(state.active_experience_id),
        format_func=lambda item: experience_label(base.get_experience(item)),
        key="active_experience_selector",
    )
    state.active_experience_id = selected
    sync_query_params(state)
    return base.get_experience(selected)


def render_add_experience(client, base: CareerFactBase, state: WorkspaceState) -> None:
    with st.expander("＋ 添加一段经历"):
        with st.form("add_experience"):
            organization = st.text_input("公司、学校或项目名", key="add_org")
            role = st.text_input("你的角色", key="add_role")
            submitted = st.form_submit_button("添加经历", type="primary")
        if submitted:
            try:
                updated = client.add_experience(
                    base.id,
                    organization=organization,
                    role=role,
                )
                state.active_experience_id = updated.experiences[-1].id
                sync_query_params(state)
                st.rerun()
            except Exception as error:
                show_error(error)


def resolve_session(client, base_id: UUID, experience_id: UUID, state: WorkspaceState):
    known_id = state.session_ids_by_experience.get(experience_id)
    if known_id:
        try:
            return client.get_session(known_id)
        except ApiNotFound:
            del state.session_ids_by_experience[experience_id]
    sessions = client.list_sessions(base_id, experience_id)
    if sessions:
        state.session_ids_by_experience[experience_id] = sessions[-1].id
        return sessions[-1]
    return None


def render_mentor(
    client,
    base: CareerFactBase,
    state: WorkspaceState,
    capabilities: AgentCapabilityStatus,
) -> None:
    render_header()
    st.subheader("导师对话")
    if not capabilities.fact_audit:
        st.warning(
            "当前导师 Agent 暂时不能提炼你的回答。其他工作区仍可使用；"
            "配置 LLM 后即可继续证据访谈。"
        )
    experience = active_experience_selector(base, state)
    render_add_experience(client, base, state)
    if experience is None:
        st.info("先添加一段工作、项目、研究、校园或志愿经历。")
        return

    session = resolve_session(client, base.id, experience.id, state)
    if session is None:
        st.write("我会围绕这段经历一次问一个问题，你只需要按真实情况回答。")
        if st.button("开始聊这段经历", type="primary", key="start_interview"):
            try:
                session = client.create_session(base.id, experience.id)
                state.session_ids_by_experience[experience.id] = session.id
                client.current_question(session.id)
                st.rerun()
            except Exception as error:
                show_error(error)
        return

    for message in session.messages:
        with st.chat_message("assistant" if message.role == "assistant" else "user"):
            st.write(message.content)

    pending = list(session.pending_proposals.values())
    if pending:
        proposal = pending[-1]
        with st.container(border=True):
            st.markdown("#### 待确认事实")
            st.caption(f"维度：{DIMENSION_LABELS[proposal.dimension]} · 尚未写入证据档案")
            for value in proposal.values:
                render_fact(value)
            if proposal.rationale:
                st.caption(proposal.rationale)
            confirm_col, reject_col = st.columns(2)
            if confirm_col.button("确认写入并继续", type="primary", key=f"confirm_{proposal.id}"):
                try:
                    client.confirm_proposal(session.id, proposal.id)
                    st.rerun()
                except Exception as error:
                    show_error(error)
            if reject_col.button("这不是我的意思", key=f"reject_{proposal.id}"):
                try:
                    client.reject_proposal(session.id, proposal.id)
                    st.rerun()
                except Exception as error:
                    show_error(error)
        return

    question = session.current_question
    if question is None:
        if st.button("获取下一个问题", type="primary", key="next_question"):
            try:
                client.current_question(session.id)
                st.rerun()
            except Exception as error:
                show_error(error)
        return

    st.markdown(f"**现在只想这一件事：** {question.text}")
    answer = st.chat_input("想到什么就说什么，不需要自己组织成简历语言")
    if answer:
        try:
            with st.spinner("导师正在整理你刚才说的事实…"):
                client.answer(session.id, answer)
            st.rerun()
        except Exception as error:
            show_error(error)
    if st.button("暂时想不到", key="unknown_answer"):
        try:
            outcome = client.record_unknown(session.id, question.dimension)
            if outcome.skipped:
                st.toast("先跳过这个方向，我们换一个问题。")
            client.current_question(session.id)
            st.rerun()
        except Exception as error:
            show_error(error)


def render_evidence(client, base: CareerFactBase, state: WorkspaceState) -> None:
    st.subheader("证据档案")
    with st.expander("候选人基本信息", expanded=not bool(base.profile.name)):
        st.caption("姓名和联系方式属于统一事实档案，所有投递版本共用。")
        with st.form("candidate_profile"):
            name = st.text_input(
                "姓名",
                value=base.profile.name,
                key="profile_name",
            )
            email = st.text_input(
                "邮箱",
                value=base.profile.email,
                key="profile_email",
            )
            phone = st.text_input(
                "电话",
                value=base.profile.phone,
                key="profile_phone",
            )
            location = st.text_input(
                "所在地",
                value=base.profile.location,
                key="profile_location",
            )
            links = st.text_area(
                "个人链接（每行一个）",
                value="\n".join(base.profile.links),
                key="profile_links",
            )
            submitted = st.form_submit_button(
                "保存基本信息",
                type="primary",
                key="profile_submit",
            )
        if submitted:
            try:
                client.update_profile(
                    base.id,
                    CandidateProfile(
                        name=name.strip(),
                        email=email.strip(),
                        phone=phone.strip(),
                        location=location.strip(),
                        links=[item.strip() for item in links.splitlines() if item.strip()],
                    ),
                )
                st.rerun()
            except Exception as error:
                show_error(error)
    fact_count = sum(
        len(values)
        for experience in base.experiences
        for values in experience.statements.values()
    )
    left, right = st.columns(2)
    left.metric("已整理经历", len(base.experiences))
    right.metric("已确认事实", fact_count)
    render_add_experience(client, base, state)
    for experience in base.experiences:
        with st.container(border=True):
            st.markdown(f"### {experience_label(experience)}")
            try:
                report = client.get_experience_quality(base.id, experience.id)
                render_quality_strip(report)
                st.caption("达到可写门槛" if report.passes_gate else "继续补充行动与结果证据")
            except Exception as error:
                show_error(error)
            for dimension in QualityDimension:
                values = experience.statements[dimension]
                with st.expander(f"{DIMENSION_LABELS[dimension]} · {len(values)} 条"):
                    if not values:
                        st.caption("还没有确认事实")
                    for value in values:
                        render_fact(value)
            if st.button("继续深挖这段经历", key=f"deepen_{experience.id}"):
                state.active_experience_id = experience.id
                state.workspace = Workspace.MENTOR
                sync_query_params(state)
                st.rerun()


def render_versions(client, base: CareerFactBase, state: WorkspaceState) -> None:
    st.subheader("投递版本")
    st.write("同一份真实证据，可以针对不同岗位选择不同重点。")
    with st.expander("＋ 新建投递版本", expanded=not bool(client.list_versions(base.id))):
        with st.form("create_version"):
            name = st.text_input("版本名称", key="version_name")
            target_role = st.text_input("目标岗位", value=base.target.role, key="version_role")
            company = st.text_input("目标公司", key="version_company")
            locale = st.selectbox("主要语言", ["zh", "ja", "en"], key="version_locale")
            jd = st.text_area("职位描述（JD）", height=180, key="version_jd")
            options = [experience.id for experience in base.experiences]
            selected = st.multiselect(
                "选用经历",
                options,
                default=options,
                format_func=lambda item: experience_label(base.get_experience(item)),
                key="version_experiences",
            )
            submitted = st.form_submit_button("创建版本", type="primary")
        if submitted:
            try:
                version = client.create_version(
                    base.id,
                    name=name,
                    target_role=target_role,
                    company=company,
                    raw_jd=jd,
                    locale=locale,
                    selected_experience_ids=selected,
                )
                state.selected_version_id = version.id
                sync_query_params(state)
                st.rerun()
            except Exception as error:
                show_error(error)

    if st.button("检查证据更新", key="refresh_staleness"):
        try:
            client.refresh_version_staleness(base.id)
            st.rerun()
        except Exception as error:
            show_error(error)

    versions = client.list_versions(base.id)
    if not versions:
        st.info("还没有投递版本。先创建一个目标岗位版本。")
        return
    for version in versions:
        with st.container(border=True):
            badge = " · 当前版本" if version.is_active else ""
            st.markdown(f"### {version.name}{badge}")
            st.caption(
                f"{version.target_role or '未填写岗位'} · {version.company or '未填写公司'} · "
                f"{version.locale} · {version.status.value} · {len(version.selected_experience_ids)} 段经历"
            )
            activate, clone, rename, delete = st.columns(4)
            if activate.button("设为当前", key=f"activate_{version.id}"):
                client.activate_version(version.id)
                state.selected_version_id = version.id
                st.rerun()
            if clone.button("克隆", key=f"clone_{version.id}"):
                client.clone_version(version.id, f"{version.name} 副本")
                st.rerun()
            if rename.button("重命名", key=f"rename_toggle_{version.id}"):
                st.session_state.rename_version_id = str(version.id)
            if delete.button("删除", key=f"delete_toggle_{version.id}"):
                st.session_state.delete_version_id = str(version.id)
            if st.session_state.get("rename_version_id") == str(version.id):
                with st.form(f"rename_form_{version.id}"):
                    new_name = st.text_input("新名称", value=version.name)
                    if st.form_submit_button("保存名称"):
                        client.rename_version(version.id, new_name)
                        del st.session_state.rename_version_id
                        st.rerun()
            if st.session_state.get("delete_version_id") == str(version.id):
                st.warning("仅删除这个投递版本，不会删除证据档案。")
                yes, no = st.columns(2)
                if yes.button("确认删除", key=f"delete_yes_{version.id}"):
                    client.delete_version(version.id)
                    del st.session_state.delete_version_id
                    st.rerun()
                if no.button("取消", key=f"delete_no_{version.id}"):
                    del st.session_state.delete_version_id
                    st.rerun()


def render_preview(client, base: CareerFactBase, state: WorkspaceState) -> None:
    st.subheader("预览评审")
    versions = client.list_versions(base.id)
    if not versions:
        st.info("还没有投递版本。请先到“投递版本”工作区创建一个版本。")
        return

    by_id = {version.id: version for version in versions}
    ids = list(by_id)
    if state.selected_version_id not in by_id:
        state.selected_version_id = ids[0]
    state.selected_version_id = st.selectbox(
        "投递版本",
        ids,
        index=ids.index(state.selected_version_id),
        format_func=lambda item: by_id[item].name,
        key="preview_version",
    )
    version = by_id[state.selected_version_id]
    st.caption(f"{version.target_role} · {version.company or '未填写公司'} · {version.locale}")

    style_names = list(STYLE_CATALOG[version.locale])
    current_style = version.styles.get(version.locale, style_names[0])
    style = st.selectbox(
        "版式风格",
        style_names,
        index=style_names.index(current_style),
        key=f"preview_style_{version.id}",
    )
    if st.button("保存样式", key=f"save_style_{version.id}"):
        try:
            client.set_version_style(version.id, style)
            st.rerun()
        except Exception as error:
            show_error(error)

    try:
        preview = client.preview_version(version.id)
    except Exception as error:
        show_error(error)
        return

    for warning in preview.warnings:
        st.warning(warning.message)
    st.caption(
        f"证据版本 {preview.version_base_revision} · 当前事实库 {preview.base_revision} · "
        f"样式 {preview.style}"
    )
    st.iframe(preview.html, height=960)

    html_col, markdown_col, docx_col, pdf_col = st.columns(4)
    with html_col:
        st.download_button(
            "下载 HTML",
            data=preview.html.encode("utf-8"),
            file_name=f"{preview.filename_stem}.html",
            mime="text/html",
            key=f"download_html_{version.id}",
        )
    with markdown_col:
        st.download_button(
            "下载 Markdown",
            data=preview.markdown.encode("utf-8"),
            file_name=f"{preview.filename_stem}.md",
            mime="text/markdown",
            key=f"download_md_{version.id}",
        )
    with docx_col:
        st.link_button(
            "下载 DOCX",
            client.version_export_url(version.id, "docx"),
            use_container_width=True,
        )
    with pdf_col:
        st.link_button(
            "下载 PDF",
            client.version_export_url(version.id, "pdf"),
            use_container_width=True,
        )
    st.caption("PDF 导出需要 API 所在电脑安装 Google Chrome 或 Microsoft Edge。")


def render_app(client) -> None:
    st.set_page_config(page_title="ResumeAgent", page_icon="🧭", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.title("ResumeAgent")
    state = get_state()

    try:
        connected = client.health()
        if not connected:
            raise ApiTransportError("health check failed", retryable=True)
        bases = client.list_fact_bases()
    except Exception:
        with st.sidebar:
            st.markdown("## ResumeAgent")
            selected_label = st.radio(
                "工作区",
                list(LABEL_TO_WORKSPACE),
                index=list(WORKSPACE_LABELS).index(state.workspace),
                key="workspace_radio_offline",
            )
            state.workspace = LABEL_TO_WORKSPACE[selected_label]
        st.error("无法连接 ResumeAgent API。请先启动后端服务。")
        st.code("uvicorn resume_agent.api.main:app --reload", language="bash")
        st.caption("连接恢复后刷新页面；页面不会自动重复提交任何回答。")
        return

    try:
        capabilities = client.capabilities()
    except Exception:
        if hasattr(client, "capabilities"):
            capabilities = AgentCapabilityStatus.offline(
                "无法读取 Agent 能力状态；请确认 API 与 Web 版本一致"
            )
        else:
            capabilities = AgentCapabilityStatus.ready("injected-test-client")

    render_sidebar(client, state, bases, capabilities)
    if not bases:
        render_onboarding(client, state)
        return
    base = next(item for item in bases if item.id == state.fact_base_id)
    if state.workspace is Workspace.MENTOR:
        render_mentor(client, base, state, capabilities)
    elif state.workspace is Workspace.EVIDENCE:
        render_evidence(client, base, state)
    elif state.workspace is Workspace.VERSIONS:
        render_versions(client, base, state)
    else:
        render_preview(client, base, state)


@st.cache_resource
def get_http_client() -> HttpResumeAgentClient:
    return HttpResumeAgentClient(
        os.environ.get("RESUME_AGENT_API_URL", "http://127.0.0.1:8000"),
        timeout_seconds=float(os.environ.get("RESUME_AGENT_API_TIMEOUT", "30")),
    )


def main() -> None:
    render_app(get_http_client())
