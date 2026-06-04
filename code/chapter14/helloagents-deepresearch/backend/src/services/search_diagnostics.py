"""Persistence helpers for search quality diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def persist_search_diagnostics(
    *,
    run_id: str,
    diagnostics: list[dict[str, Any]],
    base_dir: Path | None = None,
) -> str | None:
    """Persist search diagnostics as a local JSON file and return its path."""

    if not diagnostics:
        return None

    root = base_dir or Path(__file__).resolve().parents[2] / "data" / "search_diagnostics"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "diagnostics": diagnostics,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)
