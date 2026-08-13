"""Safe JSONL loading for the bundled and user-supplied mentor benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from resume_agent.evaluation.models import EvaluationCase, MentorDataset


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "mentor_v1.jsonl"
_CASE_ADAPTER = TypeAdapter(EvaluationCase)


class DatasetError(ValueError):
    """Raised for invalid benchmark input without echoing sensitive case content."""


def load_dataset(path: str | Path | None = None) -> MentorDataset:
    dataset_path = Path(path) if path is not None else DEFAULT_DATASET_PATH
    cases = []
    seen_ids: set[str] = set()

    try:
        lines = dataset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetError(f"could not read dataset: {dataset_path}") from exc

    decoded_lines: list[tuple[int, object]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(
                f"invalid JSON in dataset {dataset_path}, line {line_number}"
            ) from exc
        decoded_lines.append((line_number, payload))

    for line_number, payload in decoded_lines:
        try:
            case = _CASE_ADAPTER.validate_python(payload)
        except ValidationError as exc:
            raise DatasetError(
                f"invalid evaluation case in {dataset_path}, line {line_number}"
            ) from exc
        if case.id in seen_ids:
            raise DatasetError(
                f"duplicate case id in {dataset_path}, line {line_number}"
            )
        seen_ids.add(case.id)
        cases.append(case)

    if not cases:
        raise DatasetError(f"dataset contains no cases: {dataset_path}")
    return MentorDataset(version=dataset_path.stem, cases=cases)
