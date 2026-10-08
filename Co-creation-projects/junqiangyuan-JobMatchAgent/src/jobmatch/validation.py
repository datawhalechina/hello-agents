"""Check source traceability and enforce scoring/education state contracts."""

import re

from .contracts import (
    CV,
    EvaluatedJob,
    EvaluationState,
    Evidence,
    JobRow,
    Match,
    Matches,
    ParsedJob,
    ParsedJobs,
)

REQUIREMENT_CUES = {
    "mandatory": r"必须|必备|须具备|硬性|required|must",
    "bonus": r"优先|加分|优选|preferred|plus",
}
EDUCATION_LEVELS = (
    "unknown",
    "secondary",
    "associate",
    "bachelor",
    "master",
    "doctorate",
)


def check_evidence(evidence: Evidence, lines: list[str]) -> None:
    """Require an exact full-line quotation within the supplied CV."""
    if not 1 <= evidence.start_line <= evidence.end_line <= len(lines):
        raise ValueError("简历证据行号超出范围")
    if evidence.quote != "\n".join(lines[evidence.start_line - 1 : evidence.end_line]):
        raise ValueError("简历证据必须逐字保留完整原文行及限定条件")


class ParserValidationError(ValueError):
    """Identify which parser must regenerate its output."""

    def __init__(self, agent: str, message: str) -> None:
        super().__init__(message)
        self.agent = agent


def validate_parsers(cv: CV, parsed: ParsedJobs, text: str, rows: list[JobRow]) -> None:
    """Check both parsers and identify the agent responsible for a failure."""
    try:
        validate_cv(cv, text)
    except ValueError as exc:
        raise ParserValidationError("cv_reader", str(exc)) from exc
    try:
        validate_jobs(parsed, rows)
    except ValueError as exc:
        raise ParserValidationError("job_opportunities_parser", str(exc)) from exc


def validate_cv(cv: CV, text: str) -> None:
    """Check CV statuses and exact source citations."""
    lines = text.splitlines()
    for section in cv.sections.all_sections():
        if (section.status == "ok") != bool(section.facts):
            raise ValueError("简历章节状态与事实不一致")
        for fact in section.facts:
            check_evidence(fact, lines)
    if cv.education_level != "unknown" and not cv.sections.education.facts:
        raise ValueError("学历必须有明确简历证据")


def validate_jobs(parsed: ParsedJobs, rows: list[JobRow]) -> None:
    """Check job identities, qualification coverage and source citations."""
    if [job.row for job in parsed.jobs] != [row.row for row in rows]:
        raise ValueError("职位解析必须保留每条 CSV 行身份及顺序")
    for job, row in zip(parsed.jobs, rows):
        if (job.status == "ok") != bool(job.requirements):
            raise ValueError("职位解析状态与要求不一致")
        if len({req.id for req in job.requirements}) != len(job.requirements):
            raise ValueError("职位要求 ID 重复")
        qualification = row.fields["任职资格"]
        for index, quote in enumerate(job.background):
            location = f"CSV 第 {row.row} 行，非评分背景 background[{index}]"
            if not quote:
                raise ValueError(
                    f"{location} 为空；删除空项，background 仅保留任职资格中的城市/薪资原文"
                )
            if quote not in qualification:
                raise ValueError(
                    f"{location} 不是任职资格中的逐字原文；"
                    "请引用该行任职资格的原文，不得改写、补充或引用其他字段"
                )
            if not re.match(
                r"(?:薪资|薪酬|薪水|月薪|年薪|工作地点|工作城市|工作地址|办公地点|salary\b|location\b)",
                quote,
                re.IGNORECASE,
            ):
                raise ValueError(
                    f"{location} 未以明确的城市/薪资标识开头；"
                    "background 仅用于城市/薪资说明，技能、经验、学历等任职要求应归入 requirements；"
                    "无法解析时标为 unparseable，不得通过归入 background 排除评分条件"
                )
        if job.status == "ok":
            covered = [False] * len(qualification)
            quotes = [req.quote for req in job.requirements] + job.background
            for quote in quotes:
                for occurrence in re.finditer(re.escape(quote), qualification):
                    covered[occurrence.start() : occurrence.end()] = [True] * len(quote)
            # AND is implicit because every extracted requirement must be assessed.
            # Recognize connectors in the original text, not concatenated leftovers.
            # OR and numbers must remain covered by the quoted requirements.
            for connector in re.finditer(
                r"以及|和|与|及|\band\b", qualification, re.IGNORECASE
            ):
                covered[connector.start() : connector.end()] = [True] * len(
                    connector.group()
                )
            remainder = "".join(
                char for char, included in zip(qualification, covered) if not included
            )
            if remainder.strip(" \t\r\n；;。.,，、:：•"):
                raise ValueError("职位解析遗漏任职资格原文；必须完整覆盖或标为无法解析")
        for req in job.requirements:
            if req.quote not in qualification:
                raise ValueError("评分条件证据必须来自任职资格")
            if req.category in REQUIREMENT_CUES and not re.search(
                REQUIREMENT_CUES[req.category], req.quote, re.IGNORECASE
            ):
                raise ValueError("必备条件/加分项必须有明确职位措辞")
            if req.minimum_education != "unknown" and re.search(
                REQUIREMENT_CUES["bonus"], req.quote, re.IGNORECASE
            ):
                raise ValueError("学历偏好不是最低学历条件")


