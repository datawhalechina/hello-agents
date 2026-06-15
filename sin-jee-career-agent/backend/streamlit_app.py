"""智能求职助手 — Web 界面"""

import streamlit as st
import sys
import os

# 确保能导入 backend 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import CareerRequest
from app.agents.career_planner_agent import get_career_planner

st.set_page_config(
    page_title="智能求职助手",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 样式 ----
st.markdown("""
<style>
.main-title { font-size: 2.5rem; font-weight: 800; color: #1a73e8; margin-bottom: 0; }
.subtitle { font-size: 1rem; color: #5f6368; margin-top: 0; }
.section-title { font-size: 1.3rem; font-weight: 600; color: #202124; border-bottom: 2px solid #1a73e8; padding-bottom: 0.3rem; margin-top: 2rem; }
.job-card { background: #f8f9fa; border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0; border-left: 4px solid #1a73e8; }
.company-card { background: #fff; border-radius: 10px; padding: 1rem; margin: 0.5rem 0; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.salary-badge { background: #e8f5e9; color: #2e7d32; padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
.budget-row { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #f1f3f4; }
.task-item { padding: 0.3rem 0 0.3rem 1rem; border-left: 2px solid #1a73e8; margin: 0.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ---- 标题 ----
st.markdown('<p class="main-title">智能求职助手</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">多 Agent 协作，为你生成专属求职策略报告</p>', unsafe_allow_html=True)
st.markdown("---")

# ---- 侧边栏表单 ----
with st.sidebar:
    st.markdown("## 填写求职需求")

    target_role = st.text_input("目标职位", placeholder="例如：后端开发工程师")
    city = st.text_input("目标城市", placeholder="例如：北京")
    start_date = st.date_input("开始日期")
    target_days = st.slider("求职周期（天）", 1, 90, 7)

    st.markdown("---")

    salary_expectation = st.selectbox("薪资期望", ["面议", "10k-15k", "15k-25k", "25k-35k", "35k-50k", "50k以上"])
    experience_level = st.selectbox("经验级别", ["应届生", "1-3年", "3-5年", "5-10年", "10年以上"])
    industry = st.selectbox("目标行业", ["互联网", "金融科技", "人工智能", "电商", "游戏", "教育", "医疗", "其他"])

    st.markdown("---")

    preferences = st.multiselect(
        "偏好标签",
        ["大厂", "创业公司", "技术氛围好", "工作生活平衡", "高薪", "期权/股权", "远程办公", "弹性工作"],
        default=["大厂", "技术氛围好"]
    )
    free_text = st.text_area("额外要求", placeholder="例如：希望找Go或Python方向，不接受996")

    submit = st.button("生成求职计划", type="primary", use_container_width=True)

# ---- 主页内容 ----
if not submit:
    st.info("在左侧填写你的求职需求，然后点击「生成求职计划」按钮开始分析。")
    st.markdown("""
    ### 工作流程

    1. **[JOB] 职位搜索 Agent** — 根据你的偏好在目标城市搜索匹配职位
    2. **[COMP] 公司研究 Agent** — 深入分析目标公司的背景、文化和发展前景
    3. **[SAL] 薪资研究 Agent** — 查询行业薪资水平，提供谈判参考
    4. **[PLAN] 求职规划 Agent** — 整合全部信息，生成完整的求职策略报告

    你将得到一份包含**职位推荐、公司分析、薪资数据、每日任务和面试准备清单**的完整报告。
    """)
else:
    if not target_role or not city:
        st.error("请至少填写目标职位和目标城市。")
    else:
        try:
            # 准备请求数据
            request = CareerRequest(
                target_role=target_role,
                city=city,
                start_date=start_date.strftime("%Y-%m-%d"),
                target_days=target_days,
                salary_expectation=salary_expectation,
                experience_level=experience_level,
                industry=industry,
                preferences=preferences,
                free_text_input=free_text,
            )

            # 调用 Agent
            with st.spinner("Agent 团队正在协作中，预计需要 30-60 秒..."):
                progress_container = st.empty()
                progress_container.markdown("**[JOB] 职位搜索 Agent** 正在搜索匹配职位...")
                agent = get_career_planner()
                plan = agent.plan_career(request)
                progress_container.empty()

            st.success(f"求职计划生成完成！共找到 {len(plan.jobs)} 个匹配职位。")

            # ---- 总体策略 ----
            st.markdown('<p class="section-title">总体策略</p>', unsafe_allow_html=True)
            st.markdown(plan.overall_strategy.replace("\n", "<br>"), unsafe_allow_html=True)

            # ---- 推荐职位 ----
            if plan.jobs:
                st.markdown('<p class="section-title">推荐职位</p>', unsafe_allow_html=True)
                cols = st.columns(min(len(plan.jobs), 2))
                for i, job in enumerate(plan.jobs):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div class="job-card">
                            <h4>{job.title}</h4>
                            <strong>{job.company}</strong> &middot; {job.location}<br>
                            <span class="salary-badge">{job.salary_range or '薪资面议'}</span>
                            <span style="margin-left: 0.5rem; color: #5f6368;">{job.source or ''}</span>
                            <p style="margin-top: 0.6rem; color: #3c4043;">{job.description}</p>
                            <p><strong>要求：</strong></p>
                            <ul>
                                {"".join(f"<li>{r}</li>" for r in job.requirements)}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)

            # ---- 公司分析 ----
            if plan.companies:
                st.markdown('<p class="section-title">目标公司分析</p>', unsafe_allow_html=True)
                for comp in plan.companies:
                    with st.expander(f"{comp.name} — {comp.industry or ''} | 评分 {comp.rating or 'N/A'}/5"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"**规模：** {comp.size or '未知'}")
                            st.markdown(f"**总部：** {comp.headquarters or '未知'}")
                            st.markdown(f"**融资：** {comp.funding_stage or '未知'}")
                            st.markdown(f"**简介：** {comp.description or ''}")
                            st.markdown(f"**文化：** {comp.culture or ''}")
                        with col_b:
                            if comp.pros:
                                st.markdown("**优势：**")
                                for p in comp.pros:
                                    st.markdown(f"- {p}")
                            if comp.cons:
                                st.markdown("**风险：**")
                                for c in comp.cons:
                                    st.markdown(f"- {c}")

            # ---- 薪资数据 ----
            if plan.salary_info:
                st.markdown('<p class="section-title">薪资行情</p>', unsafe_allow_html=True)
                for s in plan.salary_info:
                    low = f"{s.salary_range_low / 1000:.0f}k" if s.salary_range_low else "?"
                    high = f"{s.salary_range_high / 1000:.0f}k" if s.salary_range_high else "?"
                    st.markdown(f"""
                    | 职位 | 城市 | 经验 | 范围 | 平均 | 来源 |
                    |------|------|------|------|------|------|
                    | {s.role} | {s.city} | {s.experience_level or '-'} | {low}-{high} | {s.avg_salary or '-'} | {s.source or '综合'} |
                    """)

            # ---- 每日任务 ----
            if plan.daily_tasks:
                st.markdown('<p class="section-title">每日求职任务</p>', unsafe_allow_html=True)
                tabs = st.tabs([f"第{t.day_index + 1}天" for t in plan.daily_tasks])
                for tab, task in zip(tabs, plan.daily_tasks):
                    with tab:
                        st.markdown(f"**{task.date}** — {task.description}")
                        if task.preparation_tips:
                            st.info(task.preparation_tips)
                        st.markdown("**任务清单：**")
                        for item in task.tasks:
                            st.markdown(f'<div class="task-item">{item}</div>', unsafe_allow_html=True)
                        if task.target_companies:
                            st.markdown(f"**目标公司：** {'、'.join(task.target_companies)}")
                        if task.target_jobs:
                            st.markdown(f"**目标职位：** {'、'.join(task.target_jobs)}")

            # ---- 简历建议&面试准备 ----
            if plan.resume_tips:
                st.markdown('<p class="section-title">简历优化建议</p>', unsafe_allow_html=True)
                st.markdown(plan.resume_tips.replace("\n", "<br>"), unsafe_allow_html=True)

            if plan.interview_prep:
                st.markdown('<p class="section-title">面试准备清单</p>', unsafe_allow_html=True)
                st.markdown(plan.interview_prep.replace("\n", "<br>"), unsafe_allow_html=True)

            # ---- 预算 ----
            if plan.budget:
                st.markdown('<p class="section-title">求职预算估算</p>', unsafe_allow_html=True)
                b = plan.budget
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:12px; padding:1rem; max-width:400px;">
                    <div class="budget-row"><span>交通费用</span><strong>{b.transportation} 元</strong></div>
                    <div class="budget-row"><span>打印/材料</span><strong>{b.printing} 元</strong></div>
                    <div class="budget-row"><span>培训/课程</span><strong>{b.training} 元</strong></div>
                    <div class="budget-row"><span>其他</span><strong>{b.others} 元</strong></div>
                    <div class="budget-row" style="border-bottom:none; font-size:1.1rem; margin-top:0.3rem;">
                        <span>总计</span><strong style="color:#1a73e8;">{b.total} 元</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"生成失败：{str(e)}")
            st.markdown("请检查 .env 文件中的 LLM_API_KEY 是否配置正确。")

st.markdown("---")
st.caption("智能求职助手 — 基于多 Agent 协作架构")
