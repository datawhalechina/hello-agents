"""Fixed cv_reader → job_opportunities_parser → matcher orchestration."""

from pathlib import Path

from .agents import create_llm
from .report import generate_report
from .retry import validate_with_retry
from .services.cv_reader import CVReaderService
from .services.job_parser import JobParserService
from .services.matcher import MatcherService
from .validation import ParserValidationError, validate_matches, validate_parsers


def evaluate(cv_path: Path, jobs_path: Path, report_path: Path) -> None:
    """Run matching agents, then write a report from validated results."""
    text = CVReaderService.read_source(cv_path)
    rows = JobParserService.read_source(jobs_path)
    llm = create_llm()
    cv_reader = CVReaderService(llm)
    job_parser = JobParserService(llm)
    matcher = MatcherService(llm)

    print("解析简历…… cv_reader", flush=True)
    cv = cv_reader.run(str(cv_path), text)
    print(f"解析职位…… job_opportunities_parser（{len(rows)} 条）", flush=True)
    parsed = job_parser.run(str(jobs_path), rows)

    def parser_agent(error: ValueError) -> str:
        if not isinstance(error, ParserValidationError):
            raise error
        return error.agent

    def regenerate_parser(error: ValueError) -> None:
        nonlocal cv, parsed
        name = parser_agent(error)
        if name == "cv_reader":
            cv = cv_reader.run(str(cv_path), text, correction=(cv, error))
        else:
            parsed = job_parser.run(str(jobs_path), rows, correction=(parsed, error))

    validate_with_retry(
        lambda: validate_parsers(cv, parsed, text, rows),
        regenerate_parser,
        parser_agent,
    )
    print("正在评估…… matcher", flush=True)
    matches = matcher.run(cv, parsed, str(jobs_path), rows)

    def regenerate_matches(error: ValueError) -> None:
        nonlocal matches
        matches = matcher.run(
            cv, parsed, str(jobs_path), rows, correction=(matches, error)
        )

    results = validate_with_retry(
        lambda: validate_matches(cv, parsed, matches, rows),
        regenerate_matches,
        "matcher",
    )
    generate_report(cv_path, jobs_path, results, report_path)
    print(f"匹配报告已生成：{report_path}", flush=True)
