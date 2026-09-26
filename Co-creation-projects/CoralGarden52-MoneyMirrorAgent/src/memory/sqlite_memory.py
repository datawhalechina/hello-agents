"""Small, explicit SQLite-backed long-term memory.

The database is local by design: personal financial data should not leave the
user's machine just to power a dashboard demo.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..models import Goal, Quest


class SQLiteMemory:
    def __init__(self, path: str | Path = "outputs/moneymirror.db", user_id: str = "local_user") -> None:
        self.path = str(path)
        self.user_id = user_id
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS merchant_categories (
                user_id TEXT NOT NULL, merchant TEXT NOT NULL, category TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, merchant)
            );
            CREATE TABLE IF NOT EXISTS goals (
                user_id TEXT NOT NULL, goal_id TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, goal_id)
            );
            CREATE TABLE IF NOT EXISTS budgets (
                user_id TEXT NOT NULL, month TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, month)
            );
            CREATE TABLE IF NOT EXISTS quests (
                user_id TEXT NOT NULL, quest_id TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, quest_id)
            );
            CREATE TABLE IF NOT EXISTS achievements (
                user_id TEXT NOT NULL, achievement_key TEXT NOT NULL, payload TEXT NOT NULL,
                unlocked_at TEXT NOT NULL, PRIMARY KEY (user_id, achievement_key)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                user_id TEXT NOT NULL, month TEXT NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY (user_id, month)
            );
            CREATE TABLE IF NOT EXISTS reflections (
                user_id TEXT NOT NULL, month TEXT NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY (user_id, month)
            );
            CREATE TABLE IF NOT EXISTS preferences (
                user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, key)
            );
            """
        )
        self.connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def set_merchant_category(self, merchant: str, category: str) -> None:
        self.connection.execute(
            "INSERT INTO merchant_categories VALUES (?, ?, ?, ?) ON CONFLICT(user_id, merchant) DO UPDATE SET category=excluded.category, updated_at=excluded.updated_at",
            (self.user_id, merchant.strip(), category, self._now()),
        )
        self.connection.commit()

    def get_merchant_category(self, merchant: str) -> str | None:
        row = self.connection.execute("SELECT category FROM merchant_categories WHERE user_id=? AND merchant=?", (self.user_id, merchant.strip())).fetchone()
        return row["category"] if row else None

    def merchant_categories(self) -> dict[str, str]:
        rows = self.connection.execute("SELECT merchant, category FROM merchant_categories WHERE user_id=?", (self.user_id,)).fetchall()
        return {row["merchant"]: row["category"] for row in rows}

    def save_goal(self, goal: Goal | dict[str, Any]) -> None:
        payload = goal.to_dict() if isinstance(goal, Goal) else goal
        self._upsert_payload("goals", "goal_id", payload["goal_id"], payload)

    def list_goals(self, active_only: bool = False) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT payload FROM goals WHERE user_id=? ORDER BY updated_at", (self.user_id,)).fetchall()
        values = [json.loads(row["payload"]) for row in rows]
        return [value for value in values if value.get("active", True)] if active_only else values

    def save_budget(self, month: str, budget: dict[str, Any]) -> None:
        self._upsert_payload("budgets", "month", month, budget)

    def get_budget(self, month: str) -> dict[str, Any] | None:
        return self._get_payload("budgets", "month", month)

    def save_quest(self, quest: Quest | dict[str, Any]) -> None:
        payload = quest.to_dict() if isinstance(quest, Quest) else quest
        self._upsert_payload("quests", "quest_id", payload["quest_id"], payload)

    def list_quests(self, active_only: bool = False) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT payload FROM quests WHERE user_id=? ORDER BY updated_at", (self.user_id,)).fetchall()
        values = [json.loads(row["payload"]) for row in rows]
        return [value for value in values if value.get("status") == "active"] if active_only else values

    def save_achievement(self, achievement: dict[str, Any]) -> None:
        self._upsert_payload("achievements", "achievement_key", achievement["key"], achievement, timestamp_column="unlocked_at")

    def list_achievements(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT payload FROM achievements WHERE user_id=? ORDER BY unlocked_at", (self.user_id,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_snapshot(self, month: str, snapshot: dict[str, Any]) -> None:
        self._upsert_payload("snapshots", "month", month, snapshot, timestamp_column="created_at")

    def get_snapshot(self, month: str) -> dict[str, Any] | None:
        return self._get_payload("snapshots", "month", month)

    def list_snapshots(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT month, payload FROM snapshots WHERE user_id=? ORDER BY month", (self.user_id,)).fetchall()
        return [{"month": row["month"], **json.loads(row["payload"])} for row in rows]

    def save_reflection(self, month: str, reflection: dict[str, Any]) -> None:
        self._upsert_payload("reflections", "month", month, reflection, timestamp_column="created_at")

    def get_reflection(self, month: str) -> dict[str, Any] | None:
        return self._get_payload("reflections", "month", month)

    def list_reflections(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT month, payload FROM reflections WHERE user_id=? ORDER BY month", (self.user_id,)).fetchall()
        return [{"month": row["month"], **json.loads(row["payload"])} for row in rows]

    def set_preference(self, key: str, value: Any) -> None:
        self.connection.execute(
            "INSERT INTO preferences VALUES (?, ?, ?, ?) ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (self.user_id, key, json.dumps(value, ensure_ascii=False), self._now()),
        )
        self.connection.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        row = self.connection.execute("SELECT value FROM preferences WHERE user_id=? AND key=?", (self.user_id, key)).fetchone()
        return json.loads(row["value"]) if row else default

    def _upsert_payload(self, table: str, key_column: str, key: str, payload: dict[str, Any], timestamp_column: str = "updated_at") -> None:
        columns = f"user_id, {key_column}, payload, {timestamp_column}"
        self.connection.execute(
            f"INSERT INTO {table} ({columns}) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, {key_column}) DO UPDATE SET payload=excluded.payload, {timestamp_column}=excluded.{timestamp_column}",
            (self.user_id, key, json.dumps(payload, ensure_ascii=False), self._now()),
        )
        self.connection.commit()

    def _get_payload(self, table: str, key_column: str, key: str) -> dict[str, Any] | None:
        row = self.connection.execute(f"SELECT payload FROM {table} WHERE user_id=? AND {key_column}=?", (self.user_id, key)).fetchone()
        return json.loads(row["payload"]) if row else None
