"""Pure saved-training segment validation and merge algorithms (stage 3d).

This intentionally remains separate from ``workout_store.merge_sets``: that
code operates on pending workouts, while this module mutates an already-saved
record.  Their aggregation semantics should be reconciled in a separate task.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from fithealth_agent.fit_parser import HRRecord, compute_hr_in_window


def _active_saved_segments(record: dict) -> list[dict]:
    segments = record.get("segments")
    if not isinstance(segments, list):
        return []
    return [
        segment for segment in segments
        if isinstance(segment, dict)
        and not segment.get("is_rest")
        and segment.get("segment_type") == "set_active"
    ]


def _validate_saved_training_updates(record: dict, updates: object) -> str | None:
    if not isinstance(updates, list):
        return "训练组修改必须是数组"
    active_segments = _active_saved_segments(record)
    active_by_index = {segment.get("index"): segment for segment in active_segments}
    submitted_indices = [item.get("index") for item in updates if isinstance(item, dict)]
    if set(submitted_indices) != set(active_by_index):
        return "训练组提交不完整或包含无效序号"
    for item in updates:
        if not isinstance(item, dict):
            return "训练组修改格式无效"
        category = str(item.get("category") or "").strip()
        if not category or len(category) > 50:
            return "动作名称不能为空且不能超过 50 个字符"
        try:
            weight = float(item.get("weight_kg"))
            repetitions = int(item.get("repetitions"))
        except (TypeError, ValueError):
            return "重量或次数格式无效"
        if not 0 <= weight <= 1000 or not 0 <= repetitions <= 10000:
            return "重量或次数超出允许范围"
        if weight == 0 and repetitions == 0:
            return "重量和次数不能同时为 0"
    return None


_ADDITIVE_SEGMENT_FIELDS = ("distance_m", "calories")
_PEAK_SEGMENT_FIELDS = ("max_speed_mps",)
_WEIGHTED_SEGMENT_FIELDS = ("avg_cadence", "avg_power_w")


def _weighted_average(pairs: list[tuple[float, float]]) -> float | None:
    """按权重求加权平均；权重全为 0 时退回算术平均，无可用值时返回 None。"""
    values = [value for value, _ in pairs]
    if not values:
        return None
    usable = [(value, weight) for value, weight in pairs if weight > 0]
    total_weight = sum(weight for _, weight in usable)
    if not usable or total_weight <= 0:
        return sum(values) / len(values)
    return sum(value * weight for value, weight in usable) / total_weight


def _segment_numbers(segments: list[dict], field: str) -> list[tuple[float, float]]:
    """取出某个字段的 (值, 时长) 对，跳过缺失与非数值。"""
    pairs: list[tuple[float, float]] = []
    for segment in segments:
        value = segment.get(field)
        if value is None or isinstance(value, bool):
            continue
        try:
            pairs.append((float(value), float(segment.get("duration_s") or 0)))
        except (TypeError, ValueError):
            continue
    return pairs


def _merged_segment_hr(
    targets: list[dict], *, start: datetime, end: datetime, hr_samples: list[dict] | None
) -> tuple[int | None, int | None, str]:
    """Recompute HR from the sidecar stream, then fall back to segment aggregates."""
    if hr_samples:
        records: list[HRRecord] = []
        for sample in hr_samples:
            if not isinstance(sample, dict):
                continue
            stamp = sample.get("timestamp")
            beats = sample.get("heart_rate")
            if not isinstance(stamp, str) or beats is None:
                continue
            try:
                records.append(HRRecord(datetime.fromisoformat(stamp), int(beats)))
            except (TypeError, ValueError):
                continue
        if records:
            average, peak = compute_hr_in_window(records, start, end)
            if average is not None:
                return average, peak, "已从旁挂的原始心率流在新时间窗内精确重算心率"
    averages = _segment_numbers(targets, "avg_hr")
    peaks = [value for value, _ in _segment_numbers(targets, "max_hr")]
    weighted = _weighted_average(averages)
    if weighted is None and not peaks:
        return None, None, "被合并的各组都没有心率数据，合并后心率为空"
    return (
        round(weighted) if weighted is not None else None,
        round(max(peaks)) if peaks else None,
        "无原始心率流，已按各组时长加权还原平均心率、峰值取各组最大值",
    )


def _merged_segment_numbers(targets: list[dict], *, duration_s: float) -> dict[str, object]:
    """Aggregate only numeric fields that occur on at least one selected segment."""
    merged: dict[str, object] = {}
    for field in _ADDITIVE_SEGMENT_FIELDS:
        pairs = _segment_numbers(targets, field)
        if pairs:
            total = sum(value for value, _ in pairs)
            merged[field] = int(round(total)) if field == "calories" else round(total, 1)
    for field in _PEAK_SEGMENT_FIELDS:
        pairs = _segment_numbers(targets, field)
        if pairs:
            merged[field] = round(max(value for value, _ in pairs), 3)
    for field in _WEIGHTED_SEGMENT_FIELDS:
        average = _weighted_average(_segment_numbers(targets, field))
        if average is not None:
            merged[field] = int(round(average))
    speed_pairs = _segment_numbers(targets, "avg_speed_mps")
    if speed_pairs:
        distance = merged.get("distance_m")
        if isinstance(distance, (int, float)) and distance > 0 and duration_s > 0:
            merged["avg_speed_mps"] = round(float(distance) / duration_s, 3)
        else:
            average = _weighted_average(speed_pairs)
            if average is not None:
                merged["avg_speed_mps"] = round(average, 3)
    return merged


def _merge_saved_training_segments(
    record: dict, indices: object, *, hr_samples: list[dict] | None = None
) -> tuple[bool, str]:
    if not isinstance(indices, list):
        return False, "合并序号格式无效"
    try:
        selected = list(dict.fromkeys(int(index) for index in indices))
    except (TypeError, ValueError):
        return False, "合并序号格式无效"
    if len(selected) < 2:
        return False, "合并至少需要选择 2 组"
    active_by_index = {segment.get("index"): segment for segment in _active_saved_segments(record)}
    if any(index not in active_by_index for index in selected):
        return False, "只能合并当前训练中的力量动作组"
    targets = [active_by_index[index] for index in selected]
    try:
        start = min(datetime.fromisoformat(str(segment["start_time"])) for segment in targets)
        end = max(datetime.fromisoformat(str(segment["end_time"])) for segment in targets)
    except (KeyError, ValueError):
        return False, "训练组缺少有效时间，无法合并"
    segments = record.get("segments")
    if not isinstance(segments, list):
        return False, "训练记录格式无效"
    in_window = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        try:
            segment_start = datetime.fromisoformat(str(segment["start_time"]))
            segment_end = datetime.fromisoformat(str(segment["end_time"]))
        except (KeyError, ValueError):
            continue
        if segment_start >= start and segment_end <= end:
            in_window.append(segment)
    unselected_active = [
        segment.get("index") for segment in in_window
        if not segment.get("is_rest")
        and segment.get("segment_type") == "set_active"
        and segment.get("index") not in selected
    ]
    if unselected_active:
        return False, f"所选动作之间包含未选择的活动组 {unselected_active}"
    categories = [str(segment.get("category") or "未命名动作") for segment in targets]
    duration_s = round((end - start).total_seconds(), 1)
    avg_hr, max_hr, hr_note = _merged_segment_hr(targets, start=start, end=end, hr_samples=hr_samples)
    merged = {
        **targets[0],
        "index": min(selected),
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_s": duration_s,
        "category": Counter(categories).most_common(1)[0][0],
        "category_raw": Counter(categories).most_common(1)[0][0],
        "repetitions": sum(int(segment.get("repetitions") or 0) for segment in targets),
        "weight_kg": max(float(segment.get("weight_kg") or 0) for segment in targets),
        **_merged_segment_numbers(targets, duration_s=duration_s),
        "avg_hr": avg_hr,
        "max_hr": max_hr,
    }
    removed_indices = {segment.get("index") for segment in in_window}
    record["segments"] = [
        segment for segment in segments
        if not isinstance(segment, dict) or segment.get("index") not in removed_indices
    ]
    record["segments"].append(merged)
    record["segments"].sort(key=lambda segment: str(segment.get("start_time") or ""))
    for index, segment in enumerate(record["segments"], start=1):
        if isinstance(segment, dict):
            segment["index"] = index
    record["total_sets"] = len(_active_saved_segments(record))
    record["total_reps"] = sum(
        int(segment.get("repetitions") or 0) for segment in _active_saved_segments(record)
    )
    return True, hr_note
