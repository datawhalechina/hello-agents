"""Resource-scoped HTTP routes extracted from main."""

from datetime import date, timedelta
from typing import Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent import workout_store
from fithealth_agent.daily_checkin import CHECKIN_CATEGORY, is_training_record_item, validate_daily_checkin, validate_daily_checkin_update
from fithealth_agent.domain.record_view import _nutrition_record_items as _project_nutrition_record_items, _training_record_items as _project_training_record_items, _training_record_name
from fithealth_agent.domain.segment_merge import _active_saved_segments, _merge_saved_training_segments, _validate_saved_training_updates
from fithealth_agent.runtime import deps
from fithealth_agent.runtime.deps import _verified_analysis_confidence
from fithealth_agent.workflows.chat_workflow import _soreness_report_payload

router = APIRouter()

checkins_router = APIRouter()

delete_router = APIRouter()

def _training_record_items(day: str | None = None) -> list[dict]:
    return _project_training_record_items(
        deps.daily_record_store.list_records(), day
    )

def _nutrition_record_items(day: str | None = None) -> list[dict]:
    return _project_nutrition_record_items(
        deps.daily_record_store.list_records(), day
    )

@router.get("/data/training-records")
def list_training_records(day: str | None = None) -> JSONResponse:
    if day is not None:
        try:
            day = date.fromisoformat(day).isoformat()
        except ValueError:
            return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)
    return JSONResponse({"items": _training_record_items(day)})

@router.get("/data/training-records/{record_id}")
def get_training_record(record_id: str) -> JSONResponse:
    item = next(
        (record for record in deps.daily_record_store.list_records() if record.get("id") == record_id),
        None,
    )
    if item is None or not is_training_record_item(item):
        return JSONResponse({"error": "未找到训练记录"}, status_code=404)
    result = dict(item)
    record = dict(result.get("record") or {})
    record["name"] = record.get("name") or _training_record_name(
        record, str(result.get("date") or "")
    )
    result["record"] = record
    return JSONResponse(result)

@router.get("/data/nutrition-records")
def list_nutrition_records(day: str | None = None) -> JSONResponse:
    if day is not None:
        try:
            day = date.fromisoformat(day).isoformat()
        except ValueError:
            return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)
    return JSONResponse({"items": _nutrition_record_items(day)})

def _nutrition_group_target(group_id: str) -> tuple[dict | None, str, int | None]:
    """Resolve a public nutrition-group id without exposing arbitrary records."""
    parts = group_id.split("::")
    if len(parts) == 2 and parts[1] == "manual":
        record_id, kind, meal_index = parts[0], "manual", None
    elif len(parts) == 3 and parts[1] == "meal":
        try:
            meal_index = int(parts[2]) - 1
        except ValueError:
            return None, "", None
        record_id, kind = parts[0], "meal"
    else:
        return None, "", None
    saved = next(
        (
            item
            for item in deps.daily_record_store.list_records()
            if item.get("id") == record_id and item.get("category") == CHECKIN_CATEGORY
        ),
        None,
    )
    return saved, kind, meal_index

def _nutrition_group_after_save(group_id: str, day: str) -> dict | None:
    return next(
        (item for item in _nutrition_record_items(day) if item.get("id") == group_id),
        None,
    )

