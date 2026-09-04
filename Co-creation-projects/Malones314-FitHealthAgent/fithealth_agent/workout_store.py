"""workout_store.py

内存+磁盘双层 Pending Workout 状态管理。
支持所有运动类型（力量训练 / 骑行 / 跑步 / 跳绳 / 自定义…）。

职责：
  - 保存当前正在编辑的 ParsedActivity（含原始 HR 流，不暴露给 LLM）
  - 提供 get / update_set / merge_sets / confirm / clear 操作
  - merge_sets 会从原始 HR 流重新计算合并后时间窗口的 avg_hr / max_hr
"""

from __future__ import annotations

import json
import hmac
import logging
import math
import os
import secrets
import shutil
import threading
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from .atomic_json import atomic_write_json

from fithealth_agent.settings import data_path

from .fit_parser import (
    ActivitySegment, HRRecord, ParsedActivity, ParsedWorkout,
    SessionSummary,
    compute_hr_in_window,
)

logger = logging.getLogger(__name__)

_PERSIST_PATH = data_path("pending_workout.json")
_PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
_INITIAL_PERSIST_PATH = _PERSIST_PATH


def _persist_path() -> Path:
    """Resolve lazily while preserving explicit legacy test overrides."""
    if _PERSIST_PATH != _INITIAL_PERSIST_PATH:
        return _PERSIST_PATH
    path = data_path("pending_workout.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
_PERSIST_VERSION = 2
BEIJING_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")

# ---------------------------------------------------------------------------
# 全局单例（进程内）
# ---------------------------------------------------------------------------
_current: ParsedActivity | None = None
_restored_from_disk = False
_restore_issue: dict[str, Any] | None = None
_current_workout_id: str | None = None
_current_version = 0
_confirmation_token: str | None = None
_confirmation_needs_upgrade = False
# 未修改的解析原件与最近一次有效编辑前状态。两者都随 pending_workout
# 持久化，避免重启后把"可撤销"悄悄变成只能重新上传 FIT。
_parsed_source: ParsedActivity | None = None
_last_edit_snapshot: ParsedActivity | None = None
_state_lock = threading.RLock()


def _synchronized(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with _state_lock:
            return function(*args, **kwargs)

    return wrapped


def _new_confirmation_token() -> str:
    return secrets.token_urlsafe(32)


def _reset_confirmation_state() -> None:
    global _current_workout_id, _current_version, _confirmation_token
    _current_workout_id = None
    _current_version = 0
    _confirmation_token = None


def _bump_version() -> None:
    global _current_version, _confirmation_token
    _current_version += 1
    _confirmation_token = _new_confirmation_token()


@_synchronized
def set_current(workout: ParsedActivity) -> None:
    """将一个新解析的 Activity 设为当前待编辑状态，同时持久化元数据。"""
    global _current, _restored_from_disk, _restore_issue
    global _current_workout_id, _current_version, _confirmation_token
    global _parsed_source, _last_edit_snapshot
    _current = workout
    _parsed_source = _clone_activity(workout)
    _last_edit_snapshot = None
    _restored_from_disk = False
    _restore_issue = None
    _current_workout_id = str(uuid4())
    _current_version = 1
    _confirmation_token = _new_confirmation_token()
    _persist_meta(workout)


def get_current() -> ParsedActivity | None:
    return _current


def was_restored_from_disk() -> bool:
    return _restored_from_disk


def get_restore_issue() -> dict[str, Any] | None:
    """Return a copy of the startup recovery issue, if a corrupt file was found."""
    return dict(_restore_issue) if _restore_issue is not None else None


def _quarantine_files() -> list[Path]:
    persist_path = _persist_path()
    quarantine_dir = persist_path.parent / "workout-quarantine"
    current = list(quarantine_dir.glob("pending_workout.corrupt-*.json")) if quarantine_dir.is_dir() else []
    legacy = list(persist_path.parent.glob("pending_workout.corrupt-*.json"))
    return sorted(current + legacy, reverse=True)


# 「不再提醒」的标记文件后缀。用旁挂标记而不是改名/删除：数据一个字节都不动，
# 用户随时能在数据管理里重新看到它，也能真正删掉。
_DISMISS_SUFFIX = ".dismissed"


def _quarantine_path(name: str) -> Path:
    """把文件名解析成隔离文件路径，并强制归属校验（同 DATA-02 思路）。"""
    candidate = Path(str(name or "")).name
    if not candidate.startswith("pending_workout.corrupt-") or not candidate.endswith(".json"):
        raise ValueError("文件名不是隔离的待确认训练文件")
    persist_path = _persist_path()
    candidates = (persist_path.parent / "workout-quarantine" / candidate, persist_path.parent / candidate)
    path = next((item for item in candidates if item.exists()), candidates[0])
    allowed_parents = {persist_path.parent.resolve(), (persist_path.parent / "workout-quarantine").resolve()}
    if path.resolve().parent not in allowed_parents or not path.exists():
        raise ValueError("隔离文件不存在")
    return path


def dismiss_quarantined(name: str) -> dict[str, Any]:
    """标记「不再提醒」。

    原实现没有任何"已处理"状态：提示只看磁盘上有没有隔离文件，于是用户每次
    进系统都会被同一个弹窗拦一次，点了也没用（重放刻意不删文件）。
    """
    path = _quarantine_path(name)
    marker = path.with_name(path.name + _DISMISS_SUFFIX)
    marker.write_text(
        datetime.now(timezone.utc).isoformat(), encoding="utf-8"
    )
    logger.info("隔离的待确认训练已标记为不再提醒：%s", path.name)
    return {"dismissed": True, "name": path.name}


def delete_quarantined(name: str) -> dict[str, Any]:
    """永久删除一份隔离文件（连同它的不再提醒标记）。"""
    path = _quarantine_path(name)
    marker = path.with_name(path.name + _DISMISS_SUFFIX)
    path.unlink(missing_ok=True)
    marker.unlink(missing_ok=True)
    logger.info("隔离的待确认训练已永久删除：%s", path.name)
    return {"deleted": True, "name": path.name}


def clear_quarantined() -> int:
    files = _quarantine_files()
    for path in files:
        path.unlink(missing_ok=True)
        path.with_name(path.name + _DISMISS_SUFFIX).unlink(missing_ok=True)
    return len(files)


def list_quarantined(include_dismissed: bool = False) -> list[dict[str, Any]]:
    """列出隔离的待确认训练文件，并预判每份能恢复出什么（DATA-05）。

    原实现只在启动时回一句提示文案，既没有列表也没有重放接口，
    合法数据被搬走就等于永久丢失。这里对每份文件做一次只读试恢复，
    让用户在决定重放之前就能看到分段数、心率点数与运动类型。

    默认**跳过已标记「不再提醒」的**，避免启动提示反复打扰；数据管理面板
    传 include_dismissed=True 就能看到全部。
    """
    entries: list[dict[str, Any]] = []
    for path in _quarantine_files():
        dismissed = path.with_name(path.name + _DISMISS_SUFFIX).exists()
        if dismissed and not include_dismissed:
            continue
        entry: dict[str, Any] = {
            "name": path.name,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "recoverable": False,
            "dismissed": dismissed,
            "reason": "",
        }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("根节点必须是对象")
            restored, warnings = _restore_activity(payload, lenient=True)
            start = restored.session.start_time
            entry.update(
                {
                    "recoverable": True,
                    "sport": restored.session.sport,
                    "start_time": start.isoformat() if start else None,
                    "segments": len(restored.segments),
                    "hr_records": len(restored.hr_records),
                    "total_calories": restored.session.total_calories,
                    "avg_hr": restored.session.avg_hr,
                    "max_hr": restored.session.max_hr,
                    "source_file": restored.source_file,
                    "warnings": warnings,
                }
            )
        except (OSError, ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError) as exc:
            entry["reason"] = str(exc) or exc.__class__.__name__
        entries.append(entry)
    return entries


@_synchronized
def replay_quarantined(name: str) -> dict[str, Any]:
    """把一份隔离文件重新载入成当前待确认训练，交回用户走正常确认流程。

    只接受纯文件名并强制归属校验（同 DATA-02 的 resolve_raw_file 思路），
    避免用一个路径参数读到 data 目录之外的文件。
    """
    global _current, _restored_from_disk, _restore_issue
    global _current_workout_id, _current_version, _confirmation_token
    global _confirmation_needs_upgrade

    candidate = _quarantine_path(name).name
    path = _persist_path().parent / candidate
    if _current is not None:
        raise ValueError("当前已有待确认训练，请先确认或清除后再重放")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("根节点必须是对象")
    restored, warnings = _restore_activity(payload, lenient=True)

    _current = restored
    _restored_from_disk = True
    _current_workout_id = str(uuid4())
    _current_version = 1
    _confirmation_token = _new_confirmation_token()
    _confirmation_needs_upgrade = False
    _restore_issue = (
        {
            "code": "PARTIAL_PENDING_WORKOUT",
            "message": "隔离文件已重放，但只能部分恢复，请核对后再确认保存。",
            "reason": "；".join(warnings),
            "action": "restored_partial",
            "quarantine_file": candidate,
        }
        if warnings
        else None
    )
    _persist_meta(restored)
    # 重放过就别再提醒了。文件本身仍保留（重放不是破坏性操作），但用户已经
    # 处理过这一份——原实现不标记，于是每次启动都会被同一个弹窗再拦一次。
    try:
        dismiss_quarantined(candidate)
    except (OSError, ValueError) as exc:
        logger.warning("重放后标记不再提醒失败：%s", exc)
    logger.info(
        "已重放隔离的待确认训练 %s（分段 %d，心率 %d）",
        candidate,
        len(restored.segments),
        len(restored.hr_records),
    )
    return {
        "replayed": True,
        "name": candidate,
        "segments": len(restored.segments),
        "hr_records": len(restored.hr_records),
        "warnings": warnings,
    }


def get_confirmation_context() -> dict[str, Any] | None:
    """Return credentials required by the direct UI confirmation request."""
    if (
        _current is None
        or _current_workout_id is None
        or _current_version < 1
        or _confirmation_token is None
    ):
        return None
    return {
        "workout_id": _current_workout_id,
        "version": _current_version,
        "confirmation_token": _confirmation_token,
    }


@_synchronized
def get_state_snapshot() -> dict[str, Any]:
    """Return one internally consistent API snapshot of the pending state."""
    return {
        "has_workout": _current is not None,
        "workout": _current.to_public_dict() if _current is not None else None,
        "restored": _restored_from_disk if _current is not None else False,
        "restore_issue": dict(_restore_issue) if _restore_issue is not None else None,
        "confirmation": get_confirmation_context(),
        "edit_history": {
            "can_undo": _last_edit_snapshot is not None,
            "can_restore_parsed_source": (
                _current is not None
                and _parsed_source is not None
                and _activity_payload(_current) != _activity_payload(_parsed_source)
            ),
        },
    }


@_synchronized
def clear_current() -> None:
    global _current, _restored_from_disk, _restore_issue
    global _parsed_source, _last_edit_snapshot
    _current = None
    _parsed_source = None
    _last_edit_snapshot = None
    _restored_from_disk = False
    _restore_issue = None
    _reset_confirmation_state()
    _persist_path().unlink(missing_ok=True)


@_synchronized
def reload_from_disk() -> dict[str, Any]:
    """丢掉内存状态，按磁盘上的 `pending_workout.json` 重新载入。

    DATA-11：备份现在**会带上** pending_workout.json，而内存里那份待确认训练
    属于恢复前的世界。恢复备份之后原先调的是 `clear_current()`——在备份不含
    该文件的年代那是对的，现在会把刚恢复回来的待确认训练直接删掉。
    """
    global _current, _restored_from_disk, _restore_issue
    global _confirmation_needs_upgrade, _parsed_source, _last_edit_snapshot
    _current = None
    _restored_from_disk = False
    _restore_issue = None
    _parsed_source = None
    _last_edit_snapshot = None
    _reset_confirmation_state()
    restored = _load_persisted()
    if restored is not None:
        _current = restored
        _restored_from_disk = True
        if _confirmation_needs_upgrade:
            _persist_meta(restored)
            _confirmation_needs_upgrade = False
    return get_state_snapshot()


# ---------------------------------------------------------------------------
# 持久化与恢复
# ---------------------------------------------------------------------------
def _activity_payload(workout: ParsedActivity) -> dict[str, Any]:
    """Serialize a complete activity for pending-state snapshots."""
    return {
        **workout.to_public_dict(),
        "hr_records": [
            {"timestamp": item.timestamp.isoformat(), "heart_rate": item.heart_rate}
            for item in workout.hr_records
        ],
    }


def _clone_activity(workout: ParsedActivity) -> ParsedActivity:
    """Return an independent ParsedActivity without relying on mutable dataclass fields."""
    cloned, _warnings = _restore_activity(_activity_payload(workout), lenient=False)
    return cloned


def _persist_meta(workout: ParsedWorkout) -> None:
    """Persist the complete pending activity so edits remain valid after restart."""
    payload = {
        "version": _PERSIST_VERSION,
        **_activity_payload(workout),
        "confirmation": get_confirmation_context(),
    }
    if _parsed_source is not None:
        payload["parsed_source"] = _activity_payload(_parsed_source)
    if _last_edit_snapshot is not None:
        payload["last_edit_snapshot"] = _activity_payload(_last_edit_snapshot)
    persist_path = _persist_path()
    atomic_write_json(persist_path, payload)


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} 缺失")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _restore_session(data: Any) -> SessionSummary:
    if not isinstance(data, dict):
        raise ValueError("session 格式无效")
    start_time = data.get("start_time")
    return SessionSummary(
        sport=str(data.get("sport") or "未知运动"),
        sport_raw=str(data.get("sport_raw") or "unknown"),
        sub_sport=str(data.get("sub_sport") or ""),
        start_time=_parse_datetime(start_time, "session.start_time") if start_time else None,
        total_elapsed_s=float(data.get("total_elapsed_s") or 0),
        total_timer_s=float(data.get("total_timer_s") or 0),
        total_distance_m=float(data.get("total_distance_m") or 0),
        total_calories=int(data.get("total_calories") or 0),
        avg_hr=int(data["avg_hr"]) if data.get("avg_hr") is not None else None,
        max_hr=int(data["max_hr"]) if data.get("max_hr") is not None else None,
        avg_speed_mps=float(data.get("avg_speed_mps") or 0),
        max_speed_mps=float(data.get("max_speed_mps") or 0),
        avg_cadence=int(data.get("avg_cadence") or 0),
        total_ascent_m=float(data.get("total_ascent_m") or 0),
        total_descent_m=float(data.get("total_descent_m") or 0),
        avg_power_w=int(data.get("avg_power_w") or 0),
        training_effect=float(data.get("training_effect") or 0),
        anaerobic_effect=float(data.get("anaerobic_effect") or 0),
    )


def _restore_segment(data: Any) -> ActivitySegment:
    if not isinstance(data, dict):
        raise ValueError("训练分段格式无效")
    known = {"index", "segment_type", "start_time", "end_time", "duration_s", "category", "category_raw", "repetitions", "weight_kg", "is_rest", "distance_m", "avg_speed_mps", "max_speed_mps", "avg_cadence", "avg_power_w", "calories", "lap_trigger", "avg_hr", "max_hr"}
    extra = {key: value for key, value in data.items() if key not in known}
    return ActivitySegment(
        index=int(data.get("index") or 0),
        segment_type=str(data.get("segment_type") or "lap"),
        start_time=_parse_datetime(data.get("start_time"), "segment.start_time"),
        end_time=_parse_datetime(data.get("end_time"), "segment.end_time"),
        duration_s=float(data.get("duration_s") or 0),
        category=str(data.get("category") or ""),
        category_raw=str(data.get("category_raw") or ""),
        repetitions=int(data.get("repetitions") or 0),
        weight_kg=float(data.get("weight_kg") or 0),
        is_rest=bool(data.get("is_rest", False)),
        distance_m=float(data.get("distance_m") or 0),
        avg_speed_mps=float(data.get("avg_speed_mps") or 0),
        max_speed_mps=float(data.get("max_speed_mps") or 0),
        avg_cadence=int(data.get("avg_cadence") or 0),
        avg_power_w=int(data.get("avg_power_w") or 0),
        calories=int(data.get("calories") or 0),
        lap_trigger=str(data.get("lap_trigger") or ""),
        avg_hr=int(data["avg_hr"]) if data.get("avg_hr") is not None else None,
        max_hr=int(data["max_hr"]) if data.get("max_hr") is not None else None,
        extra=extra,
    )


def _next_corrupt_path() -> Path:
    persist_path = _persist_path()
    quarantine_dir = persist_path.parent / "workout-quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    candidate = quarantine_dir / f"pending_workout.corrupt-{timestamp}.json"
    suffix = 1
    while candidate.exists():
        candidate = quarantine_dir / f"pending_workout.corrupt-{timestamp}-{suffix}.json"
        suffix += 1
    return candidate


def _quarantine_corrupt_persisted(error: Exception) -> dict[str, Any]:
    """Set an unreadable pending state aside so startup will not retry it.

    DATA-05：这里刻意用 **copy 然后 unlink**，而不是 `replace`。
    `replace` 是单向搬走——一旦隔离文件本身有问题，原文件已经不在了。
    copy-then-unlink 保证任何时刻磁盘上至少有一份完整副本；而且只有在副本
    确实写成功之后才会删原件。隔离文件不再是终点：见 list_quarantined /
    replay_quarantined，它们提供了回读与重放的出口。
    """
    reason = str(error) or error.__class__.__name__
    quarantine_path: Path | None = None
    action = "kept"
    try:
        persist_path = _persist_path()
        quarantine_path = _next_corrupt_path()
        shutil.copy2(persist_path, quarantine_path)
        # 副本落盘后才删原件；删不掉也不算失败，隔离已经成立。
        try:
            persist_path.unlink(missing_ok=True)
        except OSError as unlink_error:
            logger.warning("隔离副本已写入，但删除原文件失败：%s", unlink_error)
        action = "quarantined"
    except OSError as quarantine_error:
        logger.error("隔离损坏的待确认训练文件失败：%s", quarantine_error)
        quarantine_path = None
        # 注意：这里**不再删除**原文件。原实现在隔离失败时直接 unlink，
        # 等于把唯一一份数据销毁掉——正是 DATA-05 的成因。留着它，
        # 代价只是每次启动多一条告警，收益是数据还在。
        action = "kept"

    if action == "quarantined":
        message = (
            "上次未确认的训练文件无法读取，系统已隔离该文件且未恢复训练。"
            "可在数据管理中查看隔离文件并尝试重放。"
        )
    else:
        message = (
            "上次未确认的训练文件无法读取，且隔离失败；原文件已保留在 "
            f"{_persist_path().name}，请手动备份后再处理。"
        )

    issue = {
        "code": "CORRUPT_PENDING_WORKOUT",
        "message": message,
        "reason": reason,
        "action": action,
        "quarantine_file": (
            f"workout-quarantine/{quarantine_path.name}"
            if action == "quarantined" and quarantine_path is not None
            else None
        ),
    }
    logger.warning("%s 原因：%s", message, reason)
    return issue


def _restore_activity(payload: dict[str, Any], *, lenient: bool) -> tuple[ParsedActivity, list[str]]:
    """把一份持久化 payload 还原成 ParsedActivity。

    lenient=True 时逐条跳过坏的分段/心率点并把问题记进 warnings，
    只要 session 本身能读出来就算部分可用（DATA-05 的降级路径）。
    """
    warnings: list[str] = []
    version = payload.get("version")
    if version is not None and version != _PERSIST_VERSION:
        raise ValueError(f"不支持的持久化版本：{version}")

    segments_data = payload.get("sets")
    if not isinstance(segments_data, list):
        if not lenient:
            raise ValueError("训练分段格式无效")
        warnings.append("训练分段格式无效，已按空分段恢复")
        segments_data = []

    hr_data = payload.get("hr_records", [])
    if not isinstance(hr_data, list):
        if not lenient:
            raise ValueError("hr_records 格式无效")
        warnings.append("hr_records 格式无效，已按空心率流恢复")
        hr_data = []

    segments: list[ActivitySegment] = []
    for item in segments_data:
        try:
            segments.append(_restore_segment(item))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            if not lenient:
                raise
            warnings.append(f"跳过 1 个无法解析的训练分段：{exc}")

    hr_records: list[HRRecord] = []
    skipped_hr = 0
    for item in hr_data:
        if not isinstance(item, dict) or item.get("heart_rate") is None:
            continue
        try:
            hr_records.append(
                HRRecord(
                    timestamp=_parse_datetime(item.get("timestamp"), "hr.timestamp"),
                    heart_rate=int(item["heart_rate"]),
                )
            )
        except (ValueError, TypeError, OverflowError):
            if not lenient:
                raise
            skipped_hr += 1
    if skipped_hr:
        warnings.append(f"跳过 {skipped_hr} 个无法解析的心率采样点")

    restored = ParsedActivity(
        session=_restore_session(payload.get("session")),
        segments=segments,
        hr_records=hr_records,
        source_file=str(payload.get("source_file") or ""),
        source_sha256=str(payload.get("source_sha256") or ""),
        parsed_at=str(payload.get("parsed_at") or ""),
        note=str(payload.get("note") or ""),
    )
    return restored, warnings


def _load_persisted() -> ParsedActivity | None:
    """Restore version 2 and legacy public-only pending workout files."""
    global _restore_issue
    global _current_workout_id, _current_version, _confirmation_token
    global _confirmation_needs_upgrade, _parsed_source, _last_edit_snapshot
    persist_path = _persist_path()
    if not persist_path.exists():
        return None
    try:
        payload = json.loads(persist_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("根节点必须是对象")
        try:
            restored, warnings = _restore_activity(payload, lenient=False)
        except (ValueError, TypeError, KeyError, OverflowError) as strict_error:
            # DATA-05：严格恢复失败时**先降级为"部分可用"**，只有连 session
            # 都读不出来才隔离。原实现一遇到任何字段问题就整份搬走，
            # 那两个 pending_workout.corrupt-* 文件其实完全合法。
            restored, warnings = _restore_activity(payload, lenient=True)
            warnings.insert(0, f"严格恢复失败，已降级为部分恢复：{strict_error}")
            logger.warning("待确认训练降级恢复：%s", strict_error)
        _restore_partial_warnings = warnings
        # 版本 2 的旧文件没有编辑快照。兼容时以当前已恢复内容作为基线，
        # 之后的编辑仍可撤销；新文件会持久化真正的解析原件。
        source_payload = payload.get("parsed_source")
        if isinstance(source_payload, dict):
            try:
                _parsed_source, _source_warnings = _restore_activity(
                    source_payload, lenient=False
                )
            except (ValueError, TypeError, KeyError, OverflowError):
                logger.warning("待确认训练的解析原件快照无效，已使用当前内容作为恢复基线")
                _parsed_source = _clone_activity(restored)
        else:
            _parsed_source = _clone_activity(restored)

        last_edit_payload = payload.get("last_edit_snapshot")
        if isinstance(last_edit_payload, dict):
            try:
                _last_edit_snapshot, _undo_warnings = _restore_activity(
                    last_edit_payload, lenient=False
                )
            except (ValueError, TypeError, KeyError, OverflowError):
                logger.warning("待确认训练的撤销快照无效，已忽略")
                _last_edit_snapshot = None
        else:
            _last_edit_snapshot = None
        confirmation = payload.get("confirmation")
        if (
            isinstance(confirmation, dict)
            and isinstance(confirmation.get("workout_id"), str)
            and confirmation["workout_id"]
            and isinstance(confirmation.get("version"), int)
            and confirmation["version"] >= 1
            and isinstance(confirmation.get("confirmation_token"), str)
            and len(confirmation["confirmation_token"]) >= 32
        ):
            _current_workout_id = confirmation["workout_id"]
            _current_version = confirmation["version"]
            _confirmation_token = confirmation["confirmation_token"]
            _confirmation_needs_upgrade = False
        else:
            _current_workout_id = str(uuid4())
            _current_version = 1
            _confirmation_token = _new_confirmation_token()
            _confirmation_needs_upgrade = True
        if _restore_partial_warnings:
            _restore_issue = {
                "code": "PARTIAL_PENDING_WORKOUT",
                "message": (
                    "上次未确认的训练只能部分恢复，请核对分段与心率后再确认保存。"
                ),
                "reason": "；".join(_restore_partial_warnings),
                "action": "restored_partial",
                "quarantine_file": None,
            }
        return restored
    except (OSError, ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError) as exc:
        _restore_issue = _quarantine_corrupt_persisted(exc)
        return None


def _restore_on_startup() -> None:
    global _current, _restored_from_disk, _confirmation_needs_upgrade
    restored = _load_persisted()
    if restored is not None:
        _current = restored
        _restored_from_disk = True
        if _confirmation_needs_upgrade:
            _persist_meta(restored)
            _confirmation_needs_upgrade = False


def _validate_confirmation(
    *,
    workout_id: Any,
    version: Any,
    confirmation_token: Any,
) -> dict[str, Any] | None:
    if _current is None:
        return {"error": "当前无待确认的训练数据", "code": "NO_PENDING_WORKOUT"}
    if not isinstance(workout_id, str) or not hmac.compare_digest(
        workout_id, _current_workout_id or ""
    ):
        return {"error": "待确认训练已变化，请刷新后重新确认", "code": "WORKOUT_ID_MISMATCH"}
    if not isinstance(version, int) or isinstance(version, bool) or version != _current_version:
        return {"error": "训练内容已更新，请检查后重新确认", "code": "STALE_WORKOUT_VERSION"}
    if not isinstance(confirmation_token, str) or not hmac.compare_digest(
        confirmation_token, _confirmation_token or ""
    ):
        return {"error": "训练确认凭据无效，请刷新后重试", "code": "INVALID_CONFIRMATION_TOKEN"}
    return None


# ---------------------------------------------------------------------------
# 操作函数
# ---------------------------------------------------------------------------

def _reindex(sets: list[ActivitySegment]) -> list[ActivitySegment]:
    """按 start_time 升序重排序号。"""
    sorted_sets = sorted(sets, key=lambda s: s.start_time)
    for i, s in enumerate(sorted_sets, start=1):
        s.index = i
    return sorted_sets


def _remember_last_edit() -> None:
    """Capture exactly one rollback point before a successful pending-workout edit."""
    global _last_edit_snapshot
    assert _current is not None
    _last_edit_snapshot = _clone_activity(_current)


@_synchronized
def update_set(
    index: int,
    *,
    category: str | None = None,
    weight_kg: float | None = None,
    repetitions: int | None = None,
) -> dict[str, Any]:
    """
    更新指定序号 Set 的字段。

    Args:
        index: 1-based 序号
        category: 新的动作名（中文）
        weight_kg: 新的重量
        repetitions: 新的次数

    Returns:
        更新后的 Set dict，或 {"error": "..."}
    """
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    target = next((s for s in _current.sets if s.index == index), None)
    if target is None:
        return {"error": f"未找到序号 {index} 的动作组"}
    if target.is_rest or target.segment_type != "set_active":
        return {"error": "仅支持编辑力量训练动作组"}

    normalized_category = None
    if category is not None:
        category = category.strip()
        if not category or len(category) > 50:
            return {"error": "动作名称长度应为 1-50 个字符"}
        normalized_category = category
    if weight_kg is not None:
        if not math.isfinite(weight_kg) or not 0 <= weight_kg <= 1000:
            return {"error": "重量应在 0-1000 kg 之间"}
    if repetitions is not None:
        if not 0 <= repetitions <= 10000:
            return {"error": "次数应在 0-10000 之间"}

    _remember_last_edit()
    if normalized_category is not None:
        target.category = normalized_category
        target.category_raw = normalized_category  # 用户自定义，raw 跟随
        target.extra["category_source"] = "user"
    if weight_kg is not None:
        target.weight_kg = weight_kg
    if repetitions is not None:
        target.repetitions = repetitions

    _bump_version()
    _persist_meta(_current)
    return target.to_dict()


@_synchronized
def update_sets(
    updates: list[dict[str, Any]], *, record_undo: bool = True
) -> dict[str, Any]:
    """Validate and apply all editor changes, persisting only after all are valid."""
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    if not isinstance(updates, list):
        return {"error": "训练组修改格式无效"}

    validated: list[tuple[ActivitySegment, str, float, int]] = []
    seen: set[int] = set()
    for position, item in enumerate(updates, start=1):
        if not isinstance(item, dict):
            return {"error": f"第 {position} 项修改格式无效"}
        try:
            index = int(item.get("index", 0))
            category = str(item.get("category") or "").strip()
            weight_kg = float(item.get("weight_kg"))
            repetitions_value = float(item.get("repetitions"))
        except (TypeError, ValueError):
            return {"error": f"第 {position} 项修改参数格式无效"}
        if index in seen:
            return {"error": f"第 {index} 组重复提交"}
        seen.add(index)
        target = next((s for s in _current.segments if s.index == index), None)
        if target is None:
            return {"error": f"未找到序号 {index} 的动作组"}
        if target.is_rest or target.segment_type != "set_active":
            return {"error": f"第 {index} 组不是可编辑的力量训练动作组"}
        if not category or len(category) > 50:
            return {"error": f"第 {index} 组动作名称长度应为 1-50 个字符"}
        if not math.isfinite(weight_kg) or not 0 <= weight_kg <= 1000:
            return {"error": f"第 {index} 组重量应在 0-1000 kg 之间"}
        if not math.isfinite(repetitions_value) or not repetitions_value.is_integer():
            return {"error": f"第 {index} 组次数必须是整数"}
        repetitions = int(repetitions_value)
        if not 0 <= repetitions <= 10000:
            return {"error": f"第 {index} 组次数应在 0-10000 之间"}
        validated.append((target, category, weight_kg, repetitions))

    if validated and record_undo:
        _remember_last_edit()
    for target, category, weight_kg, repetitions in validated:
        target.category = category
        target.category_raw = category
        target.extra["category_source"] = "user"
        target.weight_kg = weight_kg
        target.repetitions = repetitions
    if validated:
        _bump_version()
        _persist_meta(_current)
    return {"updated": True, "sets_count": len(validated)}


@_synchronized
def rename_sets(indices: list[int], category: str) -> dict[str, Any]:
    """Rename selected active sets without changing any measurements."""
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    try:
        clean = str(category).strip()
    except Exception:
        clean = ""
    if not clean or len(clean) > 50:
        return {"error": "动作名称长度应为 1-50 个字符"}
    try:
        wanted = sorted({int(item) for item in indices})
    except (TypeError, ValueError):
        return {"error": "动作组序号格式无效"}
    if not wanted:
        return {"error": "至少选择一个动作组"}
    targets = [next((s for s in _current.segments if s.index == i), None) for i in wanted]
    if any(s is None or s.is_rest or s.segment_type != "set_active" for s in targets):
        return {"error": "只能重命名有效的力量训练动作组"}
    _remember_last_edit()
    for target in targets:
        target.category = clean
        target.category_raw = clean
        target.extra["category_source"] = "user"
    _bump_version()
    _persist_meta(_current)
    return {"updated": True, "sets_count": len(targets)}


def workout_start_beijing(workout: ParsedActivity | None = None) -> datetime | None:
    target = workout or _current
    if target is None:
        return None
    active_starts = [
        segment.start_time
        for segment in target.segments
        if segment.start_time and not segment.is_rest
    ]
    start_times = active_starts or [
        segment.start_time for segment in target.segments if segment.start_time
    ]
    if not start_times and target.session.start_time:
        start_times = [target.session.start_time]
    if not start_times:
        return None
    start = min(start_times)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start.astimezone(BEIJING_TIMEZONE)


@_synchronized
def update_sets_and_confirm(
    updates: list[dict[str, Any]],
    note: str = "",
    *,
    workout_id: Any,
    version: Any,
    confirmation_token: Any,
    overwrite_duplicate: bool = False,
) -> dict[str, Any]:
    """Apply the complete editor draft and save that exact state as one operation."""
    confirmation_error = _validate_confirmation(
        workout_id=workout_id,
        version=version,
        confirmation_token=confirmation_token,
    )
    if confirmation_error is not None:
        return confirmation_error
    assert _current is not None
    editable_indices = {
        segment.index
        for segment in _current.segments
        if not segment.is_rest and segment.segment_type == "set_active"
    }
    try:
        submitted_indices = {int(item.get("index", 0)) for item in updates}
    except (AttributeError, TypeError, ValueError):
        return {"error": "训练组修改格式无效"}
    if editable_indices != submitted_indices:
        missing = sorted(editable_indices - submitted_indices)
        extra = sorted(submitted_indices - editable_indices)
        return {"error": f"训练组提交不完整（缺少 {missing}，多余 {extra}）"}
    note = note.strip()
    if len(note) > 500:
        return {"error": "训练感受不能超过 500 个字符"}
    update_result = update_sets(updates)
    if "error" in update_result:
        return update_result
    _current.note = note
    if not updates:
        _bump_version()
    _persist_meta(_current)
    return _save_confirmed_workout(overwrite_duplicate=overwrite_duplicate)


@_synchronized
def delete_set(index: int) -> dict[str, Any]:
    """Delete one active strength set and reindex the remaining timeline."""
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    target = next((s for s in _current.segments if s.index == index), None)
    if target is None:
        return {"error": f"未找到序号 {index} 的动作组"}
    if target.is_rest or target.segment_type != "set_active":
        return {"error": "仅支持删除力量训练动作组"}

    _remember_last_edit()
    _current.segments = [s for s in _current.segments if s.index != index]
    _current.segments = _reindex(_current.segments)
    _bump_version()
    _persist_meta(_current)
    return {"deleted": True, "index": index}


@_synchronized
def merge_sets(
    indices: list[int],
    updates: list[dict[str, Any]] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """
    合并多个动作组为一个。

    已保存记录的对应算法位于 ``domain/segment_merge.py``。两者目前服务于
    pending 与 saved 两种不同状态，本阶段只搬迁，不在这里合并实现。

    合并规则：
      - start_time = min(start_times)
      - end_time   = max(end_times)
      - duration_s = (end_time - start_time).total_seconds()，包含期间休息
      - 合并时间窗内的休息段会被删除并吸收到新动作时长中
      - 时间窗内若存在未选中的活动动作，则拒绝合并
      - repetitions = sum(repetitions)
      - weight_kg   = max(weight_kg)  # 取最大值，代表主要负重
      - category    = 被合并各组中出现频率最高的动作名
      - avg_hr / max_hr：从原始 HR 流在新时间窗口重新计算

    BUG-11：`updates` 是编辑区当前的完整草稿，**必须在合并之前落到 `_current`
    上**。原先前端只发 `{action:'merge_sets', indices}`，服务端拿自己那份旧数据
    合并、前端随后重渲染，用户没保存的"上斜卧推 80kg"就被静默丢弃了——这正是
    前端要用 `editorBusy` 把合并按钮置灰来回避的东西，而那个置灰又从不复位
    （置位 2 处、复位只在保存/合并/切换记录成功之后），于是按钮永久变灰。
    把编辑一起收下，两个缺陷的根都在这里断掉。

    Args:
        indices: 需要合并的 1-based 序号列表（至少 2 个）
        updates: 编辑区草稿；None 表示没有待应用的编辑（老调用方与 Agent 路径）
        note:    训练感受草稿；None 表示不改动

    Returns:
        合并后的新 Set dict，或 {"error": "..."}
    """
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    indices = list(dict.fromkeys(indices))
    if len(indices) < 2:
        return {"error": "合并至少需要 2 个组"}

    # 先应用编辑再合并：合并要读 category/weight/repetitions 来聚合，顺序反了
    # 聚合出来的就是旧值。`_state_lock` 是 RLock，这里能安全重入。
    if updates:
        # update_sets 会在草稿真正应用前记录撤销点；这一个快照因此能同时
        # 回退草稿编辑和本次合并，用户不会遇到只撤回半次操作的状态。
        update_result = update_sets(updates)
        if "error" in update_result:
            return update_result
    if note is not None:
        note = note.strip()
        if len(note) > 500:
            return {"error": "训练感受不能超过 500 个字符"}
        _current.note = note

    targets = [s for s in _current.sets if s.index in indices]
    if len(targets) != len(indices):
        found = [s.index for s in targets]
        missing = [i for i in indices if i not in found]
        return {"error": f"未找到序号：{missing}"}

    invalid_indices = [
        s.index for s in targets if s.is_rest or s.segment_type != "set_active"
    ]
    if invalid_indices:
        return {"error": f"仅支持合并力量训练动作组（无效序号 {invalid_indices}）"}

    # 时间聚合
    new_start = min(s.start_time for s in targets)
    new_end   = max(s.end_time   for s in targets)
    # Rest segments intersecting the selected window are absorbed. Expand the
    # merged interval to their full bounds; repeat because one expanded edge can
    # touch another rest segment. This keeps the timeline fully covered.
    while True:
        absorbed = [
            segment for segment in _current.segments
            if segment.is_rest
            and segment.start_time < new_end and segment.end_time > new_start
        ]
        expanded_start = min([new_start, *(item.start_time for item in absorbed)])
        expanded_end = max([new_end, *(item.end_time for item in absorbed)])
        if expanded_start == new_start and expanded_end == new_end:
            break
        new_start, new_end = expanded_start, expanded_end
    new_dur = (new_end - new_start).total_seconds()
    window_segments = [
        segment for segment in _current.segments
        if segment.start_time < new_end and segment.end_time > new_start
    ]
    unselected_active = [
        segment.index
        for segment in window_segments
        if not segment.is_rest
        and segment.segment_type == "set_active"
        and segment.index not in indices
    ]
    if unselected_active:
        return {
            "error": (
                "所选动作之间包含未选中的活动组 "
                f"{unselected_active}，请将它们一并选择后再合并"
            )
        }
    absorbed_rest = [segment for segment in window_segments if segment.is_rest]

    if not updates:
        _remember_last_edit()

    # 次数 & 重量
    new_reps   = sum(s.repetitions for s in targets)
    new_weight = max(s.weight_kg   for s in targets)

    # 动作名：频率最高的
    from collections import Counter
    cat_counter = Counter(s.category for s in targets)
    new_category = cat_counter.most_common(1)[0][0]

    # 心率重算（利用原始 HR 流）
    if _current.hr_records:
        avg_hr, max_hr = compute_hr_in_window(_current.hr_records, new_start, new_end)
        hr_note = "已从原始心率数据重新计算"
    else:
        avg_hr, max_hr = None, None
        hr_note = "原始心率数据不可用，心率未重算"

    # 新 Segment（index 暂设为 targets 中最小的，后面 reindex 会修正）
    merged = ActivitySegment(
        index=min(s.index for s in targets),
        segment_type="set_active",
        start_time=new_start,
        end_time=new_end,
        duration_s=new_dur,
        category=new_category,
        category_raw=new_category,
        repetitions=new_reps,
        weight_kg=new_weight,
        is_rest=False,
        avg_hr=avg_hr,
        max_hr=max_hr,
    )

    # 移除旧动作及时间窗内休息，插入覆盖完整时间窗的新动作。
    removed_indices = set(indices) | {segment.index for segment in absorbed_rest}
    _current.segments = [
        segment for segment in _current.segments if segment.index not in removed_indices
    ]
    _current.segments.append(merged)
    _current.segments = _reindex(_current.segments)

    _bump_version()
    _persist_meta(_current)
    return {
        **merged.to_dict(),
        "hr_note": hr_note,
        "merged_from": indices,
        "absorbed_rest_indices": [segment.index for segment in absorbed_rest],
        "absorbed_rest_duration_s": round(sum(segment.duration_s for segment in absorbed_rest), 1),
    }


@_synchronized
def undo_last_edit() -> dict[str, Any]:
    """Restore the state immediately before the last successful edit."""
    global _current, _last_edit_snapshot
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    if _last_edit_snapshot is None:
        return {"error": "没有可撤销的训练编辑"}
    _current = _clone_activity(_last_edit_snapshot)
    _last_edit_snapshot = None
    _bump_version()
    _persist_meta(_current)
    return {"undone": True, "sets_count": len(_current.segments)}


@_synchronized
def restore_parsed_source() -> dict[str, Any]:
    """Discard all pending edits and restore the original parsed FIT activity."""
    global _current, _last_edit_snapshot
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    if _parsed_source is None:
        return {"error": "解析原件快照不可用"}
    if _activity_payload(_current) == _activity_payload(_parsed_source):
        return {"error": "当前训练已是解析原件，无需恢复"}
    _current = _clone_activity(_parsed_source)
    _last_edit_snapshot = None
    _bump_version()
    _persist_meta(_current)
    return {"restored": True, "sets_count": len(_current.segments)}


@_synchronized
def confirm_workout(
    *,
    workout_id: Any,
    version: Any,
    confirmation_token: Any,
    overwrite_duplicate: bool = False,
) -> dict[str, Any]:
    """Save only when the caller presents the current one-time UI credentials."""
    confirmation_error = _validate_confirmation(
        workout_id=workout_id,
        version=version,
        confirmation_token=confirmation_token,
    )
    if confirmation_error is not None:
        return confirmation_error
    return _save_confirmed_workout(overwrite_duplicate=overwrite_duplicate)


def _save_confirmed_workout(*, overwrite_duplicate: bool = False) -> dict[str, Any]:
    """
    将已经通过确定性确认校验的 Segments 写入 DailyRecordStore。
    1Hz 心率流旁挂到 HRStreamStore（记录里只留摘要），随后清空 pending state。

    Returns:
        {"saved": True, "sets_count": N, "date": date} 或 {"error": "..."}
    """
    if _current is None:
        return {"error": "当前无待编辑的训练数据"}
    start_beijing = workout_start_beijing(_current)
    if start_beijing is None:
        return {"error": "训练数据缺少有效的开始时间"}
    derived_date = start_beijing.date().isoformat()
    workout_id = _current_workout_id
    workout_version = _current_version
    if workout_id is None:
        return {"error": "待确认训练缺少标识", "code": "INVALID_PENDING_STATE"}

    # 延迟导入避免循环
    from .storage import DailyRecordStore
    store = DailyRecordStore()

    sport = _current.session.sport if _current.session else "未知运动"
    active_segs = [s for s in _current.segments if not s.is_rest]
    duplicate = store.find_training_by_start(
        date=derived_date, sport=sport, start_time_beijing=start_beijing.isoformat()
    )
    if duplicate is not None:
        existing = duplicate.get("record") if isinstance(duplicate.get("record"), dict) else {}
        # Replaying the exact same FIT remains idempotent. A different import
        # at the same start is a user-visible conflict, not a silent discard.
        if (
            _current.source_sha256
            and existing.get("source_sha256") == _current.source_sha256
        ):
            clear_current()
            return {
                "saved": True,
                "sets_count": len(active_segs),
                "date": derived_date,
                "start_time_beijing": start_beijing.isoformat(),
                "record_id": duplicate["id"],
                "idempotent_replay": True,
                "duplicate_training": True,
            }
        if not overwrite_duplicate:
            return {
                "saved": False,
                "sets_count": len(active_segs),
                "date": derived_date,
                "start_time_beijing": start_beijing.isoformat(),
                "record_id": duplicate["id"],
                "duplicate_training": True,
                "code": "DUPLICATE_TRAINING",
                "message": "Duplicate training found; choose overwrite or keep the existing record.",
                "existing_revision": int(duplicate.get("revision") or 1),
                "confirmation": get_confirmation_context(),
            }

    record: dict[str, Any] = {
        "name":          f"{start_beijing:%y-%m-%d-%H-%M}-{sport}",
        "source_file":   _current.source_file,
        "source_sha256": _current.source_sha256,
        "parsed_at":     _current.parsed_at,
        "sport":         sport,
        "session":       _current.session.to_dict() if _current.session else {},
        "segments":      [s.to_dict() for s in _current.segments],
        "total_sets":    len(active_segs),
        "total_reps":    sum(s.repetitions for s in active_segs),
        "note":          _current.note,
        "workout_start_time_beijing": start_beijing.isoformat(),
        "pending_workout_id": workout_id,
        "pending_workout_version": workout_version,
    }
    existing_record = (
        duplicate.get("record")
        if isinstance(duplicate, dict) and isinstance(duplicate.get("record"), dict)
        else {}
    )
    if not _current.hr_records and isinstance(existing_record.get("hr_stream"), dict):
        # 覆盖导入没有新心率流时保留旧指针；否则整条 record 替换会制造孤儿流。
        record["hr_stream"] = dict(existing_record["hr_stream"])
    # category 字段兼容旧的 DailyRecordStore 格式
    cat_key = "training" if "strength" in sport or "训练" in sport else sport
    if duplicate is not None:
        saved_record, stale = store.update_record_if_revision(
            duplicate["id"],
            expected_revision=int(duplicate.get("revision") or 1),
            date=derived_date,
            category=cat_key,
            record=record,
        )
        if stale:
            return {"error": "The existing training record changed; reload before overwriting.", "code": "STALE_RECORD_REVISION"}
        if saved_record is None:
            return {"error": "The existing training record no longer exists; confirm again.", "code": "DUPLICATE_RECORD_MISSING"}
    else:
        saved_record = store.add_record(
            date=derived_date,
            category=cat_key,
            record=record,
            idempotency_key=(f"fit:{_current.source_sha256}" if _current.source_sha256 else workout_id),
        )

    sets_count = len(active_segs)
    # DATA-05：1Hz 心率流旁挂保存，训练记录里只留体积恒定的摘要。
    # 以前确认时直接丢弃整段流，等于每次保存都损失一份无法再生的原始数据
    # （原始 FIT 通常已经不在磁盘上了）。既不能进 daily_records.json——
    # query_daily_records 会把整条 record 交给 ReAct 观察；也不能进
    # health.db 的 heart_rate_samples——那张表按采样点等权算日均值，
    # 灌进 1Hz 会把训练那一小时加权约 30 倍。
    if _current.hr_records:
        from .hr_stream_store import HRStreamStore

        samples = [
            {"timestamp": item.timestamp.isoformat(), "heart_rate": item.heart_rate}
            for item in _current.hr_records
        ]
        try:
            summary = HRStreamStore().save(saved_record["id"], samples)
            updated = {**record, "hr_stream": summary}
            store.update_record(
                saved_record["id"],
                date=derived_date,
                category=cat_key,
                record=updated,
            )
        except OSError as exc:
            # 心率流是附加价值，写不进去不该让整次确认失败。
            logger.warning("心率流保存失败，训练记录已正常保存：%s", exc)
    clear_current()
    return {
        "saved": True,
        "sets_count": sets_count,
        "date": derived_date,
        "start_time_beijing": start_beijing.isoformat(),
        "record_id": saved_record["id"],
        "idempotent_replay": False,
        "duplicate_training": bool(duplicate is not None),
        "overwritten": bool(duplicate is not None),
    }


_restore_on_startup()
