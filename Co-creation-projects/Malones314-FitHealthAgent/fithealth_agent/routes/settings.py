"""Resource-scoped HTTP routes extracted from main."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent.domain.profile_rules import field_label, merge_profile_updates_with_existing, onboarding_reply, profile_summary, validate_profile_tool_updates
from fithealth_agent.domain.recovery_view import _recovery_checkin_items, parse_garmin_recovery_hours, render_session_intro
from fithealth_agent.runtime import deps
from fithealth_agent.workflows.chat_workflow import _current_recovery_snapshot, _soreness_report_payload, active_temporary_health_facts

router = APIRouter()

reset_router = APIRouter()

@router.get("/profile/status")
def profile_status() -> JSONResponse:
    profile = deps.profile_store.get_profile()
    missing = deps.profile_store.missing_fields(profile)
    return JSONResponse(
        {
            "complete": not missing,
            "missing_fields": missing,
            "prompt": onboarding_reply(profile, missing, []) if missing else "",
        }
    )

@router.post("/profile/confirm-update")
def confirm_profile_update(payload: dict) -> JSONResponse:
    updates, fields = validate_profile_tool_updates(payload.get("updates"))
    if not updates:
        return JSONResponse({"error": "没有可确认的有效档案变更"}, status_code=400)
    # DATA-07：合并必须交给 store 在锁内完成。原先是 get_profile() → 合并 →
    # update_profile()，两个并发确认会读到同一份旧档案，后写的那一个把前一个
    # 追加的器械直接抹掉。
    profile = deps.profile_store.update_profile(
        updates, merge=merge_profile_updates_with_existing
    )
    return JSONResponse(
        {
            "saved": True,
            "fields": fields,
            "profile": profile,
            "complete": deps.profile_store.is_complete(profile),
        }
    )

def configured_model_name(environment_key: str) -> str:
    value = os.getenv(environment_key, "").strip()
    return value if value else "未配置"

def build_session_intro(
    garmin_recovery_hours: float = 0.0,
    recovery_snapshot: object | None = None,
) -> str:
    """Build a local-only welcome summary without exposing credentials or endpoints."""
    # Import locally so this welcome builder remains usable by source-level
    # tests and by deployments that only load the existing intro functions.
    from fithealth_agent.muscle_recovery import build_recovery_snapshot

    profile = deps.profile_store.get_profile()
    missing_fields = deps.profile_store.missing_fields(profile)
    external_models_enabled = deps.external_model_settings_store.get()["external_models_enabled"]
    records_count = len(deps.daily_record_store.list_records())
    plans_count = len(deps.plan_store.list_plans())
    deps.info_store.cleanup_expired()
    memories = deps.info_store.get_all()
    memories_count = len(memories)
    temporary_health = active_temporary_health_facts(memories)
    health_imports_count = len(deps.health_store.list_imports())
    if recovery_snapshot is None:
        recovery_snapshot = build_recovery_snapshot(
            deps.daily_record_store.list_records(),
            now=datetime.now(ZoneInfo("Asia/Shanghai")),
            garmin_recovery_hours=garmin_recovery_hours,
            lookback_days=7,
        )

    profile_text = profile_summary(profile, include_birth_date=False)
    return render_session_intro(
        garmin_recovery_hours=garmin_recovery_hours,
        profile_text=profile_text,
        missing_field_labels=[field_label(field) for field in missing_fields],
        external_models_enabled=external_models_enabled,
        model_names={
            "main": configured_model_name("LLM_MODEL_ID"),
            "lite": configured_model_name("LLM_LITE_MODE_ID"),
            "vision": configured_model_name("VISION_MODEL_ID"),
        },
        records_count=records_count,
        plans_count=plans_count,
        memories_count=memories_count,
        health_imports_count=health_imports_count,
        temporary_health=temporary_health,
        recovery_snapshot=recovery_snapshot,
    )

@router.get("/session/intro")
def session_intro(garmin_recovery_hours: str | None = None) -> JSONResponse:
    try:
        garmin_hours = parse_garmin_recovery_hours(garmin_recovery_hours)
    except ValueError as exc:
        return JSONResponse(
            {
                "error": str(exc),
                "garmin_recovery_hours_valid": False,
                "garmin_recovery_hours": None,
            },
            status_code=400,
        )
    temporary_health = active_temporary_health_facts(deps.info_store.get_all())
    recovery_snapshot = _current_recovery_snapshot(garmin_hours)
    active_soreness = deps.soreness_store.list_reports(active_only=True)
    painful_prompt_regions = list(dict.fromkeys(
        report.region for report in active_soreness if report.level == "painful"
    ))
    prompt_regions = list(dict.fromkeys([
        *(load.region for load in recovery_snapshot.loads),
        *painful_prompt_regions,
    ]))
    intro_message = build_session_intro(garmin_hours, recovery_snapshot)
    if painful_prompt_regions:
        intro_message += "\n\n### 疼痛复查\n" + "\n".join(
            f"- {region}此前报告过疼痛，现在情况如何？" for region in painful_prompt_regions
        )
    return JSONResponse(
        {
            "message": intro_message,
            "external_models_enabled": deps.external_model_settings_store.get()[
                "external_models_enabled"
            ],
            "temporary_health_checkin": [
                {
                    "value": fact.get("value"),
                    "valid_from": fact.get("valid_from"),
                    "valid_until": fact.get("valid_until"),
                    "duration_type": fact.get("duration_type"),
                }
                for fact in temporary_health
            ],
            "garmin_recovery_hours": garmin_hours,
            "garmin_recovery_hours_valid": True,
            "muscle_recovery_checkin": _recovery_checkin_items(recovery_snapshot),
            "active_soreness_reports": [_soreness_report_payload(item) for item in active_soreness],
            "soreness_prompt_regions": prompt_regions,
        }
    )

EXTERNAL_MODEL_DISCLOSURE = [
    {
        "id": "chat_agent",
        "name": "主对话模型",
        "data": "当前消息、近期对话、已确认记忆，以及用于个性化的用户档案摘要。",
    },
    {
        "id": "plan_classifier",
        "name": "训练计划鉴定模型",
        "data": "规则无法确定时，最多发送训练计划前 2,000 个字符。",
    },
    {
        "id": "muscle_mapper",
        "name": "未知动作肌群查询",
        "data": "仅当本地规则无法识别保存后的动作名时，发送该动作名与允许的肌群枚举；不发送整份训练记录。",
    },
    {
        "id": "memory_summary",
        "name": "退出摘要模型",
        "data": "退出时的本次对话文本，用于判断是否生成临时记忆。",
    },
    {
        "id": "food_vision",
        "name": "餐盘视觉模型",
        "data": "餐盘图片和最多 500 个字符的补充说明；图片不保存在本地。",
    },
    {
        "id": "youtube",
        "name": "YouTube 视频搜索",
        "data": "仅在主对话模型推荐动作时发送动作关键词，不发送健康档案或原始健康数据。",
    },
]

@router.get("/settings/external-models")
def get_external_model_settings() -> JSONResponse:
    return JSONResponse(
        {
            **deps.external_model_settings_store.get(),
            "disclosure": EXTERNAL_MODEL_DISCLOSURE,
            "local_features": [
                "健康数据导入与查询",
                "训练组编辑与保存",
                "每日手动记录",
                "数据删除、导出与备份恢复",
            ],
        }
    )

@router.put("/settings/external-models")
def update_external_model_settings(payload: dict) -> JSONResponse:
    try:
        settings = deps.external_model_settings_store.set_external_models_enabled(
            payload.get("external_models_enabled")
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({**settings, "disclosure": EXTERNAL_MODEL_DISCLOSURE})

@reset_router.post("/data/profile/reset")
def reset_profile() -> JSONResponse:
    return JSONResponse({"reset": True, "profile": deps.profile_store.reset()})

