"""info_store.py

本地对话摘要存储，支持 3 天 TTL 自动清理。

存储格式（data/info_store.json）：
[
  {
    "id": "<ISO 时间戳>",
    "summary": "结构化摘要文本",
    "metadata": {"reason": "..."},
    "created_at": "<ISO>",
    "expires_at": "<ISO>"
  },
  ...
]
"""

from __future__ import annotations

import json
import logging
import hashlib
import os
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fithealth_agent.atomic_json import atomic_write_json
from fithealth_agent.json_file_lock import JsonFileLock
from fithealth_agent.muscle_map import muscle_ids_for_text, regions_for_text
from fithealth_agent.settings import data_path


logger = logging.getLogger(__name__)


class MemoryStoreDegradedError(RuntimeError):
    """记忆库文件不可解析，已进入只读降级；写入被拒绝以免覆盖原始内容。

    这是 DATA-08 的核心防线：原实现 `except Exception: data = []` 会让任何一次
    后续写入把整个记忆库永久覆盖。现在读失败必须显式暴露，绝不伪装成空库。
    """

    def __init__(self, message: str, quarantine_path: Path | None = None) -> None:
        super().__init__(message)
        self.quarantine_path = quarantine_path


MEMORY_TYPES = {"preference", "constraint", "plan_decision", "training_feedback"}
DEFAULT_MEMORY_TYPE = "training_feedback"

# Facts are deliberately a small, closed vocabulary.  Summaries remain useful
# for the model, but only these facts may drive deterministic product behaviour.
FACT_DEFINITIONS: dict[tuple[str, str], dict[str, object]] = {
    ("youtube", "avoid_channel"): {"polarity": "avoid"},
    ("training", "avoid_exercise"): {"polarity": "avoid"},
    ("training", "prefer_exercise"): {"polarity": "prefer"},
    ("training", "max_rpe"): {"polarity": "limit", "numeric": True, "minimum": 1, "maximum": 10},
    ("training", "max_sets_per_exercise"): {"polarity": "limit", "numeric": True, "minimum": 1, "maximum": 20},
    ("training", "max_total_sets"): {"polarity": "limit", "numeric": True, "minimum": 1, "maximum": 100},
    ("training", "required_plan_elements"): {"polarity": "require"},
    ("health", "injury_or_constraint"): {"polarity": "limit"},
    ("health", "recovery_status"): {"polarity": "temporary"},
    ("plan", "preference"): {"polarity": "note"},
    ("plan", "decision"): {"polarity": "note"},
    ("plan", "weekly_schedule"): {"polarity": "schedule"},
}
FACT_STATUS = {"active", "cleared", "rejected"}
_NEGATIVE_PREFERENCE_PATTERN = re.compile(
    r"(?:不喜欢|不想|不要|不做|不练|不安排|不建议|讨厌|避免|排斥|禁(?:止)?|别(?:再)?)"
)

# Canonical vocabulary for posture and muscle-condition facts.  The map is
# intentionally narrow: these values drive safety context and plan adjustments,
# so equivalent user wording must not create independent long-term facts.
BODY_POSTURE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "长期久坐": (
        "久坐", "久坐人群", "久坐族", "长时间坐着", "办公室久坐",
        "sedentary", "long term sitting", "long_term_sedentary",
    ),
    "骨盆前倾": (
        "盆骨前倾", "骨盆前倾问题", "盆骨前顷", "假翘臀", "塌腰", "塌腰凸肚",
        "小腹前凸", "鸭子步体态", "Anterior Pelvic Tilt",
    ),
    "骨盆后倾": (
        "盆骨后倾", "骨盆后移", "驼背塌臀", "折叠腰", "Posterior Pelvic Tilt",
    ),
    "下交叉综合征": (
        "下交叉症候群", "下交叉", "骨盆交叉综合征", "Lower Crossed Syndrome",
    ),
    "臀肌无力": (
        "臀大肌无力", "臀肌失忆症", "死臀综合征", "屁股塌陷", "扁平臀", "Gluteal Amnesia",
    ),
    "髂腰肌紧张": ("屈髋肌紧张", "髂腰肌僵硬", "髂腰肌缩短", "髋部前侧紧绷"),
    "腹部核心薄弱": ("核心无力", "核心不稳", "腹肌无力", "腹横肌松弛", "核心力量差"),
    "腘绳肌紧张": ("大腿后侧紧张", "大腿后侧僵硬", "腘绳肌缩短"),
    "竖脊肌紧张": ("下背部紧张", "下背痛", "腰部僵硬", "腰肌劳损"),
    "体态矫正": ("不良体态改善", "姿势矫正", "身姿纠正", "体态调整", "Posture Correction"),
}
_BODY_POSTURE_CANONICAL_FACTS = {
    ("health", "injury_or_constraint"),
    ("health", "recovery_status"),
    ("plan", "preference"),
}


