"""Derive muscle training load and recovery windows from daily records.

This module intentionally has no storage dependency.  A snapshot is rebuilt
from the current ``daily_records.json`` payload so edits, merges and deletions
are reflected automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import re
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .muscle_map import (
    REGION_ALIASES,
    REGION_LEXICON,
    MuscleHit,
    muscle_ids_for_region,
    muscle_ids_for_text,
    muscles_for_sport,
    regions_for_text,
    resolve_muscles_for_exercise,
)


BEIJING = ZoneInfo("Asia/Shanghai")
BASE_RECOVERY_HOURS: dict[str, float] = {
    "quadriceps": 48.0,
    "gluteus_maximus": 48.0,
    "latissimus": 48.0,
    "chest": 48.0,
    "erector_spinae": 48.0,
    "hamstrings": 36.0,
    "rhomboids": 36.0,
    "front_deltoid": 36.0,
    "lateral_deltoid": 36.0,
    "rear_deltoid": 36.0,
    "biceps": 24.0,
    "triceps": 24.0,
    "calves": 24.0,
    "core": 24.0,
    "abductors": 36.0,
    "adductors": 36.0,
    "brachioradialis": 24.0,
    "forearms": 24.0,
    "lower_chest": 48.0,
    "obliques": 24.0,
    "serratus_anterior": 36.0,
    "trapezius": 36.0,
    "trapezius_upper": 36.0,
    "upper_chest": 48.0,
}

#: BUG-26 问题 1：当天只有次要命中的肌群，恢复窗口按基础值折半。
#: 与容量口径（次要权重 0.4）同向，但不取 0.4——窗口是生理恢复时间，次要发力也
#: 确实需要一些时间，只是不该等同于主项。
SECONDARY_WINDOW_FACTOR = 0.5

_RECOVERED_STATE_PATTERN = re.compile(
    r"(?:都)?(?<!不)(?:正常|没感觉|没问题|还行)"
)
_NEGATED_SYMPTOM_PATTERN = re.compile(
    r"(?:没有|没|不)(?:再|怎么|什么|那么|这么|一点|任何|丝毫|明显)?"
    r"(?:酸痛|酸疼|疼痛|刺痛|酸|疼|痛|紧|发紧)(?:了)?"
)
_RECOVERY_TRANSITION_PATTERN = re.compile(
    r"(?<!没有)(?<!尚未)(?<!未见)(?<!未曾)(?<!从未)(?<!没)(?<!未)(?<!不)"
    r"(?:(?:已经|已|后来|现在|目前)?(?:完全)?"
    r"(?:恢复了?|好了|好转了?|缓解了?|消失了?|减轻了?))"
    r"(?!不|训练|锻炼|运动|计划|期|情况|状态|时间)"
)
_SORE_PATTERN = re.compile(
    r"(?:有点|还有点|稍微|轻微)?(?<!不)(?<!没)(?<!无)(?:酸痛|酸疼|酸|紧|发紧)"
)
_PAINFUL_PATTERN = re.compile(
    r"(?:刺痛|剧痛|(?<!酸)(?<!不)(?<!没)(?<!无)(?:疼痛|疼|痛)|使不上劲|无力)"
)
_ALL_RECOVERED_PATTERN = re.compile(r"(?:全部|全都|都)(?:正常|恢复|没感觉|没问题|还行|不酸|不疼|不痛)")
_THIRD_PARTY_SUBJECT_PATTERN = re.compile(
    r"(?:我的?)?(?:朋友|同事|同学|家人|亲戚|伴侣|对象|孩子|儿子|女儿|父母|爸爸|妈妈|丈夫|妻子|老公|老婆|室友|教练|客户)|他|她"
)
_SELF_SUBJECT_PATTERN = re.compile(r"我|本人|自己")


def _is_third_party_clause(text: str, symptom_start: int | None = None) -> bool:
    before = text[:symptom_start] if symptom_start is not None else text
    subjects = list(_THIRD_PARTY_SUBJECT_PATTERN.finditer(before))
    if not subjects:
        return False
    return _SELF_SUBJECT_PATTERN.search(before[subjects[-1].end():]) is None


@dataclass(frozen=True)
class SorenessReport:
    region: str
    muscle_ids: tuple[str, ...]
    level: str
    reported_at: datetime
    expires_at: datetime
    evidence: str = ""
    id: str = ""
    expired: bool = False


@dataclass(frozen=True)
class MuscleLoad:
    muscle_id: str
    zh: str
    region: str
    last_trained_at: datetime
    weekday_zh: str
    exercises: tuple[str, ...]
    effective_sets: float
    recovery_hours: float
    recovered_at: datetime
    hours_remaining: float
    role: str = "primary"
    needs_reduction: bool = False
    soreness_level: str = "unknown"
    raw_sets: float = 0.0
    history: tuple[tuple[datetime, float, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class LoadWarning:
    muscle_id: str
    zh: str
    region: str
    kind: str
    message: str
    latest_sets: float
    baseline_sets: float = 0.0
    ratio: float = 0.0
    consecutive_days: int = 0


@dataclass(frozen=True)
class MuscleRecoverySnapshot:
    loads: tuple[MuscleLoad, ...] = ()
    recovering: tuple[MuscleLoad, ...] = ()
    ready: tuple[MuscleLoad, ...] = ()
    garmin_recovery_hours: float = 0.0
    lookback_days: int = 10
    skipped_future: int = 0
    load_warnings: tuple[LoadWarning, ...] = ()

    @property
    def by_muscle(self) -> dict[str, MuscleLoad]:
        return {load.muscle_id: load for load in self.loads}

    @property
    def muscle_loads(self) -> tuple[MuscleLoad, ...]:
        """Compatibility alias for callers that prefer an explicit name."""
        return self.loads

    def for_region(self, region: str) -> tuple[MuscleLoad, ...]:
        return tuple(load for load in self.loads if load.region == region)


def _reply_level(text: str) -> str | None:
    # 局部否定只屏蔽紧随其后的症状；明确恢复则建立时间分界，只考察恢复后
    # 是否又出现主动症状。这样“不酸但很痛”仍是 painful，“疼痛已经恢复”则
    # 是 recovered，“恢复了但又有点酸”重新落回 sore。
    normalized = re.sub(r"\s+", "", str(text or ""))
    negated = list(_NEGATED_SYMPTOM_PATTERN.finditer(normalized))
    masked = normalized
    for match in reversed(negated):
        masked = masked[:match.start()] + (" " * (match.end() - match.start())) + masked[match.end():]

    transitions = list(_RECOVERY_TRANSITION_PATTERN.finditer(normalized))
    candidate = masked[transitions[-1].end():] if transitions else masked
    recovered = bool(
        transitions
        or negated
        or _RECOVERED_STATE_PATTERN.search(normalized)
    )

    if _PAINFUL_PATTERN.search(candidate):
        return "painful"
    if _SORE_PATTERN.search(candidate):
        return "sore"
    if recovered:
        return "recovered"
    return None


def parse_soreness_reply(
    message: str,
    asked_regions: list[str],
    *,
    now: datetime | None = None,
) -> list[SorenessReport]:
    """Parse deterministic region + soreness feedback from one chat message."""

    normalized = re.sub(r"\s+", "", str(message or ""))
    prompted = [region for region in asked_regions if region in REGION_ALIASES]
    mentioned = sorted(regions_for_text(normalized, include_secondary=False))
    allowed = list(dict.fromkeys([*prompted, *mentioned]))
    if not normalized or not allowed:
        return []
    now = (now or datetime.now(BEIJING)).astimezone(BEIJING)

    all_recovered = _ALL_RECOVERED_PATTERN.search(normalized)
    if all_recovered:
        return [
            SorenessReport(
                region=region,
                muscle_ids=muscle_ids_for_text(region, message),
                level="recovered",
                reported_at=now,
                expires_at=now + timedelta(hours=72),
                evidence=message[:500],
            )
            for region in allowed
        ]

    reports: list[SorenessReport] = []
    clauses = [item for item in re.split(r"[，。；;,、\n]+", normalized) if item]
    clause_regions = [
        {
            region
            for region in allowed
            if any(alias in clause for alias in REGION_ALIASES[region])
        }
        for clause in clauses
    ]
    for region in allowed:
        levels: list[str] = []
        for index, regions in enumerate(clause_regions):
            if region not in regions:
                continue
            clause = clauses[index]
            region_start = min(
                clause.find(alias)
                for alias in REGION_ALIASES[region]
                if alias in clause
            )
            if _is_third_party_clause(clause, region_start):
                continue
            end = index + 1
            while end < len(clauses) and not clause_regions[end]:
                end += 1
            parsed = _reply_level("，".join(clauses[index:end]))
            if parsed is not None:
                levels.append(parsed)
        level = levels[-1] if levels else None
        if level is not None:
            reports.append(SorenessReport(
                region=region,
                muscle_ids=muscle_ids_for_text(region, clause),
                level=level,
                reported_at=now,
                expires_at=now + timedelta(hours=72),
                evidence=message[:500],
            ))

    if reports:
        return reports
    if _is_third_party_clause(normalized):
        return []
    level = _reply_level(normalized)
    if level is not None and len(allowed) == 1:
        region = allowed[0]
        return [SorenessReport(
            region=region,
            muscle_ids=muscle_ids_for_text(region, message),
            level=level,
            reported_at=now,
            expires_at=now + timedelta(hours=72),
            evidence=message[:500],
        )]
    return []


def soreness_reply_needs_clarification(message: str, asked_regions: list[str]) -> bool:
    """True when a degree was supplied for several asked regions but no region was named."""

    normalized = re.sub(r"\s+", "", str(message or ""))
    allowed = list(dict.fromkeys(region for region in asked_regions if region in REGION_ALIASES))
    if _ALL_RECOVERED_PATTERN.search(normalized):
        return False
    if len(allowed) <= 1 or _reply_level(normalized) is None:
        return False
    return not any(
        alias in normalized
        for aliases in REGION_ALIASES.values()
        for alias in aliases
    )


@dataclass
class _Accumulated:
    hit: MuscleHit
    date_key: date
    last_trained_at: datetime
    effective_sets: float = 0.0
    exercises: set[str] | None = None
    raw_sets: float = 0.0

    def __post_init__(self) -> None:
        if self.exercises is None:
            self.exercises = set()


def _as_datetime(value: Any, *, default_tz: ZoneInfo = BEIJING) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt.astimezone(BEIJING)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _weekday_zh(value: datetime) -> str:
    return ("周一", "周二", "周三", "周四", "周五", "周六", "周日")[value.weekday()]


def _record_payload(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("record")
    return value if isinstance(value, dict) else item


def _activity_time(item: dict[str, Any], record: dict[str, Any], segment: dict[str, Any] | None = None) -> datetime | None:
    segment = segment or {}
    for key in ("start_time", "end_time"):
        parsed = _as_datetime(segment.get(key))
        if parsed is not None:
            return parsed
    session = record.get("session")
    if isinstance(session, dict):
        parsed = _as_datetime(session.get("start_time"))
        if parsed is not None:
            return parsed
    for key in ("workout_start_time_beijing", "created_at", "date"):
        parsed = _as_datetime(record.get(key) or item.get(key))
        if parsed is not None:
            return parsed
    return None


def _segments(record: dict[str, Any]) -> list[dict[str, Any]]:
    value = record.get("segments")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sport_name(item: dict[str, Any], record: dict[str, Any]) -> str:
    session = record.get("session")
    if isinstance(session, dict) and session.get("sport"):
        return str(session["sport"])
    return str(record.get("sport") or item.get("category") or "")


def _in_lookback(activity_time: datetime, now: datetime, lookback_days: int) -> bool:
    if activity_time > now:
        return False
    return activity_time >= now - timedelta(days=max(0, int(lookback_days)))


def _soreness_for(muscle_id: str, soreness: Iterable[SorenessReport] | None, now: datetime) -> str:
    level = "unknown"
    ordered = sorted(
        soreness or (),
        key=lambda item: _as_datetime(item.reported_at) or datetime.min.replace(tzinfo=BEIJING),
    )
    for report in ordered:
        expires_at = _as_datetime(report.expires_at)
        reported_at = _as_datetime(report.reported_at)
        if expires_at is not None and expires_at <= now:
            continue
        if reported_at is not None and reported_at > now:
            continue
        ids = set(report.muscle_ids or ())
        if muscle_id in ids and report.level in {"recovered", "sore", "painful"}:
            # A later report wins when callers pass reports in chronological order.
            level = report.level
    return level


def normalise_garmin_hours(value: Any) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0.0
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not 0 <= number <= 96.0:
        return None
    return round(number, 1)


def _append_event(
    buckets: dict[str, dict[date, _Accumulated]],
    hit: MuscleHit,
    activity_time: datetime,
    effective_sets: float,
    exercise: str,
) -> None:
    by_date = buckets.setdefault(hit.muscle_id, {})
    entry = by_date.get(activity_time.date())
    if entry is None:
        entry = _Accumulated(hit=hit, date_key=activity_time.date(), last_trained_at=activity_time)
        by_date[activity_time.date()] = entry
    elif entry.hit.role == "secondary" and hit.role == "primary":
        entry.hit = hit
    if activity_time > entry.last_trained_at:
        entry.last_trained_at = activity_time
    entry.effective_sets += max(0.0, effective_sets) * hit.weight
    entry.raw_sets += max(0.0, effective_sets)
    if exercise:
        entry.exercises.add(exercise)  # type: ignore[union-attr]


def build_recovery_snapshot(
    records: list[dict[str, Any]],
    *,
    now: datetime,
    soreness: list[SorenessReport] | None = None,
    garmin_recovery_hours: float = 0.0,
    lookback_days: int = 10,
    allow_external_models: bool = False,
    model_resolver: Any = None,
) -> MuscleRecoverySnapshot:
    """Build a snapshot from current records.

    Strength segments count as sets.  Lap-based sport records use total active
    minutes / 10, capped at four effective sets, and never use lap count as a
    proxy for strength-training volume.
    """

    if now.tzinfo is None:
        now = now.replace(tzinfo=BEIJING)
    now_bj = now.astimezone(BEIJING)
    garmin = normalise_garmin_hours(garmin_recovery_hours)
    if garmin is None:
        raise ValueError("garmin_recovery_hours must be between 0 and 96.0")
    buckets: dict[str, dict[date, _Accumulated]] = {}
    exercise_cache: dict[str, tuple[MuscleHit, ...]] = {}
    skipped_future = 0

    def resolve_exercise(name: str) -> tuple[MuscleHit, ...]:
        key = str(name or "").strip().casefold()
        if key not in exercise_cache:
            exercise_cache[key] = tuple(resolve_muscles_for_exercise(
                name,
                allow_external_models=allow_external_models,
                model_resolver=model_resolver,
            ))
        return exercise_cache[key]

    for item in records or []:
        if not isinstance(item, dict):
            continue
        record = _record_payload(item)
        segments = _segments(record)
        sport = _sport_name(item, record)
        active_segments = [
            segment for segment in segments
            if str(segment.get("segment_type") or "") in {"set_active", "set"}
            and not bool(segment.get("is_rest"))
        ]
        if active_segments:
            future_in_record = False
            for segment in active_segments:
                activity_time = _activity_time(item, record, segment)
                if activity_time is not None and activity_time > now_bj:
                    future_in_record = True
                    continue
                if activity_time is None or not _in_lookback(activity_time, now_bj, lookback_days):
                    continue
                name = str(segment.get("category") or "").strip()
                hits = resolve_exercise(name)
                for hit in hits:
                    _append_event(buckets, hit, activity_time, 1.0, name)
            if future_in_record:
                skipped_future += 1
            continue

        hits = muscles_for_sport(sport)
        if not hits:
            continue
        activity_time = _activity_time(item, record)
        if activity_time is not None and activity_time > now_bj:
            skipped_future += 1
            continue
        if activity_time is None or not _in_lookback(activity_time, now_bj, lookback_days):
            continue
        duration_s = sum(max(0.0, _number(segment.get("duration_s"))) for segment in segments)
        if duration_s <= 0:
            session = record.get("session")
            if isinstance(session, dict):
                duration_s = _number(session.get("total_timer_s") or session.get("total_elapsed_s"))
        effective_sets = min(4.0, max(0.0, duration_s) / 60.0 / 10.0)
        for hit in hits:
            _append_event(buckets, hit, activity_time, effective_sets, sport)

    loads: list[MuscleLoad] = []
    load_warnings: list[LoadWarning] = []
    for muscle_id, by_date in buckets.items():
        latest = by_date[max(by_date)]
        history = tuple(
            (
                item.last_trained_at,
                round(item.effective_sets, 4),
                tuple(sorted(item.exercises or set())),
            )
            for _day, item in sorted(by_date.items(), reverse=True)
        )
        history_by_day = {item.last_trained_at.date(): item for item in by_date.values()}
        latest_day = latest.last_trained_at.date()
        consecutive_days = 0
        cursor = latest_day
        while cursor in history_by_day:
            consecutive_days += 1
            cursor -= timedelta(days=1)
        if consecutive_days >= 3:
            load_warnings.append(LoadWarning(
                muscle_id=muscle_id,
                zh=latest.hit.zh,
                region=latest.hit.region,
                kind="consecutive_days",
                message=f"{latest.hit.zh}已连续 {consecutive_days} 天承受训练负荷",
                latest_sets=round(latest.effective_sets, 4),
                consecutive_days=consecutive_days,
            ))
        baseline_entries = [
            item for day, item in history_by_day.items()
            if latest_day - timedelta(days=7) <= day < latest_day
        ]
        if len(baseline_entries) >= 2:
            baseline_sets = sum(item.effective_sets for item in baseline_entries) / len(baseline_entries)
            ratio = latest.effective_sets / baseline_sets if baseline_sets > 0 else 0.0
            if (
                latest.effective_sets >= 6.0
                and latest.effective_sets - baseline_sets >= 3.0
                and ratio >= 1.5
            ):
                load_warnings.append(LoadWarning(
                    muscle_id=muscle_id,
                    zh=latest.hit.zh,
                    region=latest.hit.region,
                    kind="volume_spike",
                    message=(
                        f"{latest.hit.zh}最新容量 {latest.effective_sets:g} 组，"
                        f"较前 7 日训练日均值 {baseline_sets:.1f} 组增加 {ratio:.1f} 倍"
                    ),
                    latest_sets=round(latest.effective_sets, 4),
                    baseline_sets=round(baseline_sets, 4),
                    ratio=round(ratio, 4),
                ))
        baseline_hours = BASE_RECOVERY_HOURS.get(muscle_id, 36.0)
        # BUG-26 问题 1：容量口径早就区分了主次（次要命中权重 0.4），窗口却没有。
        # 于是"练一次背"里硬拉带来的一点小臂次要负荷，会让小臂拿到和主项一样的
        # 36 小时，进而把整个「手臂」区域标成 recovering、压掉周计划的手臂日。
        # `latest.hit.role` 经 `_append_event` 升级过，仍是 secondary 就说明**当天
        # 完全没有主项命中**，这种负荷的窗口按折扣算。
        secondary_only = latest.hit.role != "primary"
        if secondary_only:
            baseline_hours *= SECONDARY_WINDOW_FACTOR
        effective_sets = round(latest.effective_sets, 4)
        adjusted_hours = baseline_hours * (1.0 + max(0.0, effective_sets - 6.0) / 12.0)
        adjusted_hours = min(adjusted_hours, baseline_hours * 1.5)
        soreness_level = _soreness_for(muscle_id, soreness, now_bj)
        needs_reduction = soreness_level in {"sore", "painful"} or any(
            warning.muscle_id == muscle_id for warning in load_warnings
        )
        if soreness_level in {"sore", "painful"}:
            adjusted_hours *= 1.5
        recovered_at = latest.last_trained_at + timedelta(hours=adjusted_hours)
        if soreness_level == "recovered":
            hours_remaining = 0.0
            recovered_at = now_bj
        else:
            baseline_remaining = max(0.0, (recovered_at - now_bj).total_seconds() / 3600.0)
            # Garmin's value is an extra delay only for muscles that are
            # still recovering. It must not resurrect an already recovered
            # muscle when baseline_remaining has reached zero.
            hours_remaining = (
                baseline_remaining + garmin
                if baseline_remaining > 0.0
                else 0.0
            )
            recovered_at = now_bj + timedelta(hours=hours_remaining)
        loads.append(MuscleLoad(
            muscle_id=muscle_id,
            zh=latest.hit.zh,
            region=latest.hit.region,
            last_trained_at=latest.last_trained_at,
            weekday_zh=_weekday_zh(latest.last_trained_at),
            exercises=tuple(sorted(latest.exercises or set())),
            effective_sets=effective_sets,
            recovery_hours=round(adjusted_hours, 4),
            recovered_at=recovered_at,
            hours_remaining=round(hours_remaining, 4),
            role=latest.hit.role,
            needs_reduction=needs_reduction,
            soreness_level=soreness_level,
            raw_sets=round(latest.raw_sets, 4),
            history=history,
        ))

    loads.sort(key=lambda load: (load.region, load.muscle_id))
    return MuscleRecoverySnapshot(
        loads=tuple(loads),
        recovering=tuple(load for load in loads if load.hours_remaining > 0),
        ready=tuple(load for load in loads if load.hours_remaining <= 0),
        garmin_recovery_hours=garmin,
        lookback_days=lookback_days,
        skipped_future=skipped_future,
        load_warnings=tuple(load_warnings),
    )


__all__ = [
    "BASE_RECOVERY_HOURS", "SorenessReport", "MuscleLoad", "LoadWarning", "MuscleRecoverySnapshot",
    "REGION_ALIASES", "REGION_LEXICON", "build_recovery_snapshot", "normalise_garmin_hours", "parse_soreness_reply",
    "soreness_reply_needs_clarification",
]
