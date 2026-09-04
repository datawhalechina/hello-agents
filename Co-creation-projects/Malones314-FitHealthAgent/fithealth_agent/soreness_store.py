"""Short-lived, user-visible muscle soreness reports."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any, Iterable
from uuid import uuid4
from zoneinfo import ZoneInfo

from .atomic_json import atomic_write_json
from .json_file_lock import JsonFileLock
from .muscle_map import muscle_ids_for_region
from .muscle_recovery import REGION_ALIASES, SorenessReport
from .settings import data_path


BEIJING = ZoneInfo("Asia/Shanghai")
logger = logging.getLogger(__name__)
LEVELS = frozenset({"recovered", "sore", "painful"})


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("酸痛记录时间格式无效")
    if result.tzinfo is None:
        result = result.replace(tzinfo=BEIJING)
    return result.astimezone(BEIJING)


class SorenessStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_path("muscle_soreness.json")
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self._lock, JsonFileLock(self.path):
                if not self.path.exists():
                    atomic_write_json(self.path, [])

    def _read_unlocked(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("肌群酸痛记录无法读取，已停止写入以保护原文件") from exc
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValueError("肌群酸痛记录格式无效，已停止写入以保护原文件")
        return value

    def _write_unlocked(self, items: list[dict[str, Any]]) -> None:
        atomic_write_json(self.path, items)

    @staticmethod
    def _serialize(report: SorenessReport, *, report_id: str | None = None) -> dict[str, Any]:
        if report.region not in REGION_ALIASES or report.level not in LEVELS:
            raise ValueError("肌群酸痛记录的区域或程度无效")
        return {
            "id": report_id or report.id or uuid4().hex,
            "region": report.region,
            "muscle_ids": list(report.muscle_ids),
            "level": report.level,
            "reported_at": _parse_datetime(report.reported_at).isoformat(),
            "expires_at": _parse_datetime(report.expires_at).isoformat(),
            "evidence": str(report.evidence or "")[:500],
            "expired": bool(report.expired),
        }

    @staticmethod
    def _deserialize(item: dict[str, Any]) -> SorenessReport:
        region = str(item.get("region") or "")
        level = str(item.get("level") or "")
        if region not in REGION_ALIASES or level not in LEVELS:
            raise ValueError("肌群酸痛记录的区域或程度无效")
        return SorenessReport(
            region=region,
            muscle_ids=tuple(str(value) for value in item.get("muscle_ids") or ()),
            level=level,
            reported_at=_parse_datetime(item.get("reported_at")),
            expires_at=_parse_datetime(item.get("expires_at")),
            evidence=str(item.get("evidence") or ""),
            id=str(item.get("id") or ""),
            expired=bool(item.get("expired")),
        )

    def list_reports(self, *, active_only: bool = False, now: datetime | None = None) -> list[SorenessReport]:
        now = (now or datetime.now(BEIJING)).astimezone(BEIJING)
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            reports = []
            for item in items:
                try:
                    report = self._deserialize(item)
                    if not active_only or (
                        not bool(item.get("expired"))
                        and _parse_datetime(item.get("expires_at")) > now
                    ):
                        reports.append(report)
                except (ValueError, TypeError, KeyError):
                    logger.warning("跳过损坏的酸痛记录")
        reports.sort(key=lambda item: item.reported_at)
        return reports

    def add_reports(self, reports: Iterable[SorenessReport]) -> list[SorenessReport]:
        serialized = [self._serialize(report) for report in reports]
        if not serialized:
            return []
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            superseded_at = datetime.now(BEIJING).isoformat()
            for item in items:
                if item.get("expired"):
                    continue
                existing_region = str(item.get("region") or "")
                existing_ids = {str(value) for value in item.get("muscle_ids") or ()}
                same_region = [
                    incoming for incoming in serialized
                    if incoming["region"] == existing_region
                ]
                if not same_region:
                    continue
                incoming_ids = {
                    str(value)
                    for incoming in same_region
                    for value in incoming.get("muscle_ids") or ()
                }
                if existing_ids and incoming_ids:
                    remaining_ids = existing_ids - incoming_ids
                    if remaining_ids == existing_ids:
                        continue
                    if remaining_ids:
                        item["muscle_ids"] = sorted(remaining_ids)
                        continue
                item["expired"] = True
                item["expired_at"] = superseded_at
                item["expiration_reason"] = "superseded"
            items.extend(serialized)
            self._write_unlocked(items)
        return [self._deserialize(item) for item in serialized]

    def update_report(
        self,
        report_id: str,
        *,
        region: str,
        level: str,
        evidence: str | None = None,
        now: datetime | None = None,
    ) -> SorenessReport | None:
        if region not in REGION_ALIASES or level not in LEVELS:
            raise ValueError("肌群酸痛记录的区域或程度无效")
        now = (now or datetime.now(BEIJING)).astimezone(BEIJING)
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            for index, item in enumerate(items):
                if str(item.get("id") or "") != report_id:
                    continue
                previous_reported = _parse_datetime(item.get("reported_at"))
                level_changed = str(item.get("level") or "") != level
                reported_at = now if level_changed else previous_reported
                expires_at = now + timedelta(hours=72) if level_changed else _parse_datetime(item.get("expires_at"))
                updated = SorenessReport(
                    region=region,
                    muscle_ids=muscle_ids_for_region(region),
                    level=level,
                    reported_at=reported_at,
                    expires_at=expires_at,
                    evidence=str(evidence if evidence is not None else item.get("evidence") or "")[:500],
                    id=report_id,
                )
                for other_index, other in enumerate(items):
                    if other_index == index or other.get("expired") or str(other.get("region") or "") != region:
                        continue
                    other["expired"] = True
                    other["expired_at"] = now.isoformat()
                    other["expiration_reason"] = "superseded"
                items[index] = self._serialize(updated, report_id=report_id)
                self._write_unlocked(items)
                return updated
        return None

    def delete_report(self, report_id: str) -> bool:
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            remaining = [item for item in items if str(item.get("id") or "") != report_id]
            if len(remaining) == len(items):
                return False
            self._write_unlocked(remaining)
            return True

    def cleanup_expired(self, *, now: datetime | None = None) -> int:
        now = (now or datetime.now(BEIJING)).astimezone(BEIJING)
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            changed = 0
            for item in items:
                try:
                    if not item.get("expired") and _parse_datetime(item.get("expires_at")) <= now:
                        item["expired"] = True
                        item["expired_at"] = now.isoformat()
                        item["expiration_reason"] = "ttl"
                        changed += 1
                except ValueError:
                    continue
            if changed:
                self._write_unlocked(items)
            return changed

    def clear(self) -> int:
        with self._lock, JsonFileLock(self.path):
            items = self._read_unlocked()
            self._write_unlocked([])
            return len(items)


__all__ = ["LEVELS", "SorenessStore", "muscle_ids_for_region"]
