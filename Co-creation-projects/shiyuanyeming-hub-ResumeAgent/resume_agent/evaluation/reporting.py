"""Atomic JSON and Markdown output for privacy-safe benchmark reports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

from resume_agent.evaluation.models import BenchmarkReport


@dataclass(frozen=True)
class ReportFiles:
    json_path: Path
    markdown_path: Path


def write_report(report: BenchmarkReport, output_dir: str | Path) -> ReportFiles:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"mentor-evaluation-{timestamp}"
    json_path = directory / f"{stem}.json"
    markdown_path = directory / f"{stem}.md"

    json_text = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    _atomic_write(json_path, json_text)
    _atomic_write(markdown_path, _markdown_report(report))
    return ReportFiles(json_path=json_path, markdown_path=markdown_path)


def _atomic_write(path: Path, content: str) -> None:
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = handle.name
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _markdown_report(report: BenchmarkReport) -> str:
    lines = [
        "# Mentor Evaluation Report",
        "",
        f"- Dataset: `{report.dataset_version}`",
        f"- Repeats: {report.repeats}",
        f"- Total runs: {report.total_runs}",
    ]
    for key in ("framework", "model"):
        if key in report.metadata:
            lines.append(f"- {key.title()}: `{report.metadata[key]}`")

    lines.extend(["", "## Metrics", ""])
    for name, value in report.metrics.items():
        lines.append(f"- `{name}`: {value:.2%}")

    lines.extend(["", "## Failed Cases", ""])
    if not report.failed_scores:
        lines.append("All deterministic checks passed.")
    else:
        for score in report.failed_scores:
            failed_checks = [name for name, passed in score.checks.items() if not passed]
            details = ", ".join(f"`{name}`" for name in failed_checks)
            if score.error_category:
                details += f"; error: `{score.error_category}`"
            lines.append(f"- `{score.case_id}`: {details}")
    return "\n".join(lines) + "\n"
