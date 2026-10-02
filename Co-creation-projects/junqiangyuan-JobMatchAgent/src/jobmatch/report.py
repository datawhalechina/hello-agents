"""Generate a self-contained HTML report from validated matching results."""

from collections import defaultdict
from html import escape
from pathlib import Path

from .contracts import EvaluatedJob, EvaluationState

VERDICT_LABELS = {"match": "明确匹配", "mismatch": "明确不匹配", "unknown": "信息不足"}
CATEGORY_LABELS = {"mandatory": "必备条件", "general": "一般要求", "bonus": "加分项"}
GROUP_TITLES: dict[EvaluationState, str] = {
    "ranked": "推荐排名",
    "unable": "无法评估（未评分；不纳入排名）",
    "eliminated": "学历不符淘汰（未评分；不是企业招聘决定）",
}


def _e(value: object) -> str:
    """Escape dynamic values before inserting them into HTML text content."""
    return escape(str(value), quote=True)


def _job_card(result: EvaluatedJob, cv_name: str, jobs_name: str) -> str:
    row, job, match = result.source, result.parsed, result.match
    score = f"{match.score:g} / 100" if match.score is not None else "未评分"
    requirements = []
    for requirement, assessment in zip(job.requirements, match.assessments):
        evidence = "".join(
            f'<li>简历证据：{_e(cv_name)} 第 {fact.start_line}–{fact.end_line} 行 · '
            f'“{_e(fact.quote)}”</li>'
            for fact in assessment.cv_evidence
        )
        missing = (
            f'<p class="missing">缺失信息：{_e(requirement.quote)}'
            f'{"（加分项：不加分、不扣分）" if assessment.verdict == "unknown" and requirement.category == "bonus" else ""}</p>'
            if assessment.verdict == "unknown"
            else ""
        )
        requirements.append(
            '<li class="requirement">'
            f'<span class="tag">{_e(CATEGORY_LABELS[requirement.category])} · '
            f'{_e(VERDICT_LABELS[assessment.verdict])}</span>'
            f'<p>{_e(assessment.reason)}</p>'
            f'<p class="source">职位证据：{_e(jobs_name)} 第 {row.row} 行 · '
            f'任职资格：“{_e(requirement.quote)}”</p>'
            f'<ul>{evidence}</ul>{missing}</li>'
        )
    parse_note = (
        f'<p class="missing">缺失信息：任职资格 {_e(job.status)}，无法完整解析</p>'
        if job.status != "ok"
        else ""
    )
    return (
        '<article class="job">'
        '<header class="job-heading">'
        f'<div><h3>{_e(row.fields.get("岗位名称") or "未提供岗位名称")}</h3>'
        f'<p>{_e(row.fields.get("公司名字") or "未提供公司名字")} · '
        f'{_e(jobs_name)} 第 {row.row} 行</p></div>'
        f'<strong class="score">{_e(score)}</strong></header>'
        f'<p class="reason">{_e(match.reason)}</p>{parse_note}'
        f'<ul class="requirements">{"".join(requirements)}</ul></article>'
    )


def generate_report(
    cv_path: Path,
    jobs_path: Path,
    results: list[EvaluatedJob],
    report_path: Path,
) -> None:
    """Write an offline HTML report, preserving ranking and source evidence."""
    grouped: dict[EvaluationState, list[EvaluatedJob]] = defaultdict(list)
    for result in results:
        grouped[result.state].append(result)
    grouped["ranked"].sort(key=lambda item: -(item.match.score or 0))

    sections = []
    for state, title in GROUP_TITLES.items():
        jobs = grouped[state]
        if not jobs:
            body = '<p class="empty">（无）</p>'
        else:
            cards = []
            previous = object()
            rank = 0
            for position, result in enumerate(jobs, 1):
                if state == "ranked":
                    if result.match.score != previous:
                        rank = position
                    previous = result.match.score
                    prefix = f'<span class="rank">{rank}.</span>'
                else:
                    prefix = ""
                cards.append(prefix + _job_card(result, cv_path.name, jobs_path.name))
            body = "".join(cards)
        sections.append(
            f'<section><h2>{_e(title)}</h2>{body}</section>'
        )

    document = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>简历与职位匹配报告</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #1e293b; background: #f1f5f9; }}
body {{ max-width: 1000px; margin: 0 auto; padding: 36px 22px 64px; line-height: 1.65; }}
h1 {{ margin-bottom: 4px; }}
.subtitle, .source {{ color: #64748b; font-size: .92rem; }}
section {{ margin-top: 36px; }}
h2 {{ padding-bottom: 8px; border-bottom: 2px solid #cbd5e1; }}
.job {{ position: relative; margin: 18px 0; padding: 22px; border: 1px solid #e2e8f0; border-radius: 14px; background: white; box-shadow: 0 4px 14px #0f172a0a; }}
.job-heading {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }}
h3, .job-heading p {{ margin: 0; }}
.job-heading p {{ color: #64748b; }}
.score {{ white-space: nowrap; color: #0369a1; font-size: 1.15rem; }}
.rank {{ position: absolute; left: -12px; top: 16px; padding: 3px 9px; border-radius: 999px; color: white; background: #0369a1; font-weight: 700; }}
.reason {{ padding: 12px 14px; border-left: 3px solid #38bdf8; background: #f0f9ff; }}
.requirements {{ padding-left: 20px; }}
.requirement {{ margin: 16px 0; }}
.tag {{ color: #334155; font-weight: 700; }}
.source {{ margin-bottom: 4px; }}
.missing {{ color: #a16207; }}
.empty {{ color: #94a3b8; }}
footer {{ margin-top: 42px; padding-top: 16px; border-top: 1px solid #cbd5e1; color: #64748b; font-size: .9rem; }}
@media (max-width: 600px) {{ body {{ padding: 22px 14px; }} .job {{ padding: 18px 14px; }} }}
</style>
</head>
<body>
<h1>简历与职位匹配报告</h1>
<p class="subtitle">简历：{_e(cv_path.name)} · 职位数据：{_e(jobs_path.name)}</p>
<p>Match Score（0–100）是相对匹配指标，不代表录用概率或招聘决定。</p>
{"".join(sections)}
<footer>报告基于已校验的模型评估生成；证据引用对应输入文件中的原文。</footer>
</body>
</html>
'''
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(document, encoding="utf-8")
