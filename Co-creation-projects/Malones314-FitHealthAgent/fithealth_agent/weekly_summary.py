"""Deterministic local summaries for current-week health data queries."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any


WEEK_WORDS = ("本周", "这周", "本星期", "这个星期")
DATA_WORDS = (
    "数据",
    "情况",
    "健康",
    "睡眠",
    "心率",
    "恢复",
    "运动记录",
    "训练记录",
    "总结",
    "汇总",
    "营养",
    "热量",
    "餐食",
    "饮食",
)


def is_current_week_data_query(message: str) -> bool:
    normalized = "".join(message.split())
    query_words = ("查看", "看看", "汇总", "统计", "数据", "列一下", "总结")
    return (
        any(word in normalized for word in WEEK_WORDS)
        and any(word in normalized for word in DATA_WORDS)
        and any(word in normalized for word in query_words)
    )


def _display(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "--"
    if isinstance(value, float):
        value = round(value, 1)
    return f"{value}{suffix}"


def _minutes(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "--"
    total = max(0, int(round(value)))
    return f"{total // 60}小时{total % 60}分"


def build_current_week_reply(
    message: str,
    *,
    health_store: Any,
    daily_record_store: Any,
    profile: dict[str, Any],
    today: date | None = None,
    recovery: Any = None,
    soreness_reports: list[Any] | None = None,
) -> str | None:
    if not is_current_week_data_query(message):
        return None

    end = today or date.today()
    start = end - timedelta(days=end.weekday())
    health_items = health_store.get_health_range(start.isoformat(), end.isoformat())
    records = [
        item
        for item in daily_record_store.list_records()
        if start.isoformat() <= str(item.get("date") or "") <= end.isoformat()
    ]

    lines = [
        f"## 本周数据（{start.isoformat()} 至 {end.isoformat()}）",
        "",
        "| 日期 | 睡眠 | 睡眠分数 | 全天心率 | 压力 | 步数 | HRV |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    available_days = 0
    sleep_durations: list[float] = []
    heart_rate_mins: list[float] = []
    heart_rate_maxes: list[float] = []
    sleep_scores: list[float] = []
    for item in health_items:
        sleep = item.get("sleep") or {}
        heart_rate = item.get("heart_rate") or {}
        stress = item.get("stress") or {}
        activity = item.get("activity") or {}
        hrv = item.get("hrv") or {}
        if any((sleep, heart_rate, stress, activity, hrv)):
            available_days += 1
        if isinstance(sleep.get("duration_min"), (int, float)):
            sleep_durations.append(float(sleep["duration_min"]))
        if isinstance(sleep.get("score"), (int, float)):
            sleep_scores.append(float(sleep["score"]))
        if isinstance(heart_rate.get("min"), (int, float)):
            heart_rate_mins.append(float(heart_rate["min"]))
        if isinstance(heart_rate.get("max"), (int, float)):
            heart_rate_maxes.append(float(heart_rate["max"]))

        hr_text = "--"
        if heart_rate:
            hr_text = (
                f"{_display(heart_rate.get('avg'))} "
                f"({_display(heart_rate.get('min'))}-{_display(heart_rate.get('max'))}) bpm"
            )
        hrv_value = hrv.get("last_night_average")
        if hrv_value is None:
            hrv_value = hrv.get("avg")
        lines.append(
            "| {date} | {sleep} | {score} | {hr} | {stress} | {steps} | {hrv} |".format(
                date=item["date"],
                sleep=_minutes(sleep.get("duration_min")),
                score=_display(sleep.get("score")),
                hr=hr_text,
                stress=_display(stress.get("avg")),
                steps=_display(activity.get("steps")),
                hrv=_display(hrv_value, " ms"),
            )
        )

    lines.extend(["", "### 汇总", ""])
    lines.append(f"- 已导入健康数据：{available_days}/{len(health_items)} 天")
    if sleep_durations:
        lines.append(f"- 有睡眠数据的日期：{len(sleep_durations)} 天，平均 {_minutes(sum(sleep_durations) / len(sleep_durations))}")
    else:
        lines.append("- 睡眠：本周暂无已导入的完整睡眠总结")
    if sleep_scores:
        lines.append(f"- 平均睡眠分数：{round(sum(sleep_scores) / len(sleep_scores), 1)}")
    if heart_rate_mins and heart_rate_maxes:
        lines.append(
            f"- 全天心率范围：{round(min(heart_rate_mins))}-{round(max(heart_rate_maxes))} bpm"
        )
    else:
        lines.append("- 心率：本周暂无有效心率数据")

    categories = Counter(str(item.get("category") or "未分类") for item in records)
    if categories:
        category_text = "、".join(f"{name} {count} 条" for name, count in categories.items())
        lines.append(f"- 每日记录：共 {len(records)} 条（{category_text}）")
    else:
        lines.append("- 每日记录：本周暂无记录")

    training_records = []
    total_sets = 0
    for item in records:
        record = item.get("record")
        if not isinstance(record, dict):
            continue
        segments = record.get("segments")
        if not isinstance(segments, list):
            continue
        training_records.append(item)
        active_sets = [
            segment for segment in segments
            if isinstance(segment, dict)
            and not bool(segment.get("is_rest"))
            and str(segment.get("segment_type") or "") in {"set", "set_active"}
        ]
        total_sets += len(active_sets)
    lines.append(f"- 本周训练：{len(training_records)} 次，共 {total_sets} 个动作组")

    if recovery is not None:
        muscle_capacity: dict[str, float] = {}
        region_capacity: dict[str, float] = {}
        for load in getattr(recovery, "loads", ()):
            capacity = sum(
                float(effective_sets)
                for trained_at, effective_sets, _exercises in getattr(load, "history", ())
                if start <= trained_at.date() <= end
            )
            if capacity <= 0:
                continue
            muscle_capacity[f"{load.region}·{load.zh}"] = round(capacity, 1)
            region_capacity[load.region] = round(
                region_capacity.get(load.region, 0.0) + capacity, 1
            )
        if region_capacity:
            lines.append(
                "- 区域有效容量："
                + "、".join(f"{name} {sets:g} 组" for name, sets in sorted(region_capacity.items()))
            )
            lines.append(
                "- 肌群有效容量："
                + "、".join(f"{name} {sets:g} 组" for name, sets in sorted(muscle_capacity.items()))
            )
        recovering = [
            f"{load.region}·{load.zh}还需 {load.hours_remaining:g} 小时"
            for load in getattr(recovery, "recovering", ())
            if load.hours_remaining > 0
        ]
        if recovering:
            lines.append("- 当前恢复中：" + "；".join(recovering))
        warnings = [warning.message for warning in getattr(recovery, "load_warnings", ())]
        if warnings:
            lines.append("- 累积负荷预警：" + "；".join(warnings))

    active_soreness = []
    for report in soreness_reports or []:
        level = str(getattr(report, "level", ""))
        if level in {"sore", "painful"}:
            label = "疼痛" if level == "painful" else "酸痛"
            active_soreness.append(f"{getattr(report, 'region', '')}{label}")
    if active_soreness:
        lines.append("- 当前主动反馈：" + "、".join(dict.fromkeys(active_soreness)))

    photo_meals: list[dict[str, Any]] = []
    photo_days: set[str] = set()
    manual_meals: list[dict[str, Any]] = []
    manual_days: set[str] = set()
    nutrition_fields = ("calories_kcal", "protein_g", "carbs_g", "fat_g")
    for item in records:
        record = item.get("record")
        if item.get("category") != "daily_checkin" or not isinstance(record, dict):
            continue
        estimates = record.get("meal_estimates")
        saved_estimates = [
            estimate for estimate in estimates
            if isinstance(estimate, dict) and estimate.get("source") == "food_photo_estimate"
        ] if isinstance(estimates, list) else []
        photo_meals.extend(saved_estimates)
        if saved_estimates:
            photo_days.add(str(item.get("date") or ""))
        saved_manual = [
            estimate for estimate in estimates
            if isinstance(estimate, dict)
            and estimate.get("source") in {"manual_nutrition", "text_nutrition", "manual_meal"}
        ] if isinstance(estimates, list) else []
        manual_meals.extend(saved_manual)
        if saved_manual:
            manual_days.add(str(item.get("date") or ""))
        meal_totals = {
            "calories_kcal": sum(float(meal.get("total_kcal") or 0) for meal in [*saved_estimates, *saved_manual]),
            "protein_g": sum(float(meal.get("protein_g") or 0) for meal in [*saved_estimates, *saved_manual]),
            "carbs_g": sum(float(meal.get("carbs_g") or 0) for meal in [*saved_estimates, *saved_manual]),
            "fat_g": sum(float(meal.get("fat_g") or 0) for meal in [*saved_estimates, *saved_manual]),
        }
        residual = {
            field: max(0.0, float(record.get(field) or 0) - meal_totals[field])
            for field in nutrition_fields
        }
        if any(value > 0.1 for value in residual.values()):
            manual_days.add(str(item.get("date") or ""))
            manual_meals.append({
                "total_kcal": residual["calories_kcal"],
                "protein_g": residual["protein_g"],
                "carbs_g": residual["carbs_g"],
                "fat_g": residual["fat_g"],
            })
    if photo_meals:
        total_kcal = sum(float(meal.get("total_kcal") or 0) for meal in photo_meals)
        protein = sum(float(meal.get("protein_g") or 0) for meal in photo_meals)
        carbs = sum(float(meal.get("carbs_g") or 0) for meal in photo_meals)
        fat = sum(float(meal.get("fat_g") or 0) for meal in photo_meals)
        lines.append(
            f"- 餐食来源：图片估算 {len(photo_meals)} 餐/{len(photo_days)} 天（{round(total_kcal)} kcal；"
            f"蛋白质 {round(protein, 1)} g，碳水 {round(carbs, 1)} g，脂肪 {round(fat, 1)} g）"
        )
    if manual_meals:
        total_kcal = sum(float(meal.get("total_kcal") or 0) for meal in manual_meals)
        protein = sum(float(meal.get("protein_g") or 0) for meal in manual_meals)
        carbs = sum(float(meal.get("carbs_g") or 0) for meal in manual_meals)
        fat = sum(float(meal.get("fat_g") or 0) for meal in manual_meals)
        lines.append(
            f"- 餐食来源：文字/手动营养记录 {len(manual_days)} 天（{round(total_kcal)} kcal；"
            f"蛋白质 {round(protein, 1)} g，碳水 {round(carbs, 1)} g，脂肪 {round(fat, 1)} g）"
        )

    weights = profile.get("weekly_weight_kg") or []
    if isinstance(weights, list) and weights:
        numeric_weights = [float(value) for value in weights if isinstance(value, (int, float))]
        if numeric_weights:
            lines.append(
                f"- 档案中的本周体重：{', '.join(str(value) for value in numeric_weights)} kg，"
                f"平均 {round(sum(numeric_weights) / len(numeric_weights), 1)} kg"
            )

    lines.extend(["", "`--` 表示该日没有导入对应数据；汇总只使用已有数据。"])
    return "\n".join(lines)
