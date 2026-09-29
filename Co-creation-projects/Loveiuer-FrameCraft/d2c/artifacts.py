"""Write known text artifacts to a new directory, never over an existing project."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath


def validate_files(files: dict[str, str]) -> None:
    if len(files) > 50:
        raise ValueError("生成文件过多。")
    total = 0
    for name, content in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or not path.parts:
            raise ValueError("生成文件路径不合法。")
        if not isinstance(content, str):
            raise ValueError("只允许生成文本文件。")
        total += len(content.encode("utf-8"))
    if total > 5 * 1024 * 1024:
        raise ValueError("生成内容超过 5 MB，请缩小设计范围。")


def write_result(result: dict, destination: Path) -> Path:
    validate_files(result["files"])
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in result["files"].items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for name, content in {
        "design-model.json": result["design"],
        "design-analysis.json": result.get("analysis", {}),
        "agent-trace.json": result["events"],
        "review-report.json": {"review": result["review"], "metrics": result["metrics"], "mode": result["mode"]},
        "component-plan.json": result["plan"],
    }.items():
        (destination / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
