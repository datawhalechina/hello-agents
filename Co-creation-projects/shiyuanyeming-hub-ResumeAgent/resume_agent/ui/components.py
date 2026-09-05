"""Reusable Streamlit presentation helpers."""

import streamlit as st

from resume_agent.domain.models import Experience, FactValue, QualityDimension
from resume_agent.domain.quality import QualityReport


DIMENSION_LABELS = {
    QualityDimension.CONTEXT: "背景",
    QualityDimension.RESPONSIBILITY: "我的职责",
    QualityDimension.ACTION: "具体行动",
    QualityDimension.METHOD: "方法与工具",
    QualityDimension.RESULT: "结果",
    QualityDimension.EVIDENCE: "证明与数据",
}

STATUS_LABELS = {0: "还没整理", 1: "已有描述", 2: "足够具体"}


def render_quality_strip(report: QualityReport) -> None:
    columns = st.columns(6)
    for column, dimension in zip(columns, QualityDimension):
        score = report.scores[dimension]
        with column:
            st.caption(DIMENSION_LABELS[dimension])
            st.markdown(f"**{STATUS_LABELS[score]}**")


def fact_badges(value: FactValue) -> str:
    badges = [value.confidence.value, value.specificity.value]
    if value.sensitive:
        badges.append("敏感")
    return " · ".join(badges)


def render_fact(value: FactValue) -> None:
    if value.sensitive:
        with st.expander("敏感事实（点击查看）", expanded=False):
            st.write(value.text)
            st.caption(fact_badges(value))
    else:
        st.write(f"• {value.text}")
        st.caption(fact_badges(value))


def experience_label(experience: Experience) -> str:
    return f"{experience.organization} · {experience.role}"
