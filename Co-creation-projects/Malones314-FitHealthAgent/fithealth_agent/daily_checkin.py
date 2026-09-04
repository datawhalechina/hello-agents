"""Validation for structured manual daily health records."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


CHECKIN_CATEGORY = "daily_checkin"
BEIJING = ZoneInfo("Asia/Shanghai")

_NUMBER_FIELDS = {
    "weight_kg": (20, 350),
    "energy_level": (1, 10),
    "fatigue_level": (1, 10),
    "pain_level": (0, 10),
    "sleep_quality": (1, 10),
    "calories_kcal": (0, 20000),
    "protein_g": (0, 1000),
    "carbs_g": (0, 2000),
    "fat_g": (0, 1000),
    "training_rpe": (1, 10),
    "training_completion_pct": (0, 100),
}

_MEAL_SOURCES = frozenset({"food_photo_estimate", "manual_nutrition", "text_nutrition", "manual_meal"})
_MEAL_NUMBERS = {
    "total_kcal": (0, 20_000, True),
    "protein_g": (0, 1_000, False),
    "carbs_g": (0, 2_000, False),
    "fat_g": (0, 1_000, False),
    "range_low_kcal": (0, 20_000, True),
    "range_high_kcal": (0, 20_000, True),
}


def _meal_number(value: Any, field: str) -> int | float:
    minimum, maximum, integer = _MEAL_NUMBERS[field]
    if isinstance(value, bool):
        raise ValueError(f"meal_estimates.{field} 必须是数字")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"meal_estimates.{field} 必须是数字") from exc
    if not minimum <= numeric <= maximum:
        raise ValueError(f"meal_estimates.{field} 必须在 {minimum}-{maximum} 之间")
    return int(round(numeric)) if integer else round(numeric, 1)


def _validate_meal_estimates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("meal_estimates 必须是 0-20 条餐食估算")
    meals: list[dict[str, Any]] = []
    for meal in value:
        if not isinstance(meal, dict) or meal.get("source") not in _MEAL_SOURCES:
            raise ValueError("meal_estimates 来源无效")
        items = meal.get("items")
        if not isinstance(items, list) or not items or len(items) > 12:
            raise ValueError("每条餐食估算必须有 1-12 个食物项目")
        normalized_items: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("餐食项目格式无效")
            name = str(item.get("name") or "").strip()
            portion = str(item.get("portion") or "").strip()
            if not name or len(name) > 80 or len(portion) > 80:
                raise ValueError("餐食项目名称或份量格式无效")
            normalized_items.append({
                "name": name,
                "portion": portion,
                "calories_kcal": _meal_number(item.get("calories_kcal"), "total_kcal"),
                "protein_g": _meal_number(item.get("protein_g"), "protein_g"),
                "carbs_g": _meal_number(item.get("carbs_g"), "carbs_g"),
                "fat_g": _meal_number(item.get("fat_g"), "fat_g"),
            })
        confidence = meal.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            raise ValueError("餐食估算可信度无效")
        confirmed = meal.get("user_confirmed")
        if not isinstance(confirmed, bool) or (confidence == "low" and not confirmed):
            raise ValueError("低可信度餐食估算需要用户明确确认")
        assumptions = meal.get("assumptions") or []
        if not isinstance(assumptions, list) or len(assumptions) > 6 or not all(
            isinstance(item, str) and len(item) <= 160 for item in assumptions
        ):
            raise ValueError("餐食估算假设格式无效")
        normalized = {key: _meal_number(meal.get(key), key) for key in _MEAL_NUMBERS}
        item_total = sum(item["calories_kcal"] for item in normalized_items)
        if abs(normalized["total_kcal"] - item_total) > max(20, item_total * 0.05):
            raise ValueError("餐食估算总热量必须与食物项目合计一致")
        if normalized["range_low_kcal"] > normalized["range_high_kcal"]:
            raise ValueError("餐食估算热量范围无效")
        meals.append({
            "source": meal["source"],
            "meal_slot": str(meal.get("meal_slot") or "")[:20],
            "photographed_at": str(meal.get("photographed_at") or "")[:40],
            "items": normalized_items,
            **normalized,
            "confidence": confidence,
            "assumptions": assumptions,
            "user_confirmed": confirmed,
            **({"analysis_token": meal["analysis_token"][:200]} if isinstance(meal.get("analysis_token"), str) else {}),
        })
    return meals


def validate_daily_checkin_update(payload: dict[str, Any]) -> tuple[str, dict[str, Any], list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("记录必须是对象")
    try:
        record_date = date.fromisoformat(str(payload.get("date") or "")).isoformat()
    except ValueError as exc:
        raise ValueError("记录日期格式必须为 YYYY-MM-DD") from exc

    record: dict[str, Any] = {}
    cleared: list[str] = []
    for field, (minimum, maximum) in _NUMBER_FIELDS.items():
        value = payload.get(field)
        if field in payload and value is None:
            cleared.append(field)
            continue
        if value == "" or field not in payload:
            continue
        if isinstance(value, bool):
            raise ValueError(f"{field} 必须是数字")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} 必须是数字") from exc
        if not minimum <= numeric <= maximum:
            raise ValueError(f"{field} 必须在 {minimum}-{maximum} 之间")
        record[field] = int(numeric) if numeric.is_integer() else numeric

    cheat_meal = payload.get("cheat_meal")
    if "cheat_meal" in payload and cheat_meal is None:
        cleared.append("cheat_meal")
    elif cheat_meal is not None:
        if not isinstance(cheat_meal, bool):
            raise ValueError("cheat_meal 必须是布尔值")
        record["cheat_meal"] = cheat_meal

    if "note" in payload and payload.get("note") is None:
        cleared.append("note")
    note = str(payload.get("note") or "").strip()
    if len(note) > 500:
        raise ValueError("备注不能超过 500 个字符")
    if note:
        record["note"] = note
    if "meal_estimates" in payload:
        record["meal_estimates"] = _validate_meal_estimates(payload["meal_estimates"])
    if record.get("cheat_meal") is False and record.get("meal_estimates") == []:
        record.pop("cheat_meal", None)
        record.pop("meal_estimates", None)
    if not record and not cleared:
        raise ValueError("请至少填写一项每日记录")
    return record_date, record, cleared


def validate_daily_checkin(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    record_date, record, _cleared = validate_daily_checkin_update(payload)
    return record_date, record


# ══════════════════════════════════════════════════════════════════════════
# Agent 工具写入的校验（AGENT-02）
# ══════════════════════════════════════════════════════════════════════════
#
# `save_daily_record` 以前只检查 date 非空、category 是非空字符串、record 是
# dict，其余一律放行。于是模型可以写进 date="昨天"、任意深度嵌套的对象，
# 更要命的是可以把 category 写成 "training" —— 这类记录会直接出现在训练
# 记录列表里（`_training_record_items` 只排除 CHECKIN_CATEGORY），可被当作
# 解析出来的真实训练去编辑合并。而 prompts.py 里明明写着"Agent 没有保存
# 训练的权限"：权限其实是给了的，只靠提示词挡着。
#
# 这里补上确定性校验。取向是"结构从严、字段从宽"：结构限制（分类白名单、
# 嵌套深度、体积、键数量）严格执行，但不强制字段白名单——否则一个通用的
# "保存每日记录"工具会拒掉大量合理用法。已知的数值字段仍按上面那份
# _NUMBER_FIELDS 的范围校验，与手动录入共用同一套口径。

#: Agent 允许写入的分类。刻意用白名单而不是黑名单——FIT 导入会产生
#: "力量训练""跳绳""有氧运动"等中文分类，黑名单不可能列全。
AGENT_ALLOWED_CATEGORIES = ("recovery", "nutrition", "summary", "daily")
NON_TRAINING_CATEGORIES = frozenset((CHECKIN_CATEGORY, *AGENT_ALLOWED_CATEGORIES))

_NUTRITION_FIELD_ALIASES = {
    "热量_kcal": "calories_kcal", "热量": "calories_kcal", "总热量": "calories_kcal",
    "蛋白质_g": "protein_g", "蛋白质": "protein_g",
    "碳水_g": "carbs_g", "碳水": "carbs_g", "碳水化合物_g": "carbs_g",
    "脂肪_g": "fat_g", "脂肪": "fat_g",
    "膳食纤维_g": "fiber_g", "膳食纤维": "fiber_g",
    "备注": "note", "餐次": "meal_slot",
}


def normalize_agent_nutrition_record(raw_record: dict[str, Any]) -> dict[str, Any]:
    """Normalize an Agent nutrition write to the four persisted nutrient totals."""
    record: dict[str, Any] = {}
    for raw_key, value in raw_record.items():
        key = _NUTRITION_FIELD_ALIASES.get(str(raw_key).strip(), str(raw_key).strip())
        if key == "total_kcal":
            key = "calories_kcal"
        if key not in {"calories_kcal", "protein_g", "carbs_g", "fat_g"}:
            continue
        if key in record and record[key] != value:
            raise ValueError(f"营养记录中的 {key} 提供了互相冲突的值")
        record[key] = value
    if not record:
        raise ValueError("营养记录至少需要热量、蛋白质、碳水或脂肪中的一项")
    return record


def nutrition_estimate_from_totals(
    nutrients: dict[str, Any], *, source: str = "text_nutrition"
) -> dict[str, Any]:
    """Build one nutrition group using the same structure as photo estimates."""
    if source not in _MEAL_SOURCES:
        raise ValueError("营养组来源无效")
    calories = int(round(float(nutrients.get("calories_kcal") or 0)))
    protein = round(float(nutrients.get("protein_g") or 0), 1)
    carbs = round(float(nutrients.get("carbs_g") or 0), 1)
    fat = round(float(nutrients.get("fat_g") or 0), 1)
    meal = {
        "source": source,
        "items": [{
            "name": "文字记录" if source == "text_nutrition" else "手动记录",
            "portion": "未记录",
            "calories_kcal": calories,
            "protein_g": protein,
            "carbs_g": carbs,
            "fat_g": fat,
        }],
        "total_kcal": calories,
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
        "range_low_kcal": calories,
        "range_high_kcal": calories,
        "confidence": "high",
        "assumptions": [],
        "user_confirmed": True,
    }
    return _validate_meal_estimates([meal])[0]

_AGENT_MAX_KEYS = 30
_AGENT_MAX_DEPTH = 3
_AGENT_MAX_SERIALIZED_CHARS = 4000
_AGENT_MAX_KEY_CHARS = 40
_AGENT_MAX_STRING_CHARS = 500
_AGENT_MAX_LIST_ITEMS = 50


def _value_depth(value: Any, current: int = 1) -> int:
    if isinstance(value, dict):
        return max((_value_depth(item, current + 1) for item in value.values()), default=current)
    if isinstance(value, list):
        return max((_value_depth(item, current + 1) for item in value), default=current)
    return current


def _check_scalar(key: str, value: Any) -> None:
    if isinstance(value, str) and len(value) > _AGENT_MAX_STRING_CHARS:
        raise ValueError(f"{key} 的文本超过 {_AGENT_MAX_STRING_CHARS} 个字符，请精简后再保存")
    if not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError(f"{key} 含有不支持的值类型：{type(value).__name__}")


def _check_container(key: str, value: Any) -> None:
    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            _check_container(f"{key}.{sub_key}", sub_value)
    elif isinstance(value, list):
        if len(value) > _AGENT_MAX_LIST_ITEMS:
            raise ValueError(f"{key} 的列表超过 {_AGENT_MAX_LIST_ITEMS} 项")
        for item in value:
            _check_container(key, item)
    else:
        _check_scalar(key, value)


def is_training_record_item(item: Any) -> bool:
    """Return whether a stored item is a real parsed and confirmed workout."""
    if not isinstance(item, dict) or item.get("category") in NON_TRAINING_CATEGORIES:
        return False
    record = item.get("record")
    if not isinstance(record, dict) or not isinstance(record.get("segments"), list):
        return False
    session = record.get("session") if isinstance(record.get("session"), dict) else {}
    sport = str(record.get("sport") or session.get("sport") or "").strip()
    return bool(sport)


def validate_agent_daily_record(
    raw_date: Any,
    raw_category: Any,
    raw_record: Any,
    *,
    today: date | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """校验 Agent 通过工具写入的每日记录。

    返回 (日期, 分类, 记录体)；不合法时抛 ValueError，消息面向模型，
    尽量说明"应该怎么做"而不只是"哪里错了"。
    """
    # ---- 日期 ----
    try:
        record_date = date.fromisoformat(str(raw_date or "").strip())
    except ValueError as exc:
        raise ValueError(
            "date 必须是 YYYY-MM-DD 格式的具体日期（例如 2026-08-20），"
            "不能用「今天」「昨天」这类相对说法；如果不确定日期，先向用户确认。"
        ) from exc

    today = today or datetime.now(BEIJING).date()
    if record_date > today + timedelta(days=1):
        raise ValueError(f"date {record_date.isoformat()} 是未来日期，不能为尚未发生的日子记录数据。")
    if record_date < date(2000, 1, 1):
        raise ValueError(f"date {record_date.isoformat()} 过早，请确认日期是否写错。")

    # ---- 分类 ----
    category = str(raw_category or "").strip()
    if category not in AGENT_ALLOWED_CATEGORIES:
        allowed = " / ".join(AGENT_ALLOWED_CATEGORIES)
        hint = ""
        if category in {"training", "训练", "力量训练"}:
            hint = (
                "训练记录只能由用户在侧栏点击「确认并保存训练」写入，"
                "或由 FIT 文件导入产生；请改为向用户说明，不要用本工具代写。"
            )
        elif category == CHECKIN_CATEGORY:
            hint = "每日打卡由用户在打卡表单中填写，本工具不能代写。"
        raise ValueError(f"category 必须是 {allowed} 之一，收到的是「{category}」。{hint}".strip())

    # ---- 记录体 ----
    if not isinstance(raw_record, dict):
        raise ValueError("record 必须是对象（JSON object）")
    if not raw_record:
        raise ValueError("record 不能为空，请至少写入一项内容")
    if len(raw_record) > _AGENT_MAX_KEYS:
        raise ValueError(f"record 的字段数不能超过 {_AGENT_MAX_KEYS} 个")
    if _value_depth(raw_record) > _AGENT_MAX_DEPTH:
        raise ValueError(f"record 的嵌套层级不能超过 {_AGENT_MAX_DEPTH} 层，请把结构拍平后再保存")

    normalized_input = normalize_agent_nutrition_record(raw_record) if category == "nutrition" else raw_record
    record: dict[str, Any] = {}
    for key, value in normalized_input.items():
        key = str(key).strip()
        if not key:
            raise ValueError("record 中存在空字段名")
        if len(key) > _AGENT_MAX_KEY_CHARS:
            raise ValueError(f"字段名「{key[:20]}…」超过 {_AGENT_MAX_KEY_CHARS} 个字符")
        _check_container(key, value)
        # 已知数值字段沿用手动录入的范围口径，避免同一个指标两套标准
        if key in _NUMBER_FIELDS and not isinstance(value, bool) and value not in (None, ""):
            minimum, maximum = _NUMBER_FIELDS[key]
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} 必须是数字") from exc
            if not minimum <= numeric <= maximum:
                raise ValueError(f"{key} 必须在 {minimum}-{maximum} 之间，收到 {numeric:g}")
            value = int(numeric) if numeric.is_integer() else numeric
        record[key] = value

    serialized = json.dumps(record, ensure_ascii=False)
    if len(serialized) > _AGENT_MAX_SERIALIZED_CHARS:
        raise ValueError(
            f"record 序列化后 {len(serialized)} 字符，超过上限 {_AGENT_MAX_SERIALIZED_CHARS}，请精简内容"
        )

    # 标注来源，便于后续区分"模型代写"与"用户手动录入"
    record.setdefault("source", "agent_tool")
    return record_date.isoformat(), category, record
