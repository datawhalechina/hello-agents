from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backend.config import ROOT_DIR, settings


_last_cleanup: dict[str, datetime] = {}


def cleanup_deep_research_artifacts(*, force: bool = False) -> dict[str, Any]:
    """Remove old deep research run artifacts.

    This intentionally does not delete notes. Notes are indexed memory artifacts,
    while runs are reproducible per-execution files that can grow quickly.
    """

    if not _should_run("deep_research", force=force):
        return {"skipped": True, "reason": "interval"}

    run_root = _resolve_workspace(settings.run_workspace)
    stats = _cleanup_children(
        run_root,
        retention_days=settings.research_run_retention_days,
        file_patterns=["*"],
        delete_dirs=True,
    )
    stats.update(
        {
            "skipped": False,
            "target": str(run_root),
            "retention_days": settings.research_run_retention_days,
        }
    )
    return stats


def cleanup_rss_artifacts(*, force: bool = False) -> dict[str, Any]:
    """Remove old RSS generated files while keeping article state intact."""

    if not _should_run("rss_digest", force=force):
        return {"skipped": True, "reason": "interval"}

    data_root = Path(settings.rss_digest_data_root).resolve() / "runs"
    totals = {"deleted_files": 0, "deleted_dirs": 0, "deleted_bytes": 0}

    for relative, retention_days, patterns in (
        ("digests", settings.rss_digest_retention_days, ["digest_*.html"]),
        ("raw", settings.rss_cache_retention_days, ["*"]),
        ("extracted", settings.rss_cache_retention_days, ["*"]),
        ("translated", settings.rss_cache_retention_days, ["*"]),
    ):
        stats = _cleanup_children(
            data_root / relative,
            retention_days=retention_days,
            file_patterns=patterns,
            delete_dirs=False,
        )
        for key in totals:
            totals[key] += stats[key]

    totals.update(
        {
            "skipped": False,
            "target": str(data_root),
            "digest_retention_days": settings.rss_digest_retention_days,
            "cache_retention_days": settings.rss_cache_retention_days,
        }
    )
    return totals


def _should_run(name: str, *, force: bool) -> bool:
    if not settings.maintenance_cleanup_enabled:
        return False

    now = datetime.now()
    last_run = _last_cleanup.get(name)
    interval = timedelta(hours=max(settings.maintenance_cleanup_interval_hours, 1))
    if not force and last_run and now - last_run < interval:
        return False

    _last_cleanup[name] = now
    return True


def _resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _cleanup_children(
    root: Path,
    *,
    retention_days: int,
    file_patterns: list[str],
    delete_dirs: bool,
) -> dict[str, int]:
    stats = {"deleted_files": 0, "deleted_dirs": 0, "deleted_bytes": 0}
    if retention_days <= 0 or not root.exists():
        return stats

    root = root.resolve()
    cutoff = datetime.now() - timedelta(days=retention_days)

    if delete_dirs:
        for child in root.iterdir():
            if not child.exists() or not _is_child_of(child, root):
                continue
            if datetime.fromtimestamp(child.stat().st_mtime) >= cutoff:
                continue
            if child.is_dir():
                stats["deleted_bytes"] += _directory_size(child)
                shutil.rmtree(child)
                stats["deleted_dirs"] += 1
            elif child.is_file():
                stats["deleted_bytes"] += child.stat().st_size
                child.unlink()
                stats["deleted_files"] += 1
        return stats

    for pattern in file_patterns:
        for path in root.glob(pattern):
            if not path.is_file() or not _is_child_of(path, root):
                continue
            if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
                continue
            stats["deleted_bytes"] += path.stat().st_size
            path.unlink()
            stats["deleted_files"] += 1
    return stats


def _is_child_of(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
