"""Terminal presentation of already-validated matching results."""

from pathlib import Path

from .contracts import EvaluatedJob, EvaluationState

VERDICT_LABELS = {"match": "明确匹配", "mismatch": "明确不匹配", "unknown": "信息不足"}
CATEGORY_LABELS = {"mandatory": "必备条件", "general": "一般要求", "bonus": "加分项"}
GROUP_TITLES: dict[EvaluationState, str] = {
    "ranked": "推荐排名",
    "unable": "无法评估（未评分；不纳入排名）",
    "eliminated": "学历不符淘汰（未评分；不是企业招聘决定）",
}


def render(cv_path: Path, jobs_path: Path, results: list[EvaluatedJob]) -> None:
    """Group validated results, preserving CSV order for equal model scores."""
    groups: dict[EvaluationState, list[EvaluatedJob]] = {
        state: [] for state in GROUP_TITLES
    }
    for result in results:
        groups[result.state].append(result)
    groups["ranked"].sort(key=lambda item: -(item.match.score or 0))
    print("\n匹配结果 — Match Score（0–100 相对指标，不代表录用概率或招聘决定）")
    for state, title in GROUP_TITLES.items():
        print(f"\n{title}\n{'=' * 72}")
        if not groups[state]:
            print("（无）")
        previous = None
        rank = 0
        for position, result in enumerate(groups[state], 1):
            row, job, match = result.source, result.parsed, result.match
            if match.score != previous:
                rank = position
            previous = match.score
            prefix = f"{rank}. " if state == "ranked" else "- "
            score = f" {match.score:g} / 100" if match.score is not None else ""
            print(
                f"{prefix}{row.fields['岗位名称'] or '未提供岗位名称'} — {row.fields['公司名字'] or '未提供公司名字'} [{jobs_path.name} 第 {row.row} 行]{score}"
            )
            print(f"   判断依据：{match.reason}")
            for req, assessment in zip(job.requirements, match.assessments):
                print(
                    f"   {CATEGORY_LABELS[req.category]} · {VERDICT_LABELS[assessment.verdict]}：{assessment.reason}"
                )
                print(
                    f"     职位证据：{jobs_path.name} 第 {row.row} 行 · 任职资格：{req.quote}"
                )
                for fact in assessment.cv_evidence:
                    print(
                        f"     简历证据：{cv_path.name} 第 {fact.start_line}–{fact.end_line} 行 · {fact.quote}"
                    )
                if assessment.verdict == "unknown":
                    print(
                        "     缺失信息："
                        + req.quote
                        + (
                            "（加分项：不加分、不扣分）"
                            if req.category == "bonus"
                            else ""
                        )
                    )
            if job.status != "ok":
                print(f"   缺失信息：任职资格 {job.status}，无法完整解析")