@router.patch("/data/nutrition-records/{group_id}")
def update_nutrition_record(group_id: str, payload: dict) -> JSONResponse:
    saved_item, kind, meal_index = _nutrition_group_target(group_id)
    if saved_item is None:
        return JSONResponse({"error": "未找到营养记录"}, status_code=404)
    expected_revision = payload.get("revision")
    if not isinstance(expected_revision, int) or expected_revision < 1:
        return JSONResponse({"error": "缺少有效的营养记录版本"}, status_code=400)

    record = dict(saved_item.get("record") or {})
    day = str(saved_item.get("date") or "")
    try:
        if kind == "manual":
            numeric_fields = ("calories_kcal", "protein_g", "carbs_g", "fat_g")
            validation_payload: dict[str, Any] = {"date": day}
            for field in numeric_fields:
                if field in payload and payload[field] not in (None, ""):
                    validation_payload[field] = payload[field]
            if len(validation_payload) > 1:
                _, validated = validate_daily_checkin(validation_payload)
            else:
                validated = {}
            for field in numeric_fields:
                if field not in payload:
                    continue
                if payload[field] in (None, ""):
                    record.pop(field, None)
                else:
                    record[field] = validated[field]
            if "note" in payload:
                note = str(payload.get("note") or "").strip()
                if len(note) > 500:
                    raise ValueError("备注不能超过 500 个字符")
                if note:
                    record["note"] = note
                else:
                    record.pop("note", None)
            if not any(record.get(field) is not None for field in numeric_fields):
                raise ValueError("营养组至少需要保留一项营养数据")
        else:
            meals = record.get("meal_estimates")
            if (
                not isinstance(meals, list)
                or meal_index is None
                or meal_index < 0
                or meal_index >= len(meals)
                or not isinstance(meals[meal_index], dict)
            ):
                return JSONResponse({"error": "未找到营养记录"}, status_code=404)
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("餐食至少需要保留一个食物项目")
            try:
                total_kcal = sum(float(item.get("calories_kcal")) for item in items)
                protein_g = sum(float(item.get("protein_g")) for item in items)
                carbs_g = sum(float(item.get("carbs_g")) for item in items)
                fat_g = sum(float(item.get("fat_g")) for item in items)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError("食物项目营养数据必须是数字") from exc
            old_meal = meals[meal_index]
            corrected_meal = {
                **old_meal,
                "source": old_meal.get("source") or "food_photo_estimate",
                "items": items,
                "total_kcal": total_kcal,
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "range_low_kcal": total_kcal,
                "range_high_kcal": total_kcal,
                "confidence": "high",
                "user_confirmed": True,
            }
            _, validated = validate_daily_checkin({
                "date": day,
                "meal_estimates": [corrected_meal],
            })
            corrected_meal = validated["meal_estimates"][0]
            meals = list(meals)
            meals[meal_index] = corrected_meal
            record["meal_estimates"] = meals
            totals = (
                ("calories_kcal", "total_kcal", True),
                ("protein_g", "protein_g", False),
                ("carbs_g", "carbs_g", False),
                ("fat_g", "fat_g", False),
            )
            for daily_field, meal_field, integer in totals:
                old_value = float(old_meal.get(meal_field) or 0)
                new_value = float(corrected_meal.get(meal_field) or 0)
                base = float(record.get(daily_field) or 0)
                adjusted = max(0, base - old_value + new_value)
                record[daily_field] = int(round(adjusted)) if integer else round(adjusted, 1)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    updated, stale = deps.daily_record_store.update_record_if_revision(
        str(saved_item.get("id") or ""),
        expected_revision=expected_revision,
        date=day,
        category=CHECKIN_CATEGORY,
        record=record,
    )
    if stale:
        return JSONResponse(
            {"error": "营养记录已在其他页面被修改，请重新加载后再保存", "code": "STALE_RECORD_REVISION"},
            status_code=409,
        )
    if updated is None:
        return JSONResponse({"error": "未找到营养记录"}, status_code=404)
    group = _nutrition_group_after_save(group_id, day)
    return JSONResponse({"updated": True, "record": group})

