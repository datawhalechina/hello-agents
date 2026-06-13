"""Local persistence for saved internship applications."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from hashlib import sha1
from pathlib import Path
from threading import Lock
from typing import Any, Mapping


APPLICATION_STATUSES = ("待投递", "已投递", "笔试", "面试", "拒绝", "Offer", "放弃")
TRACKING_FIELDS = (
    "application_channel",
    "applied_at",
    "next_action",
    "next_action_at",
    "resume_version",
    "withdrawal_reason",
)


class ApplicationStore:
    """Persist saved jobs and application statuses to a local JSON file."""

    def __init__(self, base_dir: Path | None = None) -> None:
        backend_dir = Path(__file__).resolve().parents[2]
        self.base_dir = base_dir or backend_dir / "data"
        self.path = self.base_dir / "applications.json"
        self._lock = Lock()

    def list_applications(self) -> list[dict[str, Any]]:
        """Return saved applications sorted by most recently updated."""

        with self._lock:
            items = self._read_items()

        return sorted(
            items,
            key=lambda item: str(item.get("updated_at") or item.get("saved_at") or ""),
            reverse=True,
        )

    def save_application(
        self,
        job: Mapping[str, Any],
        *,
        application_status: str | None = None,
        status_note: str | None = None,
        application_channel: str | None = None,
        applied_at: str | None = None,
        next_action: str | None = None,
        next_action_at: str | None = None,
        resume_version: str | None = None,
        withdrawal_reason: str | None = None,
    ) -> dict[str, Any]:
        """Save or update a job while preserving an existing application status."""

        if application_status is not None:
            self._validate_status(application_status)
        self._validate_date("applied_at", applied_at)
        self._validate_date("next_action_at", next_action_at)

        tracking_values = {
            "application_channel": application_channel,
            "applied_at": applied_at,
            "next_action": next_action,
            "next_action_at": next_action_at,
            "resume_version": resume_version,
            "withdrawal_reason": withdrawal_reason,
        }

        now = self._now()
        normalized = self._normalize_job(job)
        item_id = normalized["id"]

        with self._lock:
            items = self._read_items()
            existing_index = self._find_index(items, item_id)

            if existing_index is None:
                record = {
                    **normalized,
                    "application_status": application_status or APPLICATION_STATUSES[0],
                    "status_note": status_note or "",
                    **{
                        field: _string_value(tracking_values[field])
                        for field in TRACKING_FIELDS
                    },
                    "saved_at": now,
                    "updated_at": now,
                }
                items.append(record)
            else:
                existing = items[existing_index]
                record = {
                    **existing,
                    **normalized,
                    "application_status": (
                        application_status
                        if application_status is not None
                        else existing.get("application_status", APPLICATION_STATUSES[0])
                    ),
                    "status_note": (
                        status_note
                        if status_note is not None
                        else existing.get("status_note", "")
                    ),
                    **{
                        field: (
                            _string_value(tracking_values[field])
                            if tracking_values[field] is not None
                            else existing.get(field, "")
                        )
                        for field in TRACKING_FIELDS
                    },
                    "saved_at": existing.get("saved_at") or now,
                    "updated_at": now,
                }
                items[existing_index] = record

            self._write_items(items)

        return record

    def update_application(
        self,
        item_id: str,
        *,
        application_status: str | None = None,
        status_note: str | None = None,
        application_channel: str | None = None,
        applied_at: str | None = None,
        next_action: str | None = None,
        next_action_at: str | None = None,
        resume_version: str | None = None,
        withdrawal_reason: str | None = None,
    ) -> dict[str, Any]:
        """Update mutable tracking fields for a saved application."""

        if application_status is not None:
            self._validate_status(application_status)
        self._validate_date("applied_at", applied_at)
        self._validate_date("next_action_at", next_action_at)

        tracking_values = {
            "application_channel": application_channel,
            "applied_at": applied_at,
            "next_action": next_action,
            "next_action_at": next_action_at,
            "resume_version": resume_version,
            "withdrawal_reason": withdrawal_reason,
        }

        with self._lock:
            items = self._read_items()
            existing_index = self._find_index(items, item_id)
            if existing_index is None:
                raise KeyError(item_id)

            record = dict(items[existing_index])
            if application_status is not None:
                record["application_status"] = application_status
            if status_note is not None:
                record["status_note"] = status_note
            for field, value in tracking_values.items():
                if value is not None:
                    record[field] = _string_value(value)
            record["updated_at"] = self._now()
            items[existing_index] = record
            self._write_items(items)

        return record

    def delete_application(self, item_id: str) -> bool:
        """Delete a saved application by id."""

        with self._lock:
            items = self._read_items()
            remaining = [item for item in items if str(item.get("id")) != item_id]
            if len(remaining) == len(items):
                return False
            self._write_items(remaining)

        return True

    def _read_items(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return []

        return [
            self._with_tracking_defaults(item)
            for item in items
            if isinstance(item, dict)
        ]

    def _write_items(self, items: list[dict[str, Any]]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = {"items": items}
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    @staticmethod
    def _find_index(items: list[dict[str, Any]], item_id: str) -> int | None:
        for index, item in enumerate(items):
            if str(item.get("id")) == item_id:
                return index
        return None

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"Unsupported application status: {status}")

    @staticmethod
    def _validate_date(field_name: str, value: str | None) -> None:
        if value in (None, ""):
            return
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must use YYYY-MM-DD")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must use YYYY-MM-DD") from exc
        if parsed.isoformat() != value:
            raise ValueError(f"{field_name} must use YYYY-MM-DD")

    @staticmethod
    def _with_tracking_defaults(item: dict[str, Any]) -> dict[str, Any]:
        return {
            **item,
            **{field: _string_value(item.get(field)) for field in TRACKING_FIELDS},
        }

    @staticmethod
    def _normalize_job(job: Mapping[str, Any]) -> dict[str, Any]:
        source_url = _string_value(job.get("source_url"))
        company = _string_value(job.get("company")) or "未确认"
        title = _string_value(job.get("title")) or "未确认"
        location = _string_value(job.get("location")) or "未确认"
        provided_id = _string_value(job.get("id"))
        stable_id = _stable_job_id(
            source_url=source_url,
            company=company,
            title=title,
            location=location,
        )
        item_id = stable_id if source_url else provided_id or stable_id

        return {
            "id": item_id,
            "company": company,
            "title": title,
            "location": location,
            "source_url": source_url,
            "source_title": _string_value(job.get("source_title")) or title,
            "requirements": _string_list(job.get("requirements")),
            "responsibilities": _string_list(job.get("responsibilities")),
            "tech_stack": _string_list(job.get("tech_stack")),
            "duration": _string_value(job.get("duration")) or "未确认",
            "deadline": _string_value(job.get("deadline")) or "未确认",
            "match_score": _score_value(job.get("match_score")),
            "match_reason": _string_value(job.get("match_reason"))
            or "信息不足，需点开来源确认",
            "resume_advice": _string_list(job.get("resume_advice")),
            "risks": _string_list(job.get("risks")),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_job_id(
    *,
    source_url: str,
    company: str,
    title: str,
    location: str,
) -> str:
    raw = source_url or f"{company}|{title}|{location}"
    return f"job_{sha1(raw.strip().lower().encode('utf-8')).hexdigest()[:12]}"


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _score_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, score))