def _compact_canonical_text(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


_BODY_POSTURE_LOOKUP = tuple(
    (canonical, _compact_canonical_text(term))
    for canonical, aliases in BODY_POSTURE_SYNONYMS.items()
    for term in (canonical, *aliases)
)


def canonicalize_body_posture_value(value: object) -> list[str]:
    """Return every posture/muscle condition represented by ``value``."""
    if not isinstance(value, str):
        return []
    compact = _compact_canonical_text(value)
    matches = [
        canonical
        for canonical, term in _BODY_POSTURE_LOOKUP
        if term and term in compact
    ]
    unique_matches = list(dict.fromkeys(matches))
    return unique_matches or [value]
FACT_VERSION_SINGLETON_KEYS = {
    ("plan", "weekly_schedule"),
    ("training", "max_rpe"),
    ("training", "max_sets_per_exercise"),
    ("training", "max_total_sets"),
}
FACT_CONFLICT_PAIRS = {
    ("training", "avoid_exercise"): ("training", "prefer_exercise"),
    ("training", "prefer_exercise"): ("training", "avoid_exercise"),
}


def is_negative_preference_value(value: object) -> bool:
    """Whether a supposed preferred exercise is phrased as an avoidance."""
    return isinstance(value, str) and bool(_NEGATIVE_PREFERENCE_PATTERN.search(value))


class MemoryConflictError(ValueError):
    """A pending fact was based on an older confirmed fact version."""

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
RETENTION_DAYS = {
    "permanent": None,
    "long_term": None,
    "medium": 30,
    "short": 7,
    "temporary": 3,
}
FACT_DURATION_TYPES = {"temporary", "long_term", "permanent"}
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")


def fact_retention_class(fact: dict[str, object]) -> str:
    namespace = fact.get("namespace")
    key = fact.get("key")
    if (namespace, key) in {
        ("health", "injury_or_constraint"),
        ("plan", "weekly_schedule"),
        ("plan", "decision"),
    }:
        return "long_term"
    if (namespace, key) == ("health", "recovery_status"):
        return "short"
    if namespace in {"youtube", "training"} or (namespace, key) == ("plan", "preference"):
        return "medium"
    return "temporary"


def memory_retention_class(memory_type: str, facts: list[dict[str, object]] | None) -> str:
    normalized = facts if isinstance(facts, list) else []
    classes = {fact_retention_class(fact) for fact in normalized if isinstance(fact, dict)}
    if "long_term" in classes:
        return "long_term"
    if "medium" in classes:
        return "medium"
    if memory_type == "training_feedback":
        return "short"
    if memory_type in {"constraint", "plan_decision"}:
        return "long_term"
    if memory_type == "preference":
        return "medium"
    return "temporary"


def retention_expiry(created_at: datetime, memory_type: str, facts: list[dict[str, object]]) -> datetime | None:
    retention = memory_retention_class(memory_type, facts)
    days = RETENTION_DAYS[retention]
    return None if days is None else created_at + timedelta(days=days)


def entry_expiry_for_facts(
    created_at: datetime,
    memory_type: str,
    facts: list[dict[str, object]],
) -> datetime | None:
    """Keep the container alive for as long as any contained fact can be active."""
    if not facts:
        return retention_expiry(created_at, memory_type, facts)
    expiries: list[datetime] = []
    for fact in facts:
        expires_at = fact.get("expires_at")
        if expires_at is None:
            return None
        try:
            expiries.append(datetime.fromisoformat(str(expires_at)).astimezone(timezone.utc))
        except ValueError:
            continue
    return max(expiries) if expiries else retention_expiry(created_at, memory_type, facts)


def apply_fact_retention(facts: list[dict[str, object]], created_at: datetime) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for fact in facts:
        copy = dict(fact)
        if copy.get("duration_type") == "temporary":
            local_created = created_at.astimezone(LOCAL_TIMEZONE)
            copy.setdefault("valid_from", local_created.date().isoformat())
            copy.setdefault("valid_until", (local_created + timedelta(days=7)).date().isoformat())
        retention = fact_retention_class(copy)
        days = RETENTION_DAYS[retention]
        copy["retention_class"] = retention
        if copy.get("duration_type") == "temporary" and copy.get("valid_until"):
            valid_until = date.fromisoformat(str(copy["valid_until"]))
            copy["expires_at"] = datetime.combine(
                valid_until + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
            ).isoformat()
        else:
            copy["expires_at"] = None if days is None else (created_at + timedelta(days=days)).isoformat()
        enriched.append(copy)
    return enriched


def fact_is_active(fact: dict[str, object], now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    today = current.astimezone(LOCAL_TIMEZONE).date()
    try:
        if fact.get("valid_from") and date.fromisoformat(str(fact["valid_from"])) > today:
            return False
        if fact.get("valid_until") and date.fromisoformat(str(fact["valid_until"])) < today:
            return False
    except ValueError:
        return False
    expires_at = fact.get("expires_at")
    if not expires_at:
        return True
    try:
        expiry = datetime.fromisoformat(str(expires_at)).astimezone(timezone.utc)
    except ValueError:
        return False
    return expiry > current

SCHEDULE_DAY_TYPES = {"training", "aerobic", "rest"}


def _schedule_subject(value: object, *, default: str = "") -> str | None:
    if value is None and default:
        return default
    if not isinstance(value, str):
        return None
    subject = " ".join(value.split()).strip()[:40]
    return subject or None


def _schedule_date(value: object) -> str | None | object:
    """Return a canonical ISO date, None for an omitted field, or a sentinel on error."""
    if value is None:
        return None
    if not isinstance(value, str):
        return _INVALID_SCHEDULE_VALUE
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return _INVALID_SCHEDULE_VALUE


_INVALID_SCHEDULE_VALUE = object()


def parse_weekly_schedule(value: object) -> dict[str, object] | None:
    """Parse legacy and structured weekly schedules into one canonical schema.

    Legacy values such as ``{"mon":"胸部训练"}`` remain valid.  New values use
    ``{"enabled": true, "days": {"wed": {"type": "rest"}}}`` and may set an
    inclusive effective date range.  Canonicalising here keeps every consumer
    from interpreting rest days or inactive schedules differently.
    """
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return None
    else:
        raw = value
    if not isinstance(raw, dict) or not raw:
        return None

    invalid_days: list[str] = []
    legacy = all(weekday in WEEKDAY_KEYS for weekday in raw)
    if legacy:
        raw_days = raw
        enabled = True
        effective_from = None
        effective_until = None
    else:
        mixed_legacy = "days" not in raw and any(key in WEEKDAY_KEYS for key in raw)
        if mixed_legacy:
            # A partly translated legacy object is still useful. Keep valid
            # canonical weekdays and expose every skipped key for confirmation.
            raw_days = raw
            enabled = True
            effective_from = None
            effective_until = None
        else:
            # Ignore unknown metadata keys and salvage valid entries in days.
            raw_days = raw.get("days")
            enabled = raw.get("enabled", True)
            effective_from = _schedule_date(raw.get("effective_from"))
            effective_until = _schedule_date(raw.get("effective_until"))
            reported_invalid = raw.get("invalid_days", [])
            if isinstance(reported_invalid, list):
                invalid_days.extend(
                    str(item) for item in reported_invalid
                    if isinstance(item, str) and item.strip()
                )
        if (
            not isinstance(raw_days, dict)
            or not raw_days
            or not isinstance(enabled, bool)
            or effective_from is _INVALID_SCHEDULE_VALUE
            or effective_until is _INVALID_SCHEDULE_VALUE
        ):
            return None
        if effective_from and effective_until and effective_until < effective_from:
            return None

    days: dict[str, dict[str, str]] = {}
    for weekday, raw_day in raw_days.items():
        if weekday not in WEEKDAY_KEYS:
            invalid_days.append(str(weekday))
            continue
        if raw_day is None:
            days[weekday] = {"type": "rest"}
            continue
        if isinstance(raw_day, str):
            subject = _schedule_subject(raw_day)
            if subject is None:
                invalid_days.append(weekday)
                continue
            days[weekday] = {"type": "training", "subject": subject}
            continue
        if not isinstance(raw_day, dict) or set(raw_day) - {"type", "subject"}:
            invalid_days.append(weekday)
            continue
        day_type = raw_day.get("type")
        if day_type not in SCHEDULE_DAY_TYPES:
            invalid_days.append(weekday)
            continue
        if day_type == "rest":
            days[weekday] = {"type": "rest"}
            continue
        subject = _schedule_subject(
            raw_day.get("subject"), default="有氧训练" if day_type == "aerobic" else ""
        )
        if subject is None:
            invalid_days.append(weekday)
            continue
        days[weekday] = {"type": day_type, "subject": subject}

    if not days:
        return None

    schedule: dict[str, object] = {"enabled": enabled, "days": days}
    if invalid_days:
        schedule["invalid_days"] = list(dict.fromkeys(invalid_days))
    if effective_from:
        schedule["effective_from"] = effective_from
    if effective_until:
        schedule["effective_until"] = effective_until
    return schedule


def normalize_weekly_schedule(value: object) -> str | None:
    """Validate a weekly schedule and return its canonical structured JSON form."""
    schedule = parse_weekly_schedule(value)
    if schedule is None:
        return None
    return json.dumps(schedule, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def weekly_schedule_entry_for_date(
    value: object,
    requested_day: date,
) -> dict[str, str] | None:
    """Return the enabled, in-range entry for one date, if its schedule has one."""
    schedule = parse_weekly_schedule(value)
    if schedule is None or not schedule["enabled"]:
        return None
    effective_from = schedule.get("effective_from")
    effective_until = schedule.get("effective_until")
    if effective_from and requested_day < date.fromisoformat(str(effective_from)):
        return None
    if effective_until and requested_day > date.fromisoformat(str(effective_until)):
        return None
    days = schedule["days"]
    assert isinstance(days, dict)
    entry = days.get(WEEKDAY_KEYS[requested_day.weekday()])
    return dict(entry) if isinstance(entry, dict) else None


def fact_identity_id(namespace: object, key: object, value_key: object) -> str:
    """给一条事实算一个稳定的寻址 id（BUG-12）。

    为什么用内容摘要而不是随机 uuid：事实原本靠**列表下标**寻址，而每次
    `/chat` 都会 `cleanup_expired` 物理删除过期事实、`reject_fact` 也会 pop
    移位，于是老页面点"确认/拒绝/编辑"会作用到另一条事实。改成随机 id 需要
    一次数据迁移，而且在迁移落盘之前每次读取都会生成不同的 id；内容摘要则
    **对存量数据天然稳定**，无需迁移、无需写盘就能算出同一个 id。

    id 只需在一条记忆条目内唯一（寻址总是 entry_id + fact_id 成对使用），而
    `normalize_memory_facts` 已经按 (namespace, key, value) 去重，所以同一条目
    内不会重复。编辑事实会改变 value，因此 id 随之变化——这是预期行为：值变了
    就是另一条事实，前端会拿到新的 id。
    """
    raw = "\x1f".join((str(namespace), str(key), str(value_key)))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_memory_facts(raw_facts: Any) -> list[dict[str, object]]:
    """Validate model-provided facts before they become persistent state."""
    if not isinstance(raw_facts, list):
        return []
    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_fact in raw_facts[:8]:
        if not isinstance(raw_fact, dict):
            continue
        namespace = raw_fact.get("namespace")
        key = raw_fact.get("key")
        definition = FACT_DEFINITIONS.get((namespace, key))
        if definition is None:
            continue
        status = raw_fact.get("status", "active")
        if status not in FACT_STATUS:
            continue
        value = raw_fact.get("value")
        if (namespace, key) == ("plan", "weekly_schedule"):
            normalized_value = normalize_weekly_schedule(value)
            if normalized_value is None:
                continue
            value_key = normalized_value
        elif definition.get("numeric"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(definition.get("minimum", 1)) <= value <= float(definition.get("maximum", 10)):
                continue
            normalized_value: object = float(value) if isinstance(value, float) else value
            value_key = str(normalized_value)
        else:
            if not isinstance(value, str):
                continue
            normalized_value = " ".join(value.split()).strip()[:120]
            if not normalized_value:
                continue
            if (namespace, key) in _BODY_POSTURE_CANONICAL_FACTS:
                canonical_values = canonicalize_body_posture_value(normalized_value)
                if len(canonical_values) > 1:
                    for canonical_value in canonical_values:
                        expanded_fact = dict(raw_fact)
                        expanded_fact["value"] = canonical_value
                        for fact in normalize_memory_facts([expanded_fact]):
                            identity = (
                                str(fact["namespace"]),
                                str(fact["key"]),
                                str(fact["value"]).casefold(),
                            )
                            if identity not in seen:
                                seen.add(identity)
                                normalized.append(fact)
                    continue
                normalized_value = canonical_values[0]
            if (namespace, key) == ("training", "prefer_exercise") and is_negative_preference_value(normalized_value):
                continue
            value_key = normalized_value.casefold()
        identity = (namespace, key, value_key)
        if identity in seen:
            continue
        seen.add(identity)
        scope = raw_fact.get("scope")
        if scope not in {"current_turn", "current_session", "date", "date_range", "long_term"}:
            scope = "date" if (namespace, key) == ("health", "recovery_status") else "long_term"
        duration_type = raw_fact.get("duration_type")
        if duration_type not in FACT_DURATION_TYPES:
            duration_type = (
                "temporary"
                if (namespace, key) == ("health", "recovery_status")
                or scope in {"current_turn", "current_session", "date", "date_range"}
                else "long_term"
            )
        valid_from = raw_fact.get("valid_from")
        valid_until = raw_fact.get("valid_until")
        try:
            start_date = date.fromisoformat(valid_from) if isinstance(valid_from, str) else None
            end_date = date.fromisoformat(valid_until) if isinstance(valid_until, str) else None
        except ValueError:
            continue
        if start_date and end_date and end_date < start_date:
            continue
        if duration_type != "temporary":
            valid_until = None
        normalized.append(
            {
                "namespace": namespace,
                "key": key,
                # 稳定寻址 id（BUG-12）。始终重算而不是沿用传入值：确定性算法下
                # 重算是幂等的，也能顺手修好任何被手改坏的 id。
                "fact_id": fact_identity_id(namespace, key, value_key),
                "value": normalized_value,
                "polarity": definition["polarity"],
                "status": status,
                "confidence": "explicit",
                "source": "user_statement",
                "evidence": raw_fact.get("evidence") if isinstance(raw_fact.get("evidence"), str) else "",
                "priority_class": raw_fact.get("priority_class") if raw_fact.get("priority_class") in {"safety", "current", "temporary", "schedule", "goal", "preference", "history"} else ("safety" if namespace == "health" else "schedule" if (namespace, key) == ("plan", "weekly_schedule") else "preference"),
                "scope": scope,
                "duration_type": duration_type,
                **({"valid_from": valid_from} if isinstance(valid_from, str) else {}),
                **({"valid_until": valid_until} if isinstance(valid_until, str) else {}),
                **({"version": raw_fact["version"]} if isinstance(raw_fact.get("version"), int) else {}),
                **({"base_version": raw_fact["base_version"]} if isinstance(raw_fact.get("base_version"), int) else {}),
                **({"user_confirmed": raw_fact["user_confirmed"]} if isinstance(raw_fact.get("user_confirmed"), bool) else {}),
                **({"retention_class": raw_fact["retention_class"]} if raw_fact.get("retention_class") in RETENTION_DAYS else {}),
                **({"expires_at": raw_fact["expires_at"]} if "expires_at" in raw_fact and (raw_fact.get("expires_at") is None or isinstance(raw_fact.get("expires_at"), str)) else {}),
                **({"rejected_at": raw_fact["rejected_at"]} if isinstance(raw_fact.get("rejected_at"), str) else {}),
                **({"cleared_at": raw_fact["cleared_at"][:64]} if isinstance(raw_fact.get("cleared_at"), str) else {}),
                **({"clear_reason": raw_fact["clear_reason"][:200]} if isinstance(raw_fact.get("clear_reason"), str) else {}),
                **({"previous_value": raw_fact["previous_value"]} if isinstance(raw_fact.get("previous_value"), (str, int, float, dict, list)) and not isinstance(raw_fact.get("previous_value"), bool) else {}),
                **({
                    "history": [
                        {
                            key: value[:500] if isinstance(value, str) else value
                            for key, value in item.items()
                            if key in {"action", "value", "evidence", "version", "changed_at", "at"}
                            and isinstance(value, (str, int, float, dict, list))
                            and not isinstance(value, bool)
                        }
                        for item in raw_fact["history"][-20:]
                        if isinstance(item, dict)
                    ]
                } if isinstance(raw_fact.get("history"), list) else {}),
                **({
                    "usage_log": [
                        {
                            key: value[:500]
                            for key, value in item.items()
                            if key in {"at", "action", "detail", "request_id"} and isinstance(value, str)
                        }
                        for item in raw_fact["usage_log"][-50:]
                        if isinstance(item, dict)
                    ]
                } if isinstance(raw_fact.get("usage_log"), list) else {}),
            }
        )
    return normalized


def _recovery_fact_targets(fact: dict[str, object]) -> tuple[frozenset[str], frozenset[str]]:
    text = " ".join((str(fact.get("value") or ""), str(fact.get("evidence") or "")))
    regions = frozenset(regions_for_text(text, include_secondary=False))
    muscle_ids = frozenset(
        muscle_id
        for region in regions
        for muscle_id in muscle_ids_for_text(region, text)
    )
    return regions, muscle_ids


def _same_recovery_target(left: dict[str, object], right: dict[str, object]) -> bool:
    left_regions, left_muscles = _recovery_fact_targets(left)
    right_regions, right_muscles = _recovery_fact_targets(right)
    if left_muscles and right_muscles:
        return bool(left_muscles & right_muscles)
    return bool(left_regions & right_regions)


def resolve_confirmed_memory_facts(memories: list[dict[str, Any]] | None) -> list[dict[str, object]]:
    """Merge confirmed facts; newer statements override or clear prior ones."""
    if not isinstance(memories, list):
        return []
    resolved: dict[tuple[str, str, str], dict[str, object]] = {}
    for memory in sorted(
        (item for item in memories if isinstance(item, dict)),
        key=lambda item: item.get("created_at", ""),
    ):
        for fact in normalize_memory_facts(memory.get("facts")):
            if fact.get("status") not in {"active", "cleared"} or not fact_is_active(fact) or not fact.get("user_confirmed", bool(memory.get("user_confirmed"))):
                continue
            namespace = str(fact["namespace"])
            key = str(fact["key"])
            value = fact["value"]
            # Singleton facts replace their previous value; a weekly schedule is
            # a complete map rather than independent free-text preferences.
            if (namespace, key) in {("training", "max_rpe"), ("training", "max_sets_per_exercise"), ("training", "max_total_sets"), ("plan", "weekly_schedule")}:
                for existing in list(resolved):
                    if existing[:2] == (namespace, key):
                        resolved.pop(existing)
            identity = (namespace, key, str(value).casefold())
            counterpart = FACT_CONFLICT_PAIRS.get((namespace, key))
            if counterpart:
                for existing in list(resolved):
                    if existing[:2] == counterpart and existing[2] == str(value).casefold():
                        resolved.pop(existing)
            if (namespace, key) == ("health", "recovery_status"):
                for existing_identity, existing_fact in list(resolved.items()):
                    if (
                        existing_identity[:2] == (namespace, key)
                        and _same_recovery_target(existing_fact, fact)
                    ):
                        resolved.pop(existing_identity)
            if fact["status"] == "cleared":
                resolved.pop(identity, None)
            else:
                resolved[identity] = fact
    return list(resolved.values())


class InfoStore:
    """本地 JSON 文件持久化存储，保存 LLM 提炼的对话摘要，TTL = 3天。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_path("info_store.json")
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 只读降级状态（DATA-08）。一旦置位，所有写入都会抛
        # MemoryStoreDegradedError，直到用户修好文件并调用 revalidate()。
        self._degraded_reason: str | None = None
        self._quarantine_path: Path | None = None
        # 单条解析失败的原始条目：不参与业务逻辑，但会在每次写入时原样带回，
        # 避免"一条坏记录导致其余记忆被裁掉后永久丢失"。
        self._unreadable_entries: list[Any] = []
        if not self.path.exists():
            with self._lock, JsonFileLock(self.path):
                if not self.path.exists():
                    self._write_all([], allow_empty=True)

    # ------------------------------------------------------------------
    # 内部 I/O
    # ------------------------------------------------------------------

    def _enter_readonly_degraded(self, reason: str) -> None:
        """隔离一份副本并进入只读降级。

        用 copy 而不是 move —— 原文件留在原处，用户可以直接修；
        这也是 DATA-05 里"隔离即等于丢失"那个教训的反面做法。
        """
        if self._degraded_reason is not None:
            return
        target: Path | None = None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        candidate = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        try:
            if self.path.exists():
                shutil.copy2(self.path, candidate)
                target = candidate
        except OSError as exc:  # noqa: BLE001 - 隔离失败不能反过来阻断降级
            logger.error("记忆库隔离副本写入失败：%s", exc)
        self._degraded_reason = reason
        self._quarantine_path = target
        logger.error(
            "记忆库进入只读降级：%s（隔离副本：%s）。写入已被拒绝，记忆不会被覆盖。",
            reason,
            target or "无",
        )

    def revalidate(self) -> bool:
        """用户修好文件后重新尝试加载；成功则解除只读降级。"""
        with self._lock, JsonFileLock(self.path):
            self._degraded_reason = None
            self._quarantine_path = None
            self._unreadable_entries = []
            self._read_all()
            return self._degraded_reason is None

    def storage_status(self) -> dict[str, Any]:
        with self._lock, JsonFileLock(self.path):
            if self._degraded_reason is None:
                self._read_all()
            return {
                "available": self._degraded_reason is None,
                "degraded_reason": self._degraded_reason,
                "quarantine_path": str(self._quarantine_path) if self._quarantine_path else None,
                "unreadable_entries": len(self._unreadable_entries),
            }

    @staticmethod
    def _parse_utc(raw: object) -> datetime | None:
        try:
            return datetime.fromisoformat(str(raw)).astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    def _normalize_entry(self, item: Any) -> dict[str, Any] | None:
        """把一条原始记录规范化；无法处理则返回 None（调用方负责保留原文）。"""
        if not isinstance(item, dict):
            return None
        entry = dict(item)
        memory_type = entry.get("type", DEFAULT_MEMORY_TYPE)
        if memory_type not in MEMORY_TYPES:
            memory_type = DEFAULT_MEMORY_TYPE
        importance = entry.get("importance", 1)
        if not isinstance(importance, int):
            importance = 1
        importance = min(5, max(1, importance))
        # Existing summaries were already active before confirmation existed.
        confirmed = entry.get("user_confirmed", True)
        if not isinstance(confirmed, bool):
            confirmed = bool(confirmed)
        entry["type"] = memory_type
        entry["importance"] = importance
        entry["user_confirmed"] = confirmed
        # created_at 缺失或非法时兜底，而不是让所有记忆接口一起 500。
        created = self._parse_utc(entry.get("created_at")) or self._parse_utc(entry.get("id"))
        if created is None:
            created = datetime.now(timezone.utc)
            logger.warning(
                "记忆条目 %s 的 created_at 缺失或非法，已回填为当前时间", entry.get("id")
            )
        entry["created_at"] = created.isoformat()
        facts = normalize_memory_facts(entry.get("facts"))
        entry["facts"] = apply_fact_retention(
            [
                {
                    **fact,
                    "user_confirmed": fact.get("user_confirmed", confirmed)
                    if isinstance(fact.get("user_confirmed", confirmed), bool)
                    else confirmed,
                }
                for fact in facts
            ],
            created,
        )
        entry["retention_class"] = memory_retention_class(memory_type, entry["facts"])
        entry_expiry = entry_expiry_for_facts(created, memory_type, entry["facts"])
        entry["expires_at"] = entry_expiry.isoformat() if entry_expiry else None
        return entry

    def _read_all(self) -> list[dict[str, Any]]:
        if self._degraded_reason is not None:
            return []
        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError as exc:
            self._enter_readonly_degraded(f"记忆库读取失败：{exc}")
            return []
        if not content.strip():
            # __init__ 至少会写入 "[]"，所以真正的 0 字节文件只可能来自被中断的写入。
            self._enter_readonly_degraded("记忆库文件为空（疑似写入中断）")
            return []
        try:
            data = json.loads(content)
        except ValueError as exc:
            self._enter_readonly_degraded(f"记忆库 JSON 解析失败：{exc}")
            return []
        if not isinstance(data, list):
            self._enter_readonly_degraded("记忆库顶层结构不是数组")
            return []

        normalized: list[dict[str, Any]] = []
        unreadable: list[Any] = []
        for item in data:
            try:
                entry = self._normalize_entry(item)
            except Exception as exc:  # noqa: BLE001 - 逐条隔离，坏记录不连坐
                logger.warning("跳过无法解析的记忆条目：%s", exc)
                entry = None
            if entry is None:
                unreadable.append(item)
                continue
            normalized.append(entry)
        self._unreadable_entries = unreadable
        if unreadable:
            logger.warning(
                "记忆库有 %d 条记录无法解析，已跳过但会在写入时原样保留", len(unreadable)
            )
        return normalized

    def _write_all(self, items: list[dict[str, Any]], *, allow_empty: bool = False) -> None:
        if self._degraded_reason is not None:
            raise MemoryStoreDegradedError(
                f"记忆库处于只读降级状态，写入已被拒绝：{self._degraded_reason}",
                self._quarantine_path,
            )
        payload: list[Any] = list(items) + list(self._unreadable_entries)
        if not payload and not allow_empty and self._disk_entry_count() > 0:
            raise MemoryStoreDegradedError(
                "拒绝把非空记忆库写成空 —— 疑似读取异常导致的静默清空"
            )
        # tmp 名带 pid+uuid，避免并发写入互相踩（同 fithealth_agent/atomic_json.py）。
        atomic_write_json(self.path, payload)

    def _disk_entry_count(self) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        return len(data) if isinstance(data, list) else 0

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    @staticmethod
    def _fact_slot(fact: dict[str, object]) -> tuple[str, str, str]:
        namespace = str(fact.get("namespace") or "")
        key = str(fact.get("key") or "")
        if (namespace, key) in FACT_VERSION_SINGLETON_KEYS:
            return namespace, key, "*"
        return namespace, key, str(fact.get("value") or "").casefold()

    @classmethod
    def _slot_versions(cls, items: list[dict[str, Any]]) -> dict[tuple[str, str, str], int]:
        versions: dict[tuple[str, str, str], int] = {}
        for item in items:
            for fact in item.get("facts", []) if isinstance(item.get("facts"), list) else []:
                if not isinstance(fact, dict) or not fact.get("user_confirmed", bool(item.get("user_confirmed"))):
                    continue
                slot = cls._fact_slot(fact)
                version = fact.get("version", 0)
                if isinstance(version, int):
                    versions[slot] = max(versions.get(slot, 0), version)
        return versions
    def add_entry(
        self,
        summary: str,
        metadata: dict[str, Any],
        expires_at: datetime,
        *,
        memory_type: str = DEFAULT_MEMORY_TYPE,
        importance: int = 1,
        user_confirmed: bool = False,
        facts: list[dict[str, object]] | None = None,
    ) -> dict[str, Any]:
        """保存一条对话摘要。

        Args:
            summary: LLM 提炼的结构化摘要文本（< 500字）
            metadata: 附加元数据，如 {reason: '...', pipeline_stage: '...'}
            expires_at: 过期时间（UTC），通常为 now + 3天

        Returns:
            刚写入的条目 dict
        """
        if memory_type not in MEMORY_TYPES:
            raise ValueError("Unsupported memory type")
        if not isinstance(importance, int) or not 1 <= importance <= 5:
            raise ValueError("Memory importance must be between 1 and 5")
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            now_iso = datetime.now(timezone.utc).isoformat()
            normalized_facts = apply_fact_retention(normalize_memory_facts(facts), datetime.now(timezone.utc))
            versions = self._slot_versions(items)
            for fact in normalized_facts:
                base_version = versions.get(self._fact_slot(fact), 0)
                fact["base_version"] = base_version
                fact["user_confirmed"] = bool(user_confirmed)
                if user_confirmed:
                    fact["version"] = base_version + 1
                    versions[self._fact_slot(fact)] = base_version + 1
            entry_expiry = (
                entry_expiry_for_facts(
                    datetime.fromisoformat(now_iso), memory_type, normalized_facts
                )
                if normalized_facts
                else expires_at
            )
            entry: dict[str, Any] = {
                "id": str(uuid4()),
                "summary": summary,
                "metadata": metadata,
                "created_at": now_iso,
                "expires_at": entry_expiry.isoformat() if entry_expiry else None,
                "type": memory_type,
                "importance": importance,
                "user_confirmed": user_confirmed,
                "facts": normalized_facts,
                "retention_class": memory_retention_class(memory_type, normalized_facts),
            }
            items.append(entry)
            self._write_all(items)
            return entry

    def cleanup_expired(self) -> int:
        """删除所有已过期条目，返回被删除的数量。"""
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            now = datetime.now(timezone.utc)
            remaining = []
            for item in items:
                facts = item.get("facts") if isinstance(item.get("facts"), list) else []
                if facts:
                    kept_facts = []
                    for fact in facts:
                        if not isinstance(fact, dict):
                            continue
                        if fact.get("status") == "rejected":
                            rejected_at_raw = fact.get("rejected_at") or item.get("created_at")
                            try:
                                rejected_at = datetime.fromisoformat(str(rejected_at_raw)).astimezone(timezone.utc)
                            except (TypeError, ValueError):
                                rejected_at = now
                            if rejected_at + timedelta(days=90) > now:
                                kept_facts.append(fact)
                        elif fact_is_active(fact, now):
                            kept_facts.append(fact)
                    item["facts"] = kept_facts
                    if item["facts"]:
                        remaining.append(item)
                elif item.get("expires_at") is None or datetime.fromisoformat(item["expires_at"]).astimezone(timezone.utc) > now:
                    remaining.append(item)
            removed = len(items) - len(remaining)
            if removed > 0:
                self._write_all(remaining, allow_empty=True)
            return removed

    def get_all(self) -> list[dict[str, Any]]:
        """返回所有条目（包括已过期的，调用前建议先 cleanup_expired）。"""
        with self._lock, JsonFileLock(self.path):
            return self._read_all()

    def get_recent(self, n: int = 5) -> list[dict[str, Any]]:
        """返回最近 n 条**未过期**的摘要（按 created_at 倒序）。"""
        with self._lock, JsonFileLock(self.path):
            now = datetime.now(timezone.utc)
            items = self._read_all()
            valid = [it for it in items if it.get("expires_at") is None or datetime.fromisoformat(it["expires_at"]).astimezone(timezone.utc) > now]
            valid.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return valid[:n]

    def get_context_memories(self, n: int = 5, *, intent: str = "") -> list[dict[str, Any]]:
        """Return confirmed, unexpired memories ranked for agent-context injection.

        收录规则（BUG-13）：

        1. 有**已确认且仍有效**的结构化事实 → 收录，并只带上这些事实。
        2. 条目级已确认、且**完全没有事实** → 同样收录（纯自然语言摘要）。
           以前这里硬性要求 facts 非空，导致只有摘要的记忆无论怎么确认都
           永远进不了上下文，`format_cross_session_memories` 的"历史摘要"
           分支在 /chat 中恒为空。
        3. **有事实但一条都没确认（或都被拒绝/清除）→ 不收录。** 这一条是
           安全边界：不能因为条目级已确认，就把用户明确拒绝掉的事实所对应
           的摘要原文重新灌回上下文。
        """
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
        now = datetime.now(timezone.utc)
        valid = []
        for item in items:
            if item.get("expires_at") is not None and datetime.fromisoformat(item["expires_at"]).astimezone(timezone.utc) <= now:
                continue
            all_facts = normalize_memory_facts(item.get("facts"))
            confirmed_facts = [
                fact for fact in all_facts
                if fact.get("status") == "active" and fact_is_active(fact) and fact.get("user_confirmed", bool(item.get("user_confirmed")))
            ]
            summary_only = (
                not all_facts
                and bool(item.get("user_confirmed"))
                and bool((item.get("metadata") or {}).get("legacy"))
            )
            if confirmed_facts or summary_only:
                copy = dict(item)
                copy["facts"] = confirmed_facts
                copy["user_confirmed"] = True
                valid.append(copy)
        intent_keys = {
            "create_training_plan": {
                ("plan", "weekly_schedule"), ("health", "injury_or_constraint"),
                ("health", "recovery_status"), ("training", "avoid_exercise"),
                ("training", "max_rpe"), ("training", "max_sets_per_exercise"),
                ("training", "max_total_sets"), ("training", "required_plan_elements"),
            },
            "search_youtube_video": {("youtube", "avoid_channel")},
        }.get(str(intent or ""), set())

        def relevance(item: dict[str, Any]) -> int:
            slots = {
                (str(fact.get("namespace") or ""), str(fact.get("key") or ""))
                for fact in item.get("facts") or [] if isinstance(fact, dict)
            }
            return 1 if slots & intent_keys else 0

        valid.sort(
            key=lambda item: (
                relevance(item), int(item.get("importance", 1)), item.get("created_at", "")
            ),
            reverse=True,
        )

        def is_hard_constraint(item: dict[str, Any]) -> bool:
            hard_keys = {
                ("health", "injury_or_constraint"), ("health", "recovery_status"),
                ("plan", "weekly_schedule"), ("training", "avoid_exercise"),
                ("training", "max_rpe"), ("training", "max_sets_per_exercise"),
                ("training", "max_total_sets"), ("training", "required_plan_elements"),
                ("youtube", "avoid_channel"),
            }
            for fact in item.get("facts") or []:
                if not isinstance(fact, dict):
                    continue
                namespace = str(fact.get("namespace") or "")
                key = str(fact.get("key") or "")
                if (namespace, key) in hard_keys:
                    return True
            return False

        # Hard constraints must never be evicted by a burst of high-importance
        # feedback entries. The n budget applies only to ordinary memories.
        hard = [item for item in valid if is_hard_constraint(item)]
        ordinary = [item for item in valid if not is_hard_constraint(item)]
        return hard + ordinary[:n]

    def get_enforceable_memories(self) -> list[dict[str, Any]]:
        """Return all confirmed, unexpired memory entries for deterministic enforcement."""
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
        now = datetime.now(timezone.utc)
        valid: list[dict[str, Any]] = []
        for item in items:
            expires = item.get("expires_at")
            if expires is not None and datetime.fromisoformat(expires).astimezone(timezone.utc) <= now:
                continue
            facts = [
                fact for fact in normalize_memory_facts(item.get("facts"))
                if fact.get("status") == "active" and fact_is_active(fact) and fact.get("user_confirmed", bool(item.get("user_confirmed")))
            ]
            if facts or (not normalize_memory_facts(item.get("facts")) and item.get("user_confirmed")):
                copy = dict(item)
                copy["facts"] = facts
                copy["user_confirmed"] = True
                valid.append(copy)
        return valid

    def _find_fact(
        self,
        items: list[dict[str, Any]],
        entry_id: str,
        fact_index: int | None = None,
        fact_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, object], int] | None:
        """按 fact_id 优先定位事实；只有没给 id 时才退回下标（BUG-12）。

        下标寻址保留下来只为兼容老页面。它本身是不安全的：`cleanup_expired`
        会物理删除过期事实、`reject_fact` 会 pop 移位，老页面手里的下标随时
        可能指向另一条事实。
        """
        for item in items:
            if item.get("id") != entry_id:
                continue
            facts = item.get("facts") or []
            if fact_id:
                for index, fact in enumerate(facts):
                    if isinstance(fact, dict) and fact.get("fact_id") == fact_id:
                        return item, fact, index
                return None
            if isinstance(fact_index, int) and not isinstance(fact_index, bool) and 0 <= fact_index < len(facts):
                logger.info(
                    "记忆事实按下标寻址（entry=%s index=%s）——下标可能已位移，建议前端改用 fact_id",
                    entry_id,
                    fact_index,
                )
                return item, facts[fact_index], fact_index
            return None
        return None

    @staticmethod
    def _fact_ref(fact: dict[str, object], index: int) -> dict[str, Any]:
        return {"fact_index": index, "fact_id": fact.get("fact_id")}

    def set_fact_confirmation(
        self,
        entry_id: str,
        fact_index: int | None = None,
        confirmed: bool = True,
        *,
        fact_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            found = self._find_fact(items, entry_id, fact_index, fact_id)
            if found is None:
                return None
            item, fact, index = found
            if confirmed:
                if fact.get("user_confirmed"):
                    return {"entry": item, "fact": fact, **self._fact_ref(fact, index)}
                versions = self._slot_versions(items)
                slot = self._fact_slot(fact)
                counterpart = FACT_CONFLICT_PAIRS.get(slot[:2])
                if counterpart:
                    for existing_item in items:
                        for existing_fact in existing_item.get("facts", []) if isinstance(existing_item.get("facts"), list) else []:
                            if (
                                isinstance(existing_fact, dict)
                                and existing_fact.get("user_confirmed")
                                and self._fact_slot(existing_fact)[:2] == counterpart
                                and str(existing_fact.get("value") or "").casefold() == str(fact.get("value") or "").casefold()
                            ):
                                raise MemoryConflictError("同一动作同时存在偏好与避用冲突，请先明确选择")
                current_version = versions.get(slot, 0)
                base_version = fact.get("base_version", 0)
                if not isinstance(base_version, int):
                    base_version = 0
                if current_version > base_version:
                    raise MemoryConflictError("该待确认事实基于旧版本，当前已有更新事实，请重新确认")
                fact["version"] = current_version + 1
                fact["base_version"] = current_version + 1
            fact["user_confirmed"] = bool(confirmed)
            item["user_confirmed"] = all(bool(value.get("user_confirmed")) for value in item.get("facts", []))
            self._write_all(items)
            return {"entry": item, "fact": fact, **self._fact_ref(fact, index)}

    def reject_fact(
        self,
        entry_id: str,
        fact_index: int | None = None,
        *,
        fact_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            found = self._find_fact(items, entry_id, fact_index, fact_id)
            if found is None:
                return None
            item, fact, index = found
            facts = item.get("facts") or []
            removed = facts[index]
            removed["status"] = "rejected"
            removed["user_confirmed"] = False
            removed["rejected_at"] = datetime.now(timezone.utc).isoformat()
            item.setdefault("rejected_fact_ids", []).append(removed.get("fact_id"))
            item["facts"] = facts
            item["user_confirmed"] = bool(facts) and all(bool(value.get("user_confirmed")) for value in facts)
            self._write_all(items)
            return {"entry": item, "fact": removed, **self._fact_ref(removed, index)}

    def edit_fact(
        self,
        entry_id: str,
        fact_index: int | None = None,
        value: object = None,
        evidence: str | None = None,
        *,
        fact_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            found = self._find_fact(items, entry_id, fact_index, fact_id)
            if found is None:
                return None
            item, fact, index = found
            replacement = dict(fact)
            definition = FACT_DEFINITIONS.get((replacement.get("namespace"), replacement.get("key")), {})
            if definition.get("numeric") and isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as exc:
                    raise ValueError("事实内容必须是数字") from exc
            replacement["value"] = value
            if evidence is not None:
                replacement["evidence"] = evidence
            normalized = normalize_memory_facts([replacement])
            if not normalized:
                raise ValueError("事实内容无效")
            # fact_id 由内容派生，编辑后会变。若新值与同条目里另一条事实撞车，
            # 两条会共用一个 id 而无法再分别寻址——直接拒绝，这也是合理的产品规则。
            new_id = normalized[0].get("fact_id")
            for other_index, other in enumerate(item.get("facts") or []):
                if other_index != index and isinstance(other, dict) and other.get("fact_id") == new_id:
                    raise ValueError("该条目里已存在相同内容的事实")
            history = list(fact.get("history") or [])
            history.append({
                "value": fact.get("value"),
                "evidence": fact.get("evidence", ""),
                "version": fact.get("version", 0),
                "changed_at": datetime.now(timezone.utc).isoformat(),
            })
            normalized[0]["history"] = history[-20:]
            normalized[0]["previous_value"] = fact.get("value")
            normalized[0]["user_confirmed"] = False
            slot = self._fact_slot(fact)
            normalized[0]["base_version"] = self._slot_versions(items).get(slot, 0)
            normalized[0].pop("version", None)
            item["facts"][index] = normalized[0]
            item["user_confirmed"] = False
            self._write_all(items)
            return {"entry": item, "fact": normalized[0], **self._fact_ref(normalized[0], index)}

    def forget_facts(
        self, namespace: str, key: str, value: object | None = None, *, reason: str = "user_request"
    ) -> dict[str, Any]:
        """Deterministically clear every matching confirmed fact and retain an audit trail."""
        if (namespace, key) not in FACT_DEFINITIONS:
            raise ValueError("未知的记忆事实类型")
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            cleared: list[dict[str, object]] = []
            now_iso = datetime.now(timezone.utc).isoformat()
            expected = str(value).casefold() if value is not None else None
            for item in items:
                for fact in item.get("facts", []) if isinstance(item.get("facts"), list) else []:
                    if not isinstance(fact, dict):
                        continue
                    if (fact.get("namespace"), fact.get("key")) != (namespace, key):
                        continue
                    if expected is not None and str(fact.get("value") or "").casefold() != expected:
                        continue
                    if fact.get("status") != "active" or not fact.get("user_confirmed"):
                        continue
                    fact["previous_value"] = fact.get("value")
                    fact["status"] = "cleared"
                    fact["cleared_at"] = now_iso
                    fact["clear_reason"] = reason
                    fact.setdefault("history", []).append({
                        "action": "forgotten", "value": fact.get("value"), "at": now_iso,
                    })
                    cleared.append(dict(fact))
            if cleared:
                self._write_all(items)
            return {"cleared": len(cleared), "facts": cleared, "audit_at": now_iso}

    def log_fact_usage(
        self, fact_ids: list[str], *, action: str, detail: str = "", request_id: str = ""
    ) -> int:
        wanted = {str(item) for item in fact_ids if item}
        if not wanted:
            return 0
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            now_iso = datetime.now(timezone.utc).isoformat()
            changed = 0
            for item in items:
                for fact in item.get("facts", []) if isinstance(item.get("facts"), list) else []:
                    if isinstance(fact, dict) and str(fact.get("fact_id") or "") in wanted:
                        fact.setdefault("usage_log", []).append({
                            "at": now_iso, "action": action, "detail": detail[:500],
                            "request_id": request_id,
                        })
                        fact["usage_log"] = fact["usage_log"][-50:]
                        changed += 1
            if changed:
                self._write_all(items)
            return changed

    def rollback_fact(
        self, entry_id: str, *, fact_id: str, history_index: int = -1
    ) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            found = self._find_fact(items, entry_id, fact_id=fact_id)
            if found is None:
                return None
            item, fact, index = found
            history = fact.get("history") if isinstance(fact.get("history"), list) else []
            if not history:
                raise ValueError("该事实没有可回滚的历史版本")
            try:
                old = history[history_index]
            except IndexError as exc:
                raise ValueError("历史版本不存在") from exc
            resolved_history_index = history_index if history_index >= 0 else len(history) + history_index
            replacement = dict(fact)
            replacement["value"] = old.get("value")
            replacement["evidence"] = old.get("evidence", replacement.get("evidence", ""))
            normalized = normalize_memory_facts([replacement])
            if not normalized:
                raise ValueError("历史版本内容无效")
            normalized[0]["history"] = history[:resolved_history_index]
            normalized[0]["previous_value"] = fact.get("value")
            normalized[0]["user_confirmed"] = False
            normalized[0]["base_version"] = self._slot_versions(items).get(self._fact_slot(fact), 0)
            item["facts"][index] = normalized[0]
            item["user_confirmed"] = False
            self._write_all(items)
            return {"entry": item, "fact": normalized[0], **self._fact_ref(normalized[0], index)}

    def reject_entry(self, entry_id: str) -> dict[str, Any] | None:
        """Reject every pending fact in an entry without nested public-method locks."""
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            target = next((item for item in items if item.get("id") == entry_id), None)
            if target is None:
                return None
            now_iso = datetime.now(timezone.utc).isoformat()
            rejected_ids = set(target.get("rejected_fact_ids") or [])
            changed = 0
            for fact in target.get("facts", []) if isinstance(target.get("facts"), list) else []:
                if not isinstance(fact, dict) or fact.get("user_confirmed") or fact.get("status") != "active":
                    continue
                fact["status"] = "rejected"
                fact["user_confirmed"] = False
                fact["rejected_at"] = now_iso
                rejected_ids.add(fact.get("fact_id"))
                changed += 1
            target["rejected_fact_ids"] = [item for item in rejected_ids if item]
            target["user_confirmed"] = False
            if changed:
                self._write_all(items)
            return {"entry": target, "rejected": changed}

    def confirm_entry(self, entry_id: str) -> dict[str, Any] | None:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            target = next((item for item in items if item.get("id") == entry_id), None)
            if target is None:
                return None
            if not isinstance(target.get("facts"), list) or not target.get("facts"):
                raise ValueError("该记忆没有可确认的事实")
            versions = self._slot_versions(items)
            pending = [fact for fact in target.get("facts", []) if isinstance(fact, dict) and not fact.get("user_confirmed")]
            for fact in pending:
                current_version = versions.get(self._fact_slot(fact), 0)
                base_version = fact.get("base_version", 0)
                if not isinstance(base_version, int):
                    base_version = 0
                if current_version > base_version:
                    raise MemoryConflictError("该待确认记忆包含基于旧版本的事实，当前已有更新事实，请逐条检查并重新确认")
            for fact in pending:
                slot = self._fact_slot(fact)
                current_version = versions.get(slot, 0)
                fact["version"] = current_version + 1
                fact["user_confirmed"] = True
                fact["base_version"] = current_version + 1
                versions[slot] = current_version + 1
            target["user_confirmed"] = all(bool(fact.get("user_confirmed")) for fact in target.get("facts", []))
            self._write_all(items)
            return {"entry": target}
    def delete_entry(self, entry_id: str) -> bool:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            remaining = [item for item in items if item.get("id") != entry_id]
            if len(remaining) == len(items):
                return False
            self._write_all(remaining, allow_empty=True)
            return True

    def clear(self) -> int:
        with self._lock, JsonFileLock(self.path):
            items = self._read_all()
            self._write_all([], allow_empty=True)
            return len(items)