@router.delete("/data/nutrition-records/{group_id}")
def delete_nutrition_record(group_id: str, payload: dict) -> JSONResponse:
    saved_item, kind, meal_index = _nutrition_group_target(group_id)
    if saved_item is None:
        return JSONResponse({"error": "未找到营养记录"}, status_code=404)
    expected_revision = payload.get("revision")
    if not isinstance(expected_revision, int) or expected_revision < 1:
        return JSONResponse({"error": "缺少有效的营养记录版本"}, status_code=400)

    record = dict(saved_item.get("record") or {})
    day = str(saved_item.get("date") or "")
    nutrient_fields = ("calories_kcal", "protein_g", "carbs_g", "fat_g")
    if kind == "manual":
        for field in nutrient_fields:
            record.pop(field, None)
        for field in ("nutrition_source", "nutrition_items", "meal_slot"):
            record.pop(field, None)
    else:
        meals = record.get("meal_estimates")
        if (
            not isinstance(meals, list)
            or meal_index is None
            or meal_index < 0
            or meal_index >= len(meals)
            or not isinstance(meals[meal_index], dict)
        ):
            return JSONResponse({"error": "未找到营养记录"}, status_code=404)
        removed_meal = meals[meal_index]
        remaining_meals = [*meals[:meal_index], *meals[meal_index + 1:]]
        if remaining_meals:
            record["meal_estimates"] = remaining_meals
        else:
            record.pop("meal_estimates", None)
            record.pop("nutrition_source", None)
        for daily_field, meal_field, integer in (
            ("calories_kcal", "total_kcal", True),
            ("protein_g", "protein_g", False),
            ("carbs_g", "carbs_g", False),
            ("fat_g", "fat_g", False),
        ):
            adjusted = max(
                0.0,
                float(record.get(daily_field) or 0) - float(removed_meal.get(meal_field) or 0),
            )
            if adjusted <= 0.05:
                record.pop(daily_field, None)
            else:
                record[daily_field] = int(round(adjusted)) if integer else round(adjusted, 1)

    updated, stale = deps.daily_record_store.update_record_if_revision(
        str(saved_item.get("id") or ""),
        expected_revision=expected_revision,
        date=day,
        category=CHECKIN_CATEGORY,
        record=record,
    )
    if stale:
        return JSONResponse(
            {"error": "营养记录已在其他页面被修改，请重新加载后再删除", "code": "STALE_RECORD_REVISION"},
            status_code=409,
        )
    if updated is None:
        return JSONResponse({"error": "未找到营养记录"}, status_code=404)
    return JSONResponse({"deleted": True, "id": group_id, "date": day})

@router.patch("/data/training-records/{record_id}")
def update_training_record(record_id: str, payload: dict) -> JSONResponse:
    item = next(
        (record for record in deps.daily_record_store.list_records() if record.get("id") == record_id),
        None,
    )
    if item is None or not is_training_record_item(item):
        return JSONResponse({"error": "未找到训练记录"}, status_code=404)
    expected_revision = payload.get("revision")
    if not isinstance(expected_revision, int) or expected_revision < 1:
        return JSONResponse({"error": "缺少有效的训练记录版本"}, status_code=400)
    record = dict(item.get("record") or {})
    updates = payload.get("updates")
    validation_error = _validate_saved_training_updates(record, updates)
    if validation_error:
        return JSONResponse({"error": validation_error}, status_code=400)
    update_by_index = {int(update["index"]): update for update in updates}
    for segment in _active_saved_segments(record):
        update = update_by_index[int(segment["index"])]
        segment["category"] = str(update["category"]).strip()
        segment["category_raw"] = segment["category"]
        segment["weight_kg"] = float(update["weight_kg"])
        segment["repetitions"] = int(update["repetitions"])
    rename_indices = payload.get("rename_indices")
    rename_category = str(payload.get("rename_category") or "").strip()
    if rename_indices is not None:
        try:
            rename_indices = sorted({int(index) for index in rename_indices})
        except (TypeError, ValueError):
            return JSONResponse({"error": "重命名序号格式无效"}, status_code=400)
        if not rename_indices or not rename_category or len(rename_category) > 50:
            return JSONResponse({"error": "动作名称长度应为 1-50 个字符且至少选择一组"}, status_code=400)
        active = {int(segment["index"]): segment for segment in _active_saved_segments(record)}
        if any(index not in active for index in rename_indices):
            return JSONResponse({"error": "只能重命名有效的力量训练动作组"}, status_code=400)
        for index in rename_indices:
            segment = active[index]
            segment["category"] = rename_category
            segment["category_raw"] = rename_category
            segment["category_source"] = "user"
    note = str(payload.get("note") or "").strip()
    if len(note) > 500:
        return JSONResponse({"error": "训练感受不能超过 500 个字符"}, status_code=400)
    record["note"] = note
    merge_indices = payload.get("merge_indices")
    notice = ""
    if merge_indices is not None:
        # DATA-13：把旁挂的 1Hz 心率流一并交进去，能精确重算就别用加权近似。
        merged, notice = _merge_saved_training_segments(
            record, merge_indices, hr_samples=deps.hr_stream_store.load(record_id)
        )
        if not merged:
            return JSONResponse({"error": notice}, status_code=400)
    record["name"] = _training_record_name(record, str(item.get("date") or ""))
    saved, stale = deps.daily_record_store.update_record_if_revision(
        record_id,
        expected_revision=expected_revision,
        date=str(item.get("date") or ""),
        category=str(item.get("category") or "training"),
        record=record,
    )
    if stale:
        return JSONResponse(
            {"error": "训练记录已在其他页面被修改，请重新加载后再保存", "code": "STALE_RECORD_REVISION"},
            status_code=409,
        )

    if saved is None:
        return JSONResponse({"error": "未找到训练记录"}, status_code=404)
    return JSONResponse({"updated": True, "record": saved, "notice": notice})

