"""Report extraction, telemetry parsing, and persistence helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote


_TELEMETRY_PATTERN = re.compile(r"\s*<telemetry>\s*(\{[\s\S]*?\})\s*</telemetry>\s*$", re.IGNORECASE)
_MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_URL_SCHEMES = ("http://", "https://", "data:", "file://")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ReportTelemetry:
    methods: tuple[str, ...] = ()
    domain: str = "unknown"
    tools_used: tuple[str, ...] = ()
    search_used: bool = False
    search_notes: str = "unknown"
    cleaned_data_saved: bool = False
    cleaned_data_path: str = ""
    figures_generated: tuple[str, ...] = ()
    valid: bool = False
    warning: str | None = None
    raw_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReportExtractionResult:
    report_markdown: str
    telemetry: ReportTelemetry


def _normalize_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return tuple(normalized)


def extract_report_and_telemetry(result_text: str) -> ReportExtractionResult:
    """Extract the report body and structured telemetry from the model output."""

    if not result_text.strip():
        return ReportExtractionResult(
            report_markdown="# Data Analysis Report\n\nNo valid output was produced.",
            telemetry=ReportTelemetry(warning="missing_output"),
        )

    raw_text = result_text.strip()
    telemetry = ReportTelemetry(warning="missing")
    telemetry_match = _TELEMETRY_PATTERN.search(raw_text)
    report_body = raw_text

    if telemetry_match:
        report_body = raw_text[: telemetry_match.start()].strip()
        telemetry_json = telemetry_match.group(1).strip()
        try:
            payload = json.loads(telemetry_json)
            if not isinstance(payload, dict):
                raise ValueError("Telemetry JSON must decode to an object.")
            telemetry = ReportTelemetry(
                methods=_normalize_string_list(payload.get("methods")),
                domain=str(payload.get("domain", "unknown")).strip() or "unknown",
                tools_used=_normalize_string_list(payload.get("tools_used")),
                search_used=bool(payload.get("search_used", False)),
                search_notes=str(payload.get("search_notes", "unknown")).strip() or "unknown",
                cleaned_data_saved=bool(payload.get("cleaned_data_saved", False)),
                cleaned_data_path=str(payload.get("cleaned_data_path", "")).strip(),
                figures_generated=_normalize_string_list(payload.get("figures_generated")),
                valid=True,
                warning=None,
                raw_payload=payload,
            )
        except Exception as exc:
            telemetry = ReportTelemetry(warning=f"malformed:{exc}")

    report_match = re.search(r"(# .+[\s\S]*)", report_body)
    if report_match:
        cleaned_report = report_match.group(1).strip()
    else:
        cleaned_report = report_body.strip()

    if not cleaned_report:
        cleaned_report = "# Data Analysis Report\n\nNo valid Markdown report body was produced."

    return ReportExtractionResult(report_markdown=cleaned_report, telemetry=telemetry)


def extract_markdown_report(result_text: str) -> str:
    """Extract only the human-facing Markdown report from the agent output."""

    return extract_report_and_telemetry(result_text).report_markdown


def _resolve_markdown_asset_path(
    raw_target: str,
    *,
    project_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> str:
    target = raw_target.strip()
    if not target:
        return raw_target

    if target.startswith(_URL_SCHEMES) or target.startswith("/"):
        return target

    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    candidate_path = Path(target)
    if candidate_path.is_absolute():
        return candidate_path.resolve().as_posix()

    roots: list[Path] = []
    if base_dir is not None:
        roots.append(Path(base_dir))
    if project_root is not None:
        roots.append(Path(project_root))
    else:
        roots.append(PROJECT_ROOT)
    roots.append(Path.cwd())

    for root in roots:
        try:
            resolved = (root / candidate_path).resolve()
        except OSError:
            continue
        if resolved.exists():
            return resolved.as_posix()

    fallback_root = Path(project_root) if project_root is not None else PROJECT_ROOT
    return (fallback_root / candidate_path).resolve().as_posix()


def normalize_markdown_image_paths(
    report_markdown: str,
    *,
    project_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> str:
    """Convert Markdown image references to absolute filesystem paths."""

    def replace(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        raw_target = match.group(2).strip()
        normalized_target = _resolve_markdown_asset_path(
            raw_target,
            project_root=project_root,
            base_dir=base_dir,
        )
        return f"![{alt_text}]({normalized_target})"

    return _MARKDOWN_IMAGE_PATTERN.sub(replace, report_markdown)


def convert_markdown_images_to_gradio_urls(
    report_markdown: str,
    *,
    project_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> str:
    """Convert Markdown image references to Gradio-served file URLs."""

    def replace(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        raw_target = match.group(2).strip()
        absolute_target = _resolve_markdown_asset_path(
            raw_target,
            project_root=project_root,
            base_dir=base_dir,
        )
        # Gradio 4.x serves local files through the /file=... route.
        gradio_target = f"/file={quote(absolute_target, safe='/:')}"
        return f"![{alt_text}]({gradio_target})"

    return _MARKDOWN_IMAGE_PATTERN.sub(replace, report_markdown)


def save_markdown_report(report_markdown: str, report_path: str | Path) -> Path:
    """Persist a Markdown report to disk."""

    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown, encoding="utf-8")
    return path
