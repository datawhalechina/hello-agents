"""
饮食场景 Mock 工具：营养查询、运动/睡眠摘要（可替换为真实 API）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

# 便利店/外卖常见高蛋白选项（演示用）
_NUTRITION_MOCK: Dict[str, Dict[str, Any]] = {
    "鸡蛋": {"protein_g_per_unit": 6.0, "unit": "1个(约50g)", "kcal_per_unit": 70},
    "水煮蛋": {"protein_g_per_unit": 6.0, "unit": "1个", "kcal_per_unit": 70},
    "希腊酸奶": {"protein_g_per_unit": 12.0, "unit": "100g", "kcal_per_unit": 95},
    "酸奶": {"protein_g_per_unit": 4.0, "unit": "100g", "kcal_per_unit": 85},
    "牛奶": {"protein_g_per_unit": 3.3, "unit": "100ml", "kcal_per_unit": 60},
    "豆浆": {"protein_g_per_unit": 3.6, "unit": "100ml", "kcal_per_unit": 40},
    "即食鸡胸肉": {"protein_g_per_unit": 24.0, "unit": "100g", "kcal_per_unit": 120},
    "鸡腿肉": {"protein_g_per_unit": 20.0, "unit": "100g", "kcal_per_unit": 180},
    "金枪鱼罐头": {"protein_g_per_unit": 22.0, "unit": "100g", "kcal_per_unit": 110},
    "蛋白棒": {"protein_g_per_unit": 15.0, "unit": "1根(约40g)", "kcal_per_unit": 180},
    "豆腐": {"protein_g_per_unit": 8.0, "unit": "100g", "kcal_per_unit": 80},
    "豆干": {"protein_g_per_unit": 16.0, "unit": "100g", "kcal_per_unit": 140},
}


def nutrition_lookup(query: str) -> Dict[str, Any]:
    """
    按关键词匹配 mock 营养表；支持多个关键词逗号分隔。
    """
    q = (query or "").strip()
    if not q:
        return {"matches": [], "hint": "请提供食物名称关键词"}

    keys = [k.strip() for k in q.replace("，", ",").split(",") if k.strip()]
    if not keys:
        keys = [q]

    matches: List[Dict[str, Any]] = []
    for kw in keys:
        for name, meta in _NUTRITION_MOCK.items():
            if kw in name or name in kw:
                matches.append({"name": name, **meta})
        # 直接命中
        if kw in _NUTRITION_MOCK and not any(m["name"] == kw for m in matches):
            matches.append({"name": kw, **_NUTRITION_MOCK[kw]})

    # 去重按 name
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for m in matches:
        if m["name"] not in seen:
            seen.add(m["name"])
            uniq.append(m)

    return {
        "query": q,
        "matches": uniq[:20],
        "source": "mock_nutrition_db",
    }


def activity_sleep_summary(user_id: str) -> Dict[str, Any]:
    """
    Mock：可穿戴/手填摘要。后续可改为读 user_profiles 或外部 API。
    """
    _ = user_id
    return {
        "user_id": user_id,
        "date": "今日",
        "steps": 8200,
        "sleep_hours": 6.5,
        "sleep_quality": "一般",
        "evening_workout": True,
        "workout_type": "力量训练",
        "notes": "mock：连续感知数据可接手环/OpenAPI",
        "source": "mock_wearable",
    }


def tools_spec() -> str:
    return json.dumps(
        [
            {
                "name": "nutrition_lookup",
                "description": "查询常见便利店/外卖食物蛋白质含量与份量单位",
                "parameters": {"query": "关键词，多个用英文逗号分隔"},
            },
            {
                "name": "activity_sleep_summary",
                "description": "获取用户今日步数、睡眠与晚间是否安排训练等摘要",
                "parameters": {"user_id": "用户 ID"},
            },
        ],
        ensure_ascii=False,
        indent=2,
    )


def dispatch_tool(name: str, action_input: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    if name == "nutrition_lookup":
        return nutrition_lookup(str(action_input.get("query", "")))
    if name == "activity_sleep_summary":
        uid = str(action_input.get("user_id") or user_id)
        return activity_sleep_summary(uid)
    return {"error": f"未知工具: {name}"}