@router.get("/data/overview")
def data_overview() -> JSONResponse:
    deps.info_store.cleanup_expired()
    pending = workout_store.get_current()
    profile = deps.profile_store.get_profile()
    return JSONResponse(
        {
            "records": _training_record_items(),
            "daily_records": [
                {
                    "id": item.get("id"), "date": item.get("date"),
                    "category": item.get("category"), "created_at": item.get("created_at"),
                    "record": item.get("record") if isinstance(item.get("record"), dict) else {},
                }
                for item in deps.daily_record_store.list_records()
                if not is_training_record_item(item)
            ],
            "plans": [
                {key: item.get(key) for key in ("id", "date", "subject", "filename", "title", "memo", "content", "source", "created_at", "updated_at")}
                for item in deps.plan_store.list_plans()
            ],
            "memories": deps.info_store.get_all(),
            "soreness_reports": [
                _soreness_report_payload(item) for item in deps.soreness_store.list_reports()
            ],
            "health_imports": deps.health_store.list_imports(),
            "profile": profile,
            "profile_complete": deps.profile_store.is_complete(profile),
            "has_pending_workout": pending is not None,
            "pending_source": pending.source_file if pending else "",
        }
    )

@checkins_router.get("/data/checkins/{day}")
def get_daily_checkin(day: str) -> JSONResponse:
    """返回某天已有的打卡记录，供表单预填。

    没有记录时返回 `{"checkin": null}` 而不是 404——"这天还没打卡"是正常状态，
    不是错误，前端不该为此走异常分支。
    """
    try:
        day = date.fromisoformat(day).isoformat()
    except ValueError:
        return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)
    item = next(
        (
            record
            for record in deps.daily_record_store.list_records()
            if record.get("date") == day and record.get("category") == CHECKIN_CATEGORY
        ),
        None,
    )
    if item is None:
        return JSONResponse({"checkin": None, "date": day})
    return JSONResponse({"checkin": item.get("record") or {}, "date": day, "id": item.get("id")})

