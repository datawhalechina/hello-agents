"""Training and nutrition record projections with no store access (stage 3d)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fithealth_agent.daily_checkin import CHECKIN_CATEGORY, is_training_record_item
from fithealth_agent.domain.plan_context import extract_iso_dates


def _training_record_name(record: dict, fallback_date: str = "") -> str:
    """Return a stable display name based on the first saved training segment."""
    sport = str(record.get("sport") or "未知训练").strip() or "未知训练"
    start_time = record.get("workout_start_time_beijing")
    if not start_time:
        segments = record.get("segments")
        if isinstance(segments, list):
            starts = [
                str(segment.get("start_time") or "")
                for segment in segments
                if isinstance(segment, dict) and not segment.get("is_rest")
            ]
            start_time = min((value for value in starts if value), default="")
    if isinstance(start_time, str) and start_time:
        try:
            start = datetime.fromisoformat(start_time)
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            start = start.astimezone(ZoneInfo("Asia/Shanghai"))
            return f"{start:%y-%m-%d-%H-%M}-{sport}"
        except ValueError:
            pass
    return f"{fallback_date[2:] if len(fallback_date) == 10 else '未知时间'}-{sport}"


def _record_overview(item: dict) -> dict:
    record = item.get("record") if isinstance(item.get("record"), dict) else {}
    session = record.get("session") if isinstance(record.get("session"), dict) else {}
    segments = record.get("segments") if isinstance(record.get("segments"), list) else []
    total_sets = record.get("total_sets")
    if total_sets is None:
        total_sets = len([segment for segment in segments if not segment.get("is_rest")])
    return {
        "id": item.get("id"),
        "date": item.get("date"),
        "category": item.get("category"),
        "created_at": item.get("created_at"),
        "sport": record.get("sport") or session.get("sport") or item.get("category") or "未知运动",
        "name": record.get("name") or _training_record_name(record, str(item.get("date") or "")),
        "total_sets": total_sets,
        "source_file": record.get("source_file") or "",
        "start_time_beijing": record.get("workout_start_time_beijing") or "",
    }


def _training_record_items(saved_records: list[dict], day: str | None = None) -> list[dict]:
    """Project already-loaded records into the selectable training-record view."""
    records = [
        _record_overview(item)
        for item in saved_records
        if is_training_record_item(item) and (day is None or item.get("date") == day)
    ]
    return sorted(
        records,
        key=lambda item: (
            str(item.get("start_time_beijing") or ""),
            str(item.get("created_at") or ""),
        ),
        reverse=True,
    )


def _requested_record_date(text: str) -> str | None:
    """查记录时用的日期抽取——不做语境门控。"""
    dates = extract_iso_dates(text)
    return dates[0][0].isoformat() if dates else None


def _nutrition_record_items(saved_records: list[dict], day: str | None = None) -> list[dict]:
    """Return one selectable group per photographed meal or manual daily intake."""
    items: list[dict] = []
    for saved in saved_records:
        if saved.get("category") != CHECKIN_CATEGORY:
            continue
        if day is not None and saved.get("date") != day:
            continue
        record = saved.get("record") if isinstance(saved.get("record"), dict) else {}
        meals = record.get("meal_estimates")
        if isinstance(meals, list) and meals:
            for index, meal in enumerate(meals, start=1):
                if not isinstance(meal, dict):
                    continue
                source = str(meal.get("source") or "food_photo_estimate")
                source_name = {
                    "food_photo_estimate": "餐盘照片",
                    "manual_nutrition": "手动营养",
                    "text_nutrition": "文字营养",
                }.get(source, "营养记录")
                items.append({
                    "id": f"{saved.get('id')}::meal::{index}",
                    "record_id": saved.get("id"),
                    "revision": saved.get("revision"),
                    "kind": "meal",
                    "meal_index": index - 1,
                    "date": saved.get("date"),
                    "name": f"{source_name} {index}",
                    "source": source,
                    "confidence": meal.get("confidence"),
                    "total_kcal": meal.get("total_kcal"),
                    "protein_g": meal.get("protein_g"),
                    "carbs_g": meal.get("carbs_g"),
                    "fat_g": meal.get("fat_g"),
                    "range_low_kcal": meal.get("range_low_kcal"),
                    "range_high_kcal": meal.get("range_high_kcal"),
                    "assumptions": meal.get("assumptions") or [],
                    "items": meal.get("items") or [],
                    "user_confirmed": bool(meal.get("user_confirmed")),
                })
            continue
        if any(record.get(field) is not None for field in ("calories_kcal", "protein_g", "carbs_g", "fat_g")):
            nutrition_items = record.get("nutrition_items") if isinstance(record.get("nutrition_items"), list) else []
            meal_slot = str(record.get("meal_slot") or "").strip()
            food_names = "、".join(
                str(item.get("name") or "").strip()
                for item in nutrition_items if isinstance(item, dict) and item.get("name")
            )
            items.append({
                "id": f"{saved.get('id')}::manual",
                "record_id": saved.get("id"),
                "revision": saved.get("revision"),
                "kind": "manual",
                "date": saved.get("date"),
                "name": " · ".join(part for part in (meal_slot, food_names) if part) or "当日手动营养合计",
                "source": record.get("nutrition_source") or record.get("source") or "manual",
                "confidence": "recorded",
                "total_kcal": record.get("calories_kcal"),
                "protein_g": record.get("protein_g"),
                "carbs_g": record.get("carbs_g"),
                "fat_g": record.get("fat_g"),
                "note": record.get("note") or "",
                "items": nutrition_items,
            })
    return sorted(items, key=lambda item: (str(item.get("date") or ""), str(item.get("id") or "")), reverse=True)


def _nutrition_record_date(text: str) -> str | None:
    return _requested_record_date(text)
