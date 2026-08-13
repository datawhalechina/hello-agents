"""Command-line entry point for the configured mentor quality benchmark."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from resume_agent.agents.runtime import build_mentor_runtime
from resume_agent.evaluation.dataset import DatasetError, load_dataset
from resume_agent.evaluation.reporting import write_report
from resume_agent.evaluation.runner import MentorBenchmark


DEFAULT_OUTPUT_DIR = Path("evaluation/reports")


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _unit_interval(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-agent-eval",
        description="Evaluate mentor questions and evidence extraction against safe fixtures.",
    )
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--repeats", type=_positive_integer, default=1)
    parser.add_argument("--fail-under", type=_unit_interval, default=0.9)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def _load_environment() -> dict[str, str]:
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(dotenv_path=Path(".env"), override=False)
    return dict(os.environ)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    values = dict(environ) if environ is not None else _load_environment()
    runtime = build_mentor_runtime(values)
    if (
        runtime.capabilities.status != "ready"
        or runtime.question_writer is None
        or runtime.fact_auditor is None
    ):
        print(
            f"mentor runtime unavailable: {runtime.capabilities.reason}",
            file=sys.stderr,
        )
        return 2

    try:
        dataset = load_dataset(args.dataset)
        report = MentorBenchmark(
            runtime.question_writer,
            runtime.fact_auditor,
        ).run(
            dataset,
            repeats=args.repeats,
            metadata={
                "framework": runtime.capabilities.framework,
                "model": runtime.capabilities.model,
            },
        )
        files = write_report(report, args.output_dir)
    except (DatasetError, OSError, ValueError) as error:
        print(f"evaluation error: {error}", file=sys.stderr)
        return 2

    print(f"JSON report: {files.json_path}")
    print(f"Markdown report: {files.markdown_path}")
    print(f"strict_pass_rate={report.strict_pass_rate:.2%}")
    if report.strict_pass_rate < args.fail_under:
        print(
            f"strict pass rate {report.strict_pass_rate:.2%} "
            f"is below required {args.fail_under:.2%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