@checkins_router.post("/data/checkins")
def save_daily_checkin(payload: dict) -> JSONResponse:
    """保存当天的手动记录；同一天重复保存是**更新**而不是再加一条。

    BUG-09：原实现直接 `add_record`，每次生成新 uuid 追加，同一天点两次保存就
    并列出两条 daily_checkin；而 `PATCH /data/checkins/{record_id}` 前端零调用，
    是完全不可达的死端点，于是"改一下今天的体重"这件事根本做不到。

    去重放在 store 的 `upsert_dated_record` 里而不是这里先查后写：查重与写入必须
    在同一把锁内，否则两个并发请求会同时判定"当日无记录"，各自追加一条。
    """
    candidate_payload = dict(payload)
    incoming_meals = candidate_payload.get("meal_estimates")
    if isinstance(incoming_meals, list):
        try:
            requested_date = date.fromisoformat(str(candidate_payload.get("date") or "")).isoformat()
        except ValueError:
            requested_date = ""
        existing_photo_meals = []
        for saved in deps.daily_record_store.list_records():
            if saved.get("date") != requested_date or saved.get("category") != CHECKIN_CATEGORY:
                continue
            record = saved.get("record") if isinstance(saved.get("record"), dict) else {}
            existing_photo_meals = [
                item for item in record.get("meal_estimates", [])
                if isinstance(item, dict) and item.get("source") == "food_photo_estimate"
            ]
            break
        normalized_meals = []
        for meal in incoming_meals:
            if not isinstance(meal, dict) or meal.get("source") != "food_photo_estimate":
                normalized_meals.append(meal)
                continue
            copy = dict(meal)
            token = str(copy.get("analysis_token") or "")
            signed_confidence = _verified_analysis_confidence(token)
            if signed_confidence is not None:
                copy["confidence"] = signed_confidence
            elif copy not in existing_photo_meals:
                return JSONResponse({"error": "餐盘照片估算缺少有效的服务端签名，请重新分析照片"}, status_code=400)
            normalized_meals.append(copy)
        candidate_payload["meal_estimates"] = normalized_meals
    try:
        record_date, record, cleared = validate_daily_checkin_update(candidate_payload)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    item, created, folded = deps.daily_record_store.upsert_dated_record(
        record_date, CHECKIN_CATEGORY, record, clear_fields=tuple(cleared)
    )
    if "weight_kg" in payload:
        recorded_day = date.fromisoformat(record_date)
        week_start = recorded_day - timedelta(days=recorded_day.weekday())
        week_end = week_start + timedelta(days=6)
        weights_by_day: dict[str, float] = {}
        for saved in deps.daily_record_store.list_records():
            saved_record = saved.get("record")
            saved_day = str(saved.get("date") or "")
            if (
                saved.get("category") == CHECKIN_CATEGORY
                and week_start.isoformat() <= saved_day <= week_end.isoformat()
                and isinstance(saved_record, dict)
                and isinstance(saved_record.get("weight_kg"), (int, float))
            ):
                weights_by_day[saved_day] = float(saved_record["weight_kg"])
        deps.profile_store.update_profile({
            "weekly_weight_kg": [weights_by_day[day] for day in sorted(weights_by_day)]
        })
    body = {**item, "created": created, "updated": not created}
    if folded:
        # 磁盘上原有的重复记录已被折叠成一条。明说，别让"记录数少了"看着像丢数据。
        body["folded_duplicates"] = folded
        body["notice"] = f"已合并该日期下之前重复保存的 {folded} 条记录。"
    return JSONResponse(body)

@delete_router.delete("/data/records/{record_id}")
def delete_record(record_id: str) -> JSONResponse:
    item = next(
        (record for record in deps.daily_record_store.list_records() if record.get("id") == record_id),
        None,
    )
    if item is None:
        return JSONResponse({"error": "未找到该记录"}, status_code=404)
    if not deps.daily_record_store.delete_record(record_id):
        return JSONResponse({"error": "未找到该记录"}, status_code=404)
    # 旁挂的 1Hz 心率流跟着记录一起删，避免留下引用不到的孤儿文件（DATA-02 的教训）
    if is_training_record_item(item):
        deps.hr_stream_store.delete(record_id)
    return JSONResponse({"deleted": True, "id": record_id})

@delete_router.post("/data/records/delete-batch")
def delete_records_batch(payload: dict) -> JSONResponse:
    record_ids = payload.get("ids")
    if not isinstance(record_ids, list) or not record_ids:
        return JSONResponse({"error": "请选择需要删除的训练记录"}, status_code=400)
    normalized = list(dict.fromkeys(str(item).strip() for item in record_ids if str(item).strip()))
    if not normalized:
        return JSONResponse({"error": "训练记录 ID 无效"}, status_code=400)
    existing_ids = {
        str(item.get("id"))
        for item in deps.daily_record_store.list_records()
    }
    allowed = [record_id for record_id in normalized if record_id in existing_ids]
    if not allowed:
        return JSONResponse({"error": "未找到可删除的记录"}, status_code=404)
    removed = deps.daily_record_store.delete_records(allowed)
    for record_id in allowed:
        deps.hr_stream_store.delete(record_id)
    return JSONResponse({"deleted": removed})

