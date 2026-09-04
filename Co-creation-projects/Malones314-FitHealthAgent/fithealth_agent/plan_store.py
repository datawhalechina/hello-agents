from __future__ import annotations

import hashlib
import json
import re
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from fithealth_agent.atomic_json import atomic_write_json
from fithealth_agent.json_file_lock import JsonFileLock
from fithealth_agent.settings import data_path


ALLOWED_SOURCES = {"agent_generated", "agent_auto_corrected", "uploaded_optimized"}


class TrainingPlanStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_path("training_plans.json")
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self._lock, JsonFileLock(self.path):
                if not self.path.exists():
                    self._write_all([])

    def _read_all(self) -> list[dict[str, Any]]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("training_plans.json 必须是数组格式")
        return data

    def _write_all(self, items: list[dict[str, Any]]) -> None:
        # DATA-06：flush + fsync + replace，且 tmp 名带 pid+uuid。
        atomic_write_json(self.path, items)

    @staticmethod
    def validate_date(value: str) -> str:
        try:
            return date_type.fromisoformat(value).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("计划日期格式必须为 YYYY-MM-DD") from exc

    @staticmethod
    def clean_subject(value: str) -> str:
        subject = re.sub(r"[\\/:*?\"<>|\r\n]+", "", str(value or "")).strip()
        if not subject:
            raise ValueError("训练科目不能为空")
        if len(subject) > 40:
            raise ValueError("训练科目不能超过 40 个字符")
        if not subject.endswith("训练"):
            subject += "训练"
        return subject

    @staticmethod
    def clean_title(value: str) -> str:
        title = re.sub(r"[\r\n]+", " ", str(value or "")).strip()
        if not title:
            raise ValueError("计划标题不能为空")
        if len(title) > 100:
            raise ValueError("计划标题不能超过 100 个字符")
        return title

    @staticmethod
    def clean_memo(value: str) -> str:
        memo = str(value or "").strip()
        if len(memo) > 1_000:
            raise ValueError("计划备忘录不能超过 1000 个字符")
        return memo

    @staticmethod
    def content_hash(content: str) -> str:
        normalized = str(content or "").strip().replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _filename(self, plan_date: str, subject: str, items: list[dict[str, Any]], exclude_id: str = "") -> str:
        base = f"{plan_date[2:]}-{subject}"
        used = {
            item.get("filename")
            for item in items
            if item.get("id") != exclude_id
        }
        candidate = f"{base}.md"
        number = 2
        while candidate in used:
            candidate = f"{base}-{number}.md"
            number += 1
        return candidate

    def list_plans(self) -> list[dict[str, Any]]:
        with self._lock, JsonFileLock(self.path):
            return list(reversed(self._read_all()))

    def get(self, plan_id: str) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            return next((item for item in self._read_all() if item.get("id") == plan_id), None)

    def add(self, *, date: str, subject: str, title: str, content: str, source: str, memo: str = "") -> dict[str, Any]:
        plan_date = self.validate_date(date)
        clean_subject = self.clean_subject(subject)
        clean_title = self.clean_title(title)
        content = str(content or "").strip()
        if not content:
            raise ValueError("计划内容不能为空")
        if len(content.encode("utf-8")) > 1024 * 1024:
            raise ValueError("计划内容不能超过 1 MiB")
        if source not in ALLOWED_SOURCES:
            raise ValueError("计划来源无效")
        memo = self.clean_memo(memo)

        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            digest = self.content_hash(content)
            duplicate = next(
                (item for item in items if item.get("content_hash") == digest and item.get("date") == plan_date),
                None,
            )
            if duplicate:
                memo_updated = bool(memo and memo != duplicate.get("memo"))
                if memo_updated:
                    duplicate["memo"] = memo
                    duplicate["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._write_all(items)
                return {**duplicate, "duplicate": True, "memo_updated": memo_updated}

            now = datetime.now(timezone.utc).isoformat()
            item = {
                "id": str(uuid4()),
                "date": plan_date,
                "subject": clean_subject,
                "filename": self._filename(plan_date, clean_subject, items),
                "title": clean_title,
                "content": content,
                "source": source,
                "content_hash": digest,
                "memo": memo,
                "created_at": now,
                "updated_at": now,
            }
            items.append(item)
            self._write_all(items)
            return {**item, "duplicate": False}

    def update(self, plan_id: str, *, date: str, subject: str, title: str, memo: str = "", content: str | None = None) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            item = next((candidate for candidate in items if candidate.get("id") == plan_id), None)
            if item is None:
                return None
            plan_date = self.validate_date(date)
            clean_subject = self.clean_subject(subject)
            item["date"] = plan_date
            item["subject"] = clean_subject
            item["title"] = self.clean_title(title)
            item["memo"] = self.clean_memo(memo)
            if content is not None:
                clean_content = str(content).strip()
                if not clean_content:
                    raise ValueError("计划内容不能为空")
                if len(clean_content.encode("utf-8")) > 1024 * 1024:
                    raise ValueError("计划内容不能超过 1 MiB")
                item["content"] = clean_content
                item["content_hash"] = self.content_hash(clean_content)
            item["filename"] = self._filename(plan_date, clean_subject, items, exclude_id=plan_id)
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_all(items)
            return item

    def delete(self, plan_id: str) -> bool:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            remaining = [item for item in items if item.get("id") != plan_id]
            if len(remaining) == len(items):
                return False
            self._write_all(remaining)
            return True

    def delete_many(self, plan_ids: list[str]) -> int:
        wanted = set(plan_ids)
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            remaining = [item for item in items if item.get("id") not in wanted]
            removed = len(items) - len(remaining)
            if removed:
                self._write_all(remaining)
            return removed

    def clear(self) -> int:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            self._write_all([])
            return len(items)
