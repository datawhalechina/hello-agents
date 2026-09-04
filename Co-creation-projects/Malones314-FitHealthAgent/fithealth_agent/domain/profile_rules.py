"""档案字段校验、合并与展示纯规则（main.py 拆分：阶段 3b）。"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo


#: 用户未配置器械时的唯一默认值；storage 与展示规则共同引用，避免两份默认漂移。
DEFAULT_EQUIPMENT = ["哑铃", "哑铃凳"]


def validate_profile_tool_updates(
    raw_updates: object, source_message: str = ""
) -> tuple[dict[str, object], list[str]]:
    """Validate constrained Function Calling arguments before profile persistence."""
    if not isinstance(raw_updates, dict):
        return {}, []
    normalized_message = "".join(str(source_message or "").split())
    if normalized_message and any(marker in normalized_message for marker in (
        "?", "？", "是不是", "是否", "有没有", "有没", "哪些", "什么", "不知道", "吗",
    )):
        return {}, []
    updates: dict[str, object] = {}
    labels: list[str] = []
    weights = raw_updates.get("weekly_weight_kg")
    if isinstance(weights, list) and 1 <= len(weights) <= 7:
        try:
            normalized_weights = [float(weight) for weight in weights]
        except (TypeError, ValueError):
            normalized_weights = []
        if normalized_weights and all(25 <= weight <= 250 for weight in normalized_weights):
            updates["weekly_weight_kg"] = normalized_weights
            labels.append("weekly_weight_kg")
    height = raw_updates.get("height_cm")
    if isinstance(height, (int, float)) and not isinstance(height, bool) and 100 <= height <= 250:
        updates["height_cm"] = float(height)
        labels.append("height_cm")
    birth_date = raw_updates.get("birth_date")
    if isinstance(birth_date, str):
        try:
            parsed_birth_date = date.fromisoformat(birth_date)
            today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
            age = today.year - parsed_birth_date.year - (
                (today.month, today.day) < (parsed_birth_date.month, parsed_birth_date.day)
            )
            if 13 <= age <= 120:
                updates["birth_date"] = parsed_birth_date.isoformat()
                labels.append("birth_date")
        except ValueError:
            pass
    sex = raw_updates.get("sex")
    if sex in {"male", "female"}:
        updates["sex"] = sex
        labels.append("sex")
    goal = raw_updates.get("goal")
    if isinstance(goal, str):
        cleaned_goal = goal.strip()
        if 1 <= len(cleaned_goal) <= 30:
            updates["goal"] = cleaned_goal
            labels.append("goal")
    equipment_change = raw_updates.get("equipment_change")
    if isinstance(equipment_change, dict):
        mode = equipment_change.get("mode")
        equipment = equipment_change.get("items")
    else:
        mode = None
        equipment = None
    if mode in {"add", "remove", "replace"} and isinstance(equipment, list) and 1 <= len(equipment) <= 20:
        cleaned_equipment = list(
            dict.fromkeys(
                item.strip()
                for item in equipment
                if isinstance(item, str) and 1 <= len(item.strip()) <= 24
            )
        )
        if cleaned_equipment:
            updates["equipment"] = {"mode": mode, "items": cleaned_equipment}
            labels.append("equipment")
    return updates, labels


def merge_profile_updates_with_existing(
    profile: dict[str, object], updates: dict[str, object]
) -> dict[str, object]:
    """Resolve explicit equipment changes while the profile write lock is held."""
    merged = dict(updates)
    existing_equipment = profile.get("equipment")
    incoming_equipment = updates.get("equipment")
    if isinstance(existing_equipment, list) and isinstance(incoming_equipment, dict):
        mode = incoming_equipment.get("mode")
        items = incoming_equipment.get("items")
        if isinstance(items, list):
            current = [item for item in existing_equipment if isinstance(item, str) and item.strip()]
            requested = [item for item in items if isinstance(item, str) and item.strip()]
            if mode == "add":
                merged["equipment"] = list(dict.fromkeys([*current, *requested]))
            elif mode == "remove":
                unwanted = set(requested)
                merged["equipment"] = [item for item in current if item not in unwanted]
            elif mode == "replace":
                merged["equipment"] = list(dict.fromkeys(requested))
    return merged


def equipment_change_preview(profile: dict[str, object], updates: dict[str, object]) -> dict[str, object] | None:
    """Build the before/after diff shown in the profile confirmation card."""
    change = updates.get("equipment")
    before = profile.get("equipment")
    if not isinstance(change, dict) or not isinstance(before, list):
        return None
    after = merge_profile_updates_with_existing(profile, updates).get("equipment")
    if not isinstance(after, list):
        return None
    before_items = [item for item in before if isinstance(item, str)]
    after_items = [item for item in after if isinstance(item, str)]
    return {
        "mode": change.get("mode"),
        "before": before_items,
        "after": after_items,
        "added": [item for item in after_items if item not in before_items],
        "removed": [item for item in before_items if item not in after_items],
    }


def field_label(field: str) -> str:
    labels = {
        "weekly_weight_kg": "本周体重",
        "height_cm": "身高",
        "birth_date": "出生日期",
        "sex": "性别",
        "goal": "健身目标",
        "equipment": "可用器械",
    }
    return labels.get(field, field)


def profile_summary(
    profile: dict[str, object], *, include_birth_date: bool = True
) -> str:
    weights = profile.get("weekly_weight_kg") or []
    height = profile.get("height_cm")
    birth_date_raw = profile.get("birth_date")
    age = None
    if isinstance(birth_date_raw, str):
        try:
            birth_date = date.fromisoformat(birth_date_raw)
            today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except ValueError:
            pass
    sex_code = profile.get("sex")
    sex = {"male": "男", "female": "女"}.get(sex_code, "未填写")
    goal = profile.get("goal")
    equipment = profile.get("equipment") or DEFAULT_EQUIPMENT
    birth_date_line = f"- 出生日期：{birth_date_raw}\n" if include_birth_date else ""
    return (
        f"- 本周体重(kg)：{weights}\n"
        f"- 身高(cm)：{height}\n"
        f"{birth_date_line}"
        f"- 年龄：{age}\n"
        f"- 性别：{sex}\n"
        f"- 可用器械：{equipment}\n"
        f"- 健身目标：{goal}"
    )


def onboarding_reply(profile: dict[str, object], missing_fields: list[str], updated_fields: list[str]) -> str:
    prefix = ""
    if updated_fields:
        readable = "、".join(field_label(item) for item in updated_fields)
        prefix = f"已记录：{readable}。\n\n"

    missing_desc = []
    if "weekly_weight_kg" in missing_fields:
        missing_desc.append("本周体重（kg，可填 1-7 天，例如 70.2, 69.9, 69.8）")
    if "height_cm" in missing_fields:
        missing_desc.append("身高（cm，例如 175）")
    if "birth_date" in missing_fields:
        missing_desc.append("出生日期（例如 2001年3月14日出生，用于自动计算年龄和基础代谢）")
    if "sex" in missing_fields:
        missing_desc.append("性别（男 / 女，用于计算基础代谢）")
    if "goal" in missing_fields:
        missing_desc.append("健身目标（如 减脂 / 增肌 / 塑形）")

    missing_text = "\n".join(f"{index}. {item}" for index, item in enumerate(missing_desc, start=1))
    equipment = profile.get("equipment") or DEFAULT_EQUIPMENT

    return (
        f"{prefix}在开始前我需要先完善你的用户信息，请补充：\n{missing_text}\n\n"
        f"当前可用器械：{equipment}（默认是 {DEFAULT_EQUIPMENT}）。"
        "如果你要修改器械，直接说“器械改为 杠铃、拉力器”。"
    )