def classify(cv: CV, job: ParsedJob, match: Match) -> EvaluationState:
    """Validate assessments and derive the only permitted scoring state."""
    if [a.requirement_id for a in match.assessments] != [
        r.id for r in job.requirements
    ]:
        raise ValueError("评估必须覆盖所有职位要求，保持 ID 和顺序")
    facts = [fact for section in cv.sections.all_sections() for fact in section.facts]
    for assessment in match.assessments:
        if assessment.verdict != "unknown" and not assessment.cv_evidence:
            raise ValueError("明确匹配/不匹配必须有简历证据")
        if any(fact not in facts for fact in assessment.cv_evidence):
            raise ValueError("评估证据必须来自简历结构化事实")
    eliminated = False
    insufficient = job.status != "ok"
    for req, assessment in zip(job.requirements, match.assessments):
        if req.minimum_education != "unknown":
            if req.category == "bonus":
                raise ValueError("学历偏好不能标为最低学历")
            if cv.education_level == "unknown":
                expected = "unknown"
            elif EDUCATION_LEVELS.index(cv.education_level) < EDUCATION_LEVELS.index(
                req.minimum_education
            ):
                expected = "mismatch"
            else:
                expected = "match"
            if assessment.verdict != expected:
                raise ValueError("最低学历评估与明确学历事实不一致")
            if expected != "unknown" and not any(
                fact in cv.sections.education.facts for fact in assessment.cv_evidence
            ):
                raise ValueError("最低学历判断必须引用教育背景证据")
            eliminated |= expected == "mismatch"
        insufficient |= req.category != "bonus" and assessment.verdict == "unknown"
    state: EvaluationState = (
        "eliminated" if eliminated else "unable" if insufficient else "ranked"
    )
    if (state == "ranked") != (match.score is not None):
        raise ValueError("模型分数与评估状态不一致；无法评估/学历淘汰不得评分")
    return state


def validate_matches(
    cv: CV, parsed: ParsedJobs, matches: Matches, rows: list[JobRow]
) -> list[EvaluatedJob]:
    """Pair each source job with one validated evaluation in CSV order."""
    if sorted(match.row for match in matches.jobs) != [row.row for row in rows]:
        raise ValueError("评估必须覆盖每个 CSV 职位且不可重复")
    by_row = {match.row: match for match in matches.jobs}
    return [
        EvaluatedJob(row, job, by_row[row.row], classify(cv, job, by_row[row.row]))
        for row, job in zip(rows, parsed.jobs)
    ]
