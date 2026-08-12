"""Visual review helpers for scientific figure auditing."""

from __future__ import annotations

import base64
import io
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .prompts import build_visual_reviewer_prompt
from .reporting import ReportTelemetry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_VISION_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
_MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


@dataclass(frozen=True)
class VisualReviewFinding:
    figure: str
    severity: str
    issue: str
    suggested_fix: str


@dataclass(frozen=True)
class PreparedVisionImage:
    path: Path
    alt_text: str
    original_size: tuple[int, int]
    resized_size: tuple[int, int]
    output_bytes: int
    encoded_image: str
    media_type: str = "image/jpeg"


@dataclass(frozen=True)
class VisualReviewResult:
    status: str
    decision: str
    summary: str
    findings: tuple[VisualReviewFinding, ...] = ()
    figures_reviewed: tuple[str, ...] = ()
    skipped_figures: tuple[str, ...] = ()
    duration_ms: int = 0
    raw_response: str = ""
    image_metadata: tuple[dict[str, Any], ...] = ()
    warning: str = ""


def _elapsed_ms(start_time: float) -> int:
    return int(round((time.perf_counter() - start_time) * 1000))


def _extract_first_json_object(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        raise ValueError("Model returned an empty response.")

    if stripped.startswith("```"):
        fence_lines = stripped.splitlines()
        if len(fence_lines) >= 3 and fence_lines[0].startswith("```") and fence_lines[-1].startswith("```"):
            stripped = "\n".join(fence_lines[1:-1]).strip()

    start = stripped.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]
    raise ValueError("Unterminated JSON object in visual review response.")


def _parse_visual_response(raw_response: str) -> tuple[str, str, tuple[VisualReviewFinding, ...]]:
    payload = json.loads(_extract_first_json_object(raw_response))
    if not isinstance(payload, dict):
        raise ValueError("Visual reviewer response JSON must be an object.")

    decision = str(payload.get("decision", "")).strip()
    if decision not in {"Pass", "Flag"}:
        raise ValueError("Visual reviewer decision must be Pass or Flag.")

    summary = str(payload.get("summary", "")).strip()
    if not summary:
        raise ValueError("Visual reviewer summary must be a non-empty string.")

    findings_payload = payload.get("findings", [])
    if not isinstance(findings_payload, list):
        raise ValueError("Visual reviewer findings must be a list.")

    findings: list[VisualReviewFinding] = []
    for item in findings_payload:
        if not isinstance(item, dict):
            continue
        findings.append(
            VisualReviewFinding(
                figure=str(item.get("figure", "")).strip() or "unknown",
                severity=str(item.get("severity", "")).strip() or "medium",
                issue=str(item.get("issue", "")).strip() or "未提供具体问题。",
                suggested_fix=str(item.get("suggested_fix", "")).strip() or "请检查该图表的可读性与标注。",
            )
        )
    return decision, summary, tuple(findings)


def _resolve_candidate_path(raw_target: str | Path, *, run_dir: Path) -> Path:
    candidate = Path(str(raw_target).strip())
    if candidate.is_absolute():
        return candidate.resolve()

    project_candidate = (PROJECT_ROOT / candidate).resolve()
    if project_candidate.exists():
        return project_candidate

    run_candidate = (run_dir / candidate).resolve()
    if run_candidate.exists():
        return run_candidate

    return project_candidate


def _matches_review_round(path: Path, review_round: int) -> bool:
    return f"review_round_{review_round}" in path.as_posix()


def _iter_report_image_refs(report_markdown: str) -> list[tuple[str, str]]:
    return [(match.group(1).strip(), match.group(2).strip()) for match in _MARKDOWN_IMAGE_PATTERN.finditer(report_markdown)]


def select_visual_review_candidates(
    *,
    report_markdown: str,
    telemetry: ReportTelemetry,
    run_dir: Path,
    review_round: int,
    max_images: int,
) -> tuple[list[tuple[Path, str]], tuple[str, ...]]:
    selected: list[tuple[Path, str]] = []
    skipped: list[str] = []
    seen: set[str] = set()

    def maybe_add(raw_target: str | Path, alt_text: str) -> None:
        resolved = _resolve_candidate_path(raw_target, run_dir=run_dir)
        resolved_key = resolved.as_posix()
        if resolved_key in seen:
            return
        seen.add(resolved_key)

        if not resolved.exists():
            skipped.append(f"{resolved.name or resolved_key} (missing_file)")
            return
        if not _matches_review_round(resolved, review_round):
            skipped.append(f"{resolved.name} (different_review_round)")
            return
        if resolved.suffix.lower() not in SUPPORTED_VISION_SUFFIXES:
            skipped.append(f"{resolved.name} (unsupported_suffix:{resolved.suffix.lower() or 'none'})")
            return
        if len(selected) >= max_images:
            skipped.append(f"{resolved.name} (omitted_due_to_limit)")
            return
        selected.append((resolved, alt_text.strip() or resolved.stem))

    for alt_text, target in _iter_report_image_refs(report_markdown):
        maybe_add(target, alt_text)

    for figure_path in telemetry.figures_generated:
        maybe_add(figure_path, Path(str(figure_path)).stem)

    return selected, tuple(skipped)


