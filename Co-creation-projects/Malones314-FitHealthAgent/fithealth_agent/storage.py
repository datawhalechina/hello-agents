import json
from threading import RLock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from fithealth_agent.atomic_json import atomic_write_json
from fithealth_agent.json_file_lock import JsonFileLock
from fithealth_agent.settings import data_path
from fithealth_agent.daily_checkin import normalize_agent_nutrition_record
from fithealth_agent.domain.profile_rules import DEFAULT_EQUIPMENT as PROFILE_DEFAULT_EQUIPMENT


class DailyRecordStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or data_path("daily_records.json")
        self._write_lock = RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            with self._write_lock, JsonFileLock(self.db_path):
                if not self.db_path.exists():
                    self._write_all([])

    def _read_all(self) -> list[dict[str, Any]]:
        content = self.db_path.read_text(encoding="utf-8")
        records = json.loads(content)
        if not isinstance(records, list):
            raise ValueError("daily_records.json 必须是数组格式。")
        migrated = False
        for item in records:
            if not isinstance(item, dict):
                raise ValueError("daily_records.json 包含无效记录。")
            if not item.get("id"):
                item["id"] = str(uuid4())
                migrated = True
            if not item.get("created_at"):
                item["created_at"] = datetime.now(timezone.utc).isoformat()
                migrated = True
            if not isinstance(item.get("revision"), int) or item["revision"] < 1:
                item["revision"] = 1
                migrated = True
        if self._migrate_agent_nutrition_records(records):
            migrated = True
        for item in records:
            record = item.get("record")
            if (
                item.get("category") == "daily_checkin"
                and isinstance(record, dict)
                and record.get("nutrition_source") == "agent_tool"
                and any(key in record for key in ("热量_kcal", "蛋白质_g", "碳水_g", "脂肪_g", "餐次", "食物", "重量_g"))
            ):
                item["record"] = normalize_agent_nutrition_record(record)
                item["revision"] = int(item.get("revision") or 1) + 1
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                migrated = True
        if migrated:
            self._write_all(records)
        return records

    @staticmethod
    def _migrate_agent_nutrition_records(records: list[dict[str, Any]]) -> bool:
        """Move legacy Agent nutrition rows into their dated daily check-in."""
        from fithealth_agent.daily_checkin import (
            normalize_agent_nutrition_record, nutrition_estimate_from_totals,
        )
        migrated = False
        legacy_nutrition_keys = {
            "热量_kcal", "热量", "总热量", "total_kcal", "蛋白质_g", "蛋白质",
            "碳水_g", "碳水", "碳水化合物_g", "脂肪_g", "脂肪",
        }
        discarded_food_keys = {
            "餐次", "meal_slot", "食物", "food", "重量_g", "weight_g",
            "膳食纤维_g", "膳食纤维", "fiber_g", "备注",
        }
        for item in records:
            record = item.get("record")
            if (
                item.get("category") != "daily_checkin"
                or not isinstance(record, dict)
                or not legacy_nutrition_keys.intersection(record)
                or not (record.get("source") == "agent_tool" or record.get("nutrition_source") == "agent_tool")
            ):
                continue
            # Legacy check-ins can contain a zero-valued canonical placeholder
            # alongside the actual Chinese Agent estimate. Prefer the explicit
            # legacy nutrient fields when repairing that known shape.
            nutrients = normalize_agent_nutrition_record({
                key: record[key] for key in legacy_nutrition_keys if key in record
            })
            cleaned = {
                key: value for key, value in record.items()
                if key not in legacy_nutrition_keys and key not in discarded_food_keys
            }
            cleaned.update(nutrients)
            existing_meals = cleaned.get("meal_estimates")
            if not isinstance(existing_meals, list) or not existing_meals:
                cleaned["meal_estimates"] = [nutrition_estimate_from_totals(nutrients)]
            cleaned.pop("source", None)
            cleaned["nutrition_source"] = "agent_tool"
            item["record"] = cleaned
            item["revision"] = int(item.get("revision") or 1) + 1
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            migrated = True
        checkins = {
            str(item.get("date") or ""): item
            for item in records
            if item.get("category") == "daily_checkin"
        }
        removed: set[int] = set()
        for item in records:
            record = item.get("record")
            if (
                item.get("category") != "nutrition"
                or not isinstance(record, dict)
                or record.get("source") != "agent_tool"
            ):
                continue
            try:
                legacy_values = {
                    key: record[key] for key in legacy_nutrition_keys if key in record
                }
                normalized = normalize_agent_nutrition_record(legacy_values or record)
            except ValueError:
                # Keep unrecognized legacy rows intact rather than deleting evidence.
                continue
            normalized.setdefault("nutrition_source", "agent_tool")
            normalized["meal_estimates"] = [nutrition_estimate_from_totals(normalized)]
            day = str(item.get("date") or "")
            target = checkins.get(day)
            if target is None:
                item["category"] = "daily_checkin"
                item["record"] = normalized
                checkins[day] = item
            else:
                target_record = target.get("record")
                merged = dict(target_record) if isinstance(target_record, dict) else {}
                for field, value in normalized.items():
                    if field in {"calories_kcal", "protein_g", "carbs_g", "fat_g"}:
                        merged[field] = round(float(merged.get(field) or 0) + float(value), 1)
                    elif field == "meal_estimates" and isinstance(value, list):
                        existing_meals = merged.get(field)
                        merged[field] = [*(existing_meals if isinstance(existing_meals, list) else []), *value]
                    else:
                        merged[field] = value
                target["record"] = merged
                target["revision"] = max(
                    int(target.get("revision") or 1), int(item.get("revision") or 1)
                ) + 1
                target["updated_at"] = datetime.now(timezone.utc).isoformat()
                removed.add(id(item))
            migrated = True
        nutrient_pairs = (
            ("calories_kcal", "total_kcal"), ("protein_g", "protein_g"),
            ("carbs_g", "carbs_g"), ("fat_g", "fat_g"),
        )
        for item in records:
            record = item.get("record")
            if (
                item.get("category") != "daily_checkin"
                or not isinstance(record, dict)
                or record.get("nutrition_source") != "agent_tool"
            ):
                continue
            meals = record.get("meal_estimates")
            if not isinstance(meals, list) or not meals:
                continue
            residual: dict[str, float] = {}
            for daily_field, meal_field in nutrient_pairs:
                total = record.get(daily_field)
                if not isinstance(total, (int, float)):
                    residual[daily_field] = 0.0
                    continue
                grouped = sum(
                    float(meal.get(meal_field) or 0)
                    for meal in meals if isinstance(meal, dict)
                )
                residual[daily_field] = round(float(total) - grouped, 1)
            if any(value < -0.1 for value in residual.values()) or not any(value > 0.1 for value in residual.values()):
                continue
            record["meal_estimates"] = [
                *meals,
                nutrition_estimate_from_totals(residual, source="text_nutrition"),
            ]
            item["revision"] = int(item.get("revision") or 1) + 1
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            migrated = True
        if removed:
            records[:] = [item for item in records if id(item) not in removed]
        return migrated

    def _write_all(self, records: list[dict[str, Any]]) -> None:
        # DATA-06：flush + fsync + replace，且 tmp 名带 pid+uuid。
        # 串行化由公开方法上的 self._write_lock + JsonFileLock 负责，
        # 这里刻意保持无锁，避免与调用方形成 JsonFileLock 嵌套（不可重入）。
        atomic_write_json(self.db_path, records)

    def add_record(
        self,
        date: str,
        category: str,
        record: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            if idempotency_key:
                existing = next(
                    (
                        item
                        for item in records
                        if item.get("idempotency_key") == idempotency_key
                    ),
                    None,
                )
                if existing is not None:
                    return {**existing, "idempotent_replay": True}
            item = {
                "id": str(uuid4()),
                "date": date,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "revision": 1,
                "record": record,
            }
            if idempotency_key:
                item["idempotency_key"] = idempotency_key
            records.append(item)
            self._write_all(records)
            return item

    def upsert_dated_record(
        self, date: str, category: str, record: dict[str, Any], *,
        clear_fields: tuple[str, ...] = (), additive_fields: tuple[str, ...] = (),
        append_fields: tuple[str, ...] = (),
    ) -> tuple[dict[str, Any], bool, int]:
        """按 (日期, 分类) 唯一化地写入一条记录，返回 (记录, 是否新建, 折叠掉的重复条数)。

        BUG-09：每日打卡原先只走 `add_record`，每次生成新 uuid 追加，同一天点两次
        保存就并列出两条 daily_checkin，而 `PATCH /data/checkins/{id}` 是前端零调用
        的死端点。

        **查重与写入必须在同一把锁内完成**——调用方先查再写的话，两个并发请求会
        同时判定"当日无记录"，各自追加一条，重复照旧（DATA-07 在 profile 上踩过
        同一个坑）。

        记录体按字段**合并**而不是整体替换：表单里留空的字段根本不会进
        `validate_daily_checkin` 的结果，早上记体重、晚上记热量是正常用法，
        整体替换会把早上那条抹掉。代价是无法把某个字段改回"空"，相比静默丢数据
        这是更可接受的一侧。

        磁盘上可能已经躺着旧缺陷留下的重复记录。这里把它们**折叠**成一条（旧→新
        依次合并，新值覆盖旧值，保留最早那条的 id 与 created_at），而不是删掉多余
        的那几条——折叠不丢任何字段值，且折叠条数原样返回，由调用方告诉用户。
        """
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            # 列表顺序即插入顺序，所以这就是时间顺序：越靠后越新。
            matches = [
                item
                for item in records
                if item.get("date") == date and item.get("category") == category
            ]
            if not matches:
                item = {
                    "id": str(uuid4()),
                    "date": date,
                    "category": category,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "revision": 1,
                    "record": record,
                }
                records.append(item)
                self._write_all(records)
                return item, True, 0

            merged: dict[str, Any] = {}
            for item in matches:
                existing = item.get("record")
                if isinstance(existing, dict):
                    merged.update(existing)
            for field, value in record.items():
                if field in append_fields and isinstance(value, list):
                    previous = merged.get(field)
                    merged[field] = [*(previous if isinstance(previous, list) else []), *value]
                elif field in additive_fields and isinstance(value, (int, float)):
                    previous = merged.get(field)
                    merged[field] = round(float(previous or 0) + float(value), 1)
                    if isinstance(value, int) and isinstance(previous, (int, type(None))):
                        merged[field] = int(round(merged[field]))
                else:
                    merged[field] = value
            for field in clear_fields:
                merged.pop(field, None)

            target = matches[0]
            target["record"] = merged
            target["revision"] = int(target.get("revision") or 1) + 1
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            duplicates = matches[1:]
            if duplicates:
                extra_ids = {item.get("id") for item in duplicates}
                records = [item for item in records if item.get("id") not in extra_ids]
            self._write_all(records)
            return target, False, len(duplicates)

    def query_records(self, date: str | None = None, limit: int = 7) -> list[dict[str, Any]]:
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            if date:
                filtered = [r for r in records if r.get("date") == date]
            else:
                filtered = records
            return filtered[-limit:]

    def list_records(self) -> list[dict[str, Any]]:
        with self._write_lock, JsonFileLock(self.db_path):
            return list(reversed(self._read_all()))

    def find_training_by_start(
        self, *, date: str, sport: str, start_time_beijing: str, tolerance_seconds: int = 60
    ) -> dict[str, Any] | None:
        """Find one previously saved training at the same local start time and sport."""
        try:
            target_start = datetime.fromisoformat(start_time_beijing)
        except ValueError:
            return None
        with self._write_lock, JsonFileLock(self.db_path):
            for item in self._read_all():
                if item.get("date") != date or item.get("category") == "daily_checkin":
                    continue
                record = item.get("record")
                if not isinstance(record, dict) or str(record.get("sport") or "") != sport:
                    continue
                saved_start = record.get("workout_start_time_beijing")
                if not isinstance(saved_start, str):
                    continue
                try:
                    difference = abs((datetime.fromisoformat(saved_start) - target_start).total_seconds())
                except ValueError:
                    continue
                if difference <= tolerance_seconds:
                    return item
        return None

    def delete_record(self, record_id: str) -> bool:
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            remaining = [item for item in records if item.get("id") != record_id]
            if len(remaining) == len(records):
                return False
            self._write_all(remaining)
            return True

    def update_record(self, record_id: str, *, date: str, category: str, record: dict[str, Any]) -> dict[str, Any] | None:
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            for item in records:
                if item.get("id") == record_id:
                    item["date"] = date
                    item["category"] = category
                    item["record"] = record
                    item["revision"] = int(item.get("revision") or 1) + 1
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._write_all(records)
                    return item
        return None

    def update_record_if_revision(
        self,
        record_id: str,
        *,
        expected_revision: int,
        date: str,
        category: str,
        record: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, bool]:
        """Update one record only when the client still holds its current revision.

        Returns ``(item, False)`` on success, ``(None, True)`` for a stale revision,
        and ``(None, False)`` when the record no longer exists.
        """
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            for item in records:
                if item.get("id") != record_id:
                    continue
                if item.get("revision") != expected_revision:
                    return None, True
                item["date"] = date
                item["category"] = category
                item["record"] = record
                item["revision"] = expected_revision + 1
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_all(records)
                return item, False
        return None, False

    def delete_records(self, record_ids: list[str]) -> int:
        wanted = set(record_ids)
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            remaining = [item for item in records if item.get("id") not in wanted]
            removed = len(records) - len(remaining)
            if removed:
                self._write_all(remaining)
            return removed

    def clear(self) -> int:
        with self._write_lock, JsonFileLock(self.db_path):
            records = self._read_all()
            self._write_all([])
            return len(records)


class UserProfileStore:
    """用户档案存储。

    DATA-07：这个 store 原先**完全无锁**，临时文件名还是固定的
    `user_profile.json.tmp`——两个并发 PATCH 会同时 `open("w")` 同一个 tmp，
    交错写入后 replace 出去的是两份 JSON 拼在一起的垃圾。而 `update_profile`
    本身是典型的 read-modify-write，即使不产出垃圾也会丢更新。

    修法与 `DailyRecordStore` 保持一致：
    * 所有**公开**方法（读和写都算）套 `RLock` + `JsonFileLock`——进程内靠
      RLock，跨进程（uvicorn 多 worker、脚本与服务并行）靠文件锁；
    * `_read` / `_write` 等私有方法刻意保持无锁。`JsonFileLock` 每次进入都
      新开一个句柄，**不可重入**，在私有方法里再套一层会直接死锁；
    * read-modify-write 整段收在同一把锁内，所以"读到的档案"和"写回去的
      档案"之间不存在其他写入者。
    """

    DEFAULT_EQUIPMENT = PROFILE_DEFAULT_EQUIPMENT
    REQUIRED_FIELDS = ("weekly_weight_kg", "height_cm", "birth_date", "sex", "goal")

    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or data_path("user_profile.json")
        self._write_lock = RLock()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.profile_path.exists():
            # 双重检查：拿到锁之后再看一次，避免两个实例同时初始化时
            # 后来者把前者刚写好的档案覆盖成默认值。
            with self._write_lock, JsonFileLock(self.profile_path):
                if not self.profile_path.exists():
                    self._write(self._default_profile())

    def _default_profile(self) -> dict[str, Any]:
        return {
            "weekly_weight_kg": [],
            "height_cm": None,
            "birth_date": None,
            "sex": None,
            "equipment": self.DEFAULT_EQUIPMENT.copy(),
            "goal": None,
        }

    def _read(self) -> dict[str, Any]:
        content = self.profile_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("user_profile.json 必须是对象格式。")
        return data

    def _write(self, profile: dict[str, Any]) -> None:
        # DATA-06 + DATA-07：flush + fsync + replace，且 tmp 名带 pid+uuid。
        atomic_write_json(self.profile_path, profile)

    def _normalized_profile(self) -> dict[str, Any]:
        """读盘并补齐默认值。无锁——调用方必须已经持有锁。"""
        profile = self._default_profile()
        profile.update(self._read())
        equipment = profile.get("equipment")
        # An empty list is meaningful: the user may explicitly remove every
        # available item and train with bodyweight only.
        if not isinstance(equipment, list):
            profile["equipment"] = self.DEFAULT_EQUIPMENT.copy()
        return profile

    def get_profile(self) -> dict[str, Any]:
        with self._write_lock, JsonFileLock(self.profile_path):
            return self._normalized_profile()

    def update_profile(
        self,
        updates: dict[str, Any],
        *,
        merge: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """在锁内完成 read-modify-write。

        `merge(现有档案, 传入的 updates) -> 实际要落盘的 updates` 用于追加式
        字段（例如器械列表要跟现有值求并集）。这类合并**必须**在锁内拿到的
        档案上做：调用方先 `get_profile()` 再 `update_profile()` 的话，两个
        并发请求会读到同一份旧档案，其中一个的追加内容直接丢失。
        """
        with self._write_lock, JsonFileLock(self.profile_path):
            profile = self._normalized_profile()
            effective = merge(profile, updates) if merge is not None else updates
            for key, value in effective.items():
                profile[key] = value
            self._write(profile)
            return profile

    def reset(self) -> dict[str, Any]:
        with self._write_lock, JsonFileLock(self.profile_path):
            profile = self._default_profile()
            self._write(profile)
            return profile

    def is_complete(self, profile: dict[str, Any] | None = None) -> bool:
        target = profile or self.get_profile()
        for field in self.REQUIRED_FIELDS:
            value = target.get(field)
            if value is None:
                return False
            if field == "weekly_weight_kg" and (not isinstance(value, list) or not value):
                return False
        return True

    def missing_fields(self, profile: dict[str, Any] | None = None) -> list[str]:
        target = profile or self.get_profile()
        missing: list[str] = []
        for field in self.REQUIRED_FIELDS:
            value = target.get(field)
            if value is None:
                missing.append(field)
            elif field == "weekly_weight_kg" and (not isinstance(value, list) or not value):
                missing.append(field)
        return missing