def prepare_image_for_vision(
    image_path: Path,
    *,
    alt_text: str,
    max_image_side: int = 1024,
    jpeg_quality: int = 80,
) -> PreparedVisionImage:
    from PIL import Image

    side_limit = max(256, min(int(max_image_side), 2048))
    quality = max(40, min(int(jpeg_quality), 90))

    with Image.open(image_path) as opened:
        image = opened.convert("RGB")
        original_size = (image.width, image.height)
        longest_side = max(image.size)
        if longest_side > side_limit:
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:  # pragma: no cover - compatibility fallback
                resample = Image.LANCZOS
            image.thumbnail((side_limit, side_limit), resample)
        resized_size = (image.width, image.height)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return PreparedVisionImage(
        path=image_path.resolve(),
        alt_text=alt_text,
        original_size=original_size,
        resized_size=resized_size,
        output_bytes=len(base64.b64decode(encoded)),
        encoded_image=encoded,
    )


def _extract_message_text(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        text_parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")).strip())
        return "\n".join(part for part in text_parts if part).strip()
    return str(message_content).strip()


def run_visual_review(
    *,
    runtime_config: RuntimeConfig,
    report_markdown: str,
    telemetry: ReportTelemetry,
    run_dir: Path,
    review_round: int,
    max_images: int = 3,
    max_image_side: int = 1024,
) -> VisualReviewResult:
    started_at = time.perf_counter()

    if not runtime_config.vision_configured:
        return VisualReviewResult(
            status="unavailable",
            decision="Unavailable",
            summary="视觉审稿未启用：未检测到完整的视觉模型配置。",
            duration_ms=_elapsed_ms(started_at),
            warning="missing_vision_configuration",
        )

    selected, skipped = select_visual_review_candidates(
        report_markdown=report_markdown,
        telemetry=telemetry,
        run_dir=run_dir,
        review_round=review_round,
        max_images=max_images,
    )
    if not selected:
        return VisualReviewResult(
            status="skipped",
            decision="Skipped",
            summary="视觉审稿已跳过：当前轮没有可审查的栅格图表。",
            skipped_figures=skipped,
            duration_ms=_elapsed_ms(started_at),
            warning="no_supported_figures",
        )

    prepared_images: list[PreparedVisionImage] = []
    skipped_figures = list(skipped)
    for image_path, alt_text in selected:
        try:
            prepared_images.append(
                prepare_image_for_vision(
                    image_path,
                    alt_text=alt_text,
                    max_image_side=max_image_side,
                )
            )
        except Exception as exc:
            skipped_figures.append(f"{image_path.name} (prepare_failed:{exc})")

    if not prepared_images:
        return VisualReviewResult(
            status="failed",
            decision="Failed",
            summary="视觉审稿失败：候选图表均无法完成图像预处理。",
            skipped_figures=tuple(skipped_figures),
            duration_ms=_elapsed_ms(started_at),
            warning="image_preparation_failed",
        )

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Review round: {review_round}\n"
                "You are reviewing compressed scientific figure copies for readability, layout quality, labeling, "
                "color usage, and consistency with the report's figure references.\n"
                "Candidate figure references:\n"
                + "\n".join(
                    f"- {image.path.name} | alt={image.alt_text} | original={image.original_size[0]}x{image.original_size[1]} | "
                    f"compressed={image.resized_size[0]}x{image.resized_size[1]}"
                    for image in prepared_images
                )
            ),
        }
    ]
    for index, image in enumerate(prepared_images, start=1):
        content.append(
            {
                "type": "text",
                "text": f"Figure {index}: {image.path.name}\nReported alt text: {image.alt_text}",
            }
        )
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image.media_type};base64,{image.encoded_image}"},
            }
        )

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=runtime_config.vision_api_key,
            base_url=runtime_config.vision_base_url,
            timeout=runtime_config.vision_timeout,
        )
        response = client.chat.completions.create(
            model=str(runtime_config.vision_model_id),
            temperature=0,
            messages=[
                {"role": "system", "content": build_visual_reviewer_prompt()},
                {"role": "user", "content": content},
            ],
        )
        raw_response = _extract_message_text(response.choices[0].message.content if response.choices else "")
        decision, summary, findings = _parse_visual_response(raw_response)
        duration_ms = _elapsed_ms(started_at)
        return VisualReviewResult(
            status="completed",
            decision=decision,
            summary=summary,
            findings=findings,
            figures_reviewed=tuple(image.path.as_posix() for image in prepared_images),
            skipped_figures=tuple(skipped_figures),
            duration_ms=duration_ms,
            raw_response=raw_response,
            image_metadata=tuple(
                {
                    "path": image.path.as_posix(),
                    "alt_text": image.alt_text,
                    "original_size": list(image.original_size),
                    "resized_size": list(image.resized_size),
                    "output_bytes": image.output_bytes,
                    "media_type": image.media_type,
                }
                for image in prepared_images
            ),
        )
    except Exception as exc:
        return VisualReviewResult(
            status="failed",
            decision="Failed",
            summary=f"视觉审稿失败：{exc}",
            figures_reviewed=tuple(image.path.as_posix() for image in prepared_images),
            skipped_figures=tuple(skipped_figures),
            duration_ms=_elapsed_ms(started_at),
            warning=str(exc),
        )


__all__ = [
    "PreparedVisionImage",
    "SUPPORTED_VISION_SUFFIXES",
    "VisualReviewFinding",
    "VisualReviewResult",
    "prepare_image_for_vision",
    "run_visual_review",
    "select_visual_review_candidates",
]
