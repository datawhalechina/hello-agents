"""Resource-scoped HTTP routes extracted from main."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent.domain.memory_view import _fact_locator
from fithealth_agent.muscle_recovery import REGION_ALIASES
from fithealth_agent.runtime import deps
from fithealth_agent.workflows.chat_workflow import _soreness_report_payload

router = APIRouter()

@router.delete("/data/memories/{entry_id}")
def delete_memory(entry_id: str) -> JSONResponse:
    if not deps.info_store.delete_entry(entry_id):
        return JSONResponse({"error": "未找到该临时记忆"}, status_code=404)
    return JSONResponse({"deleted": True, "id": entry_id})

@router.patch("/data/soreness/{report_id}")
def update_soreness_report(report_id: str, payload: dict) -> JSONResponse:
    region = str(payload.get("region") or "").strip()
    level = str(payload.get("level") or "").strip()
    evidence = payload.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        return JSONResponse({"error": "证据必须是文本"}, status_code=400)
    try:
        report = deps.soreness_store.update_report(
            report_id, region=region, level=level, evidence=evidence
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if report is None:
        return JSONResponse({"error": "未找到该肌群酸痛记录"}, status_code=404)
    return JSONResponse({"updated": True, "report": _soreness_report_payload(report)})

@router.post("/data/soreness")
def create_soreness_report(payload: dict) -> JSONResponse:
    region = str(payload.get("region") or "").strip()
    level = str(payload.get("level") or "").strip()
    evidence = str(payload.get("evidence") or "手动录入")[:500]
    if region not in REGION_ALIASES or level not in {"recovered", "sore", "painful"}:
        return JSONResponse({"error": "请选择有效的区域和程度"}, status_code=400)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    from fithealth_agent.soreness_store import muscle_ids_for_region
    from fithealth_agent.muscle_recovery import SorenessReport
    report = SorenessReport(
        region=region,
        muscle_ids=muscle_ids_for_region(region),
        level=level,
        reported_at=now,
        expires_at=now + timedelta(hours=72),
        evidence=evidence,
    )
    try:
        saved = deps.soreness_store.add_reports([report])[0]
    except (OSError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    return JSONResponse({"created": True, "report": _soreness_report_payload(saved)})

@router.delete("/data/soreness/{report_id}")
def delete_soreness_report(report_id: str) -> JSONResponse:
    if not deps.soreness_store.delete_report(report_id):
        return JSONResponse({"error": "未找到该肌群酸痛记录"}, status_code=404)
    return JSONResponse({"deleted": True, "id": report_id})

@router.post("/data/memories/{entry_id}/facts/{fact_ref}/confirm")
def confirm_memory_fact(entry_id: str, fact_ref: str) -> JSONResponse:
    locator = _fact_locator(fact_ref)
    try:
        result = deps.info_store.set_fact_confirmation(
            entry_id, locator["fact_index"], True, fact_id=locator["fact_id"]
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc), "code": "MEMORY_CONFLICT", "requires_reconfirmation": True}, status_code=409)
    if result is None:
        return JSONResponse({"error": "未找到该记忆事实"}, status_code=404)
    return JSONResponse({"confirmed": True, **result})

@router.post("/data/memories/{entry_id}/facts/{fact_ref}/reject")
def reject_memory_fact(entry_id: str, fact_ref: str) -> JSONResponse:
    locator = _fact_locator(fact_ref)
    result = deps.info_store.reject_fact(
        entry_id, locator["fact_index"], fact_id=locator["fact_id"]
    )
    if result is None:
        return JSONResponse({"error": "未找到该记忆事实"}, status_code=404)
    return JSONResponse({"rejected": True, **result})

@router.patch("/data/memories/{entry_id}/facts/{fact_ref}")
def edit_memory_fact(entry_id: str, fact_ref: str, payload: dict) -> JSONResponse:
    value = payload.get("value")
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return JSONResponse({"error": "事实值类型无效"}, status_code=400)
    evidence = payload.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        return JSONResponse({"error": "证据必须是文本"}, status_code=400)
    locator = _fact_locator(fact_ref)
    try:
        result = deps.info_store.edit_fact(
            entry_id, locator["fact_index"], value, evidence, fact_id=locator["fact_id"]
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if result is None:
        return JSONResponse({"error": "未找到该记忆事实"}, status_code=404)
    return JSONResponse({"updated": True, **result})

@router.post("/data/memories/forget")
def forget_memory_facts(payload: dict) -> JSONResponse:
    namespace = payload.get("namespace")
    key = payload.get("key")
    value = payload.get("value") if "value" in payload else None
    reason = payload.get("reason", "user_request")
    if not isinstance(namespace, str) or not namespace.strip() or not isinstance(key, str) or not key.strip():
        return JSONResponse({"error": "namespace 和 key 不能为空"}, status_code=400)
    if value is not None and (not isinstance(value, (str, int, float)) or isinstance(value, bool)):
        return JSONResponse({"error": "value 类型无效"}, status_code=400)
    if not isinstance(reason, str):
        return JSONResponse({"error": "reason 必须是文本"}, status_code=400)
    try:
        result = deps.info_store.forget_facts(
            namespace.strip(), key.strip(), value, reason=reason.strip()[:200] or "user_request"
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if not result["cleared"]:
        return JSONResponse({"error": "未找到匹配的已确认记忆事实"}, status_code=404)
    return JSONResponse(result)

@router.post("/data/memories/{entry_id}/facts/{fact_ref}/rollback")
def rollback_memory_fact(entry_id: str, fact_ref: str, payload: dict | None = None) -> JSONResponse:
    locator = _fact_locator(fact_ref)
    if locator["fact_id"] is None:
        return JSONResponse({"error": "回滚必须使用稳定 fact_id"}, status_code=400)
    history_index = (payload or {}).get("history_index", -1)
    if not isinstance(history_index, int) or isinstance(history_index, bool):
        return JSONResponse({"error": "history_index 必须是整数"}, status_code=400)
    try:
        result = deps.info_store.rollback_fact(
            entry_id, fact_id=str(locator["fact_id"]), history_index=history_index
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if result is None:
        return JSONResponse({"error": "未找到该记忆事实"}, status_code=404)
    return JSONResponse({"rolled_back": True, "requires_confirmation": True, **result})

@router.post("/data/memories/{entry_id}/confirm")
def confirm_memory(entry_id: str) -> JSONResponse:
    try:
        result = deps.info_store.confirm_entry(entry_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc), "code": "MEMORY_CONFLICT", "requires_reconfirmation": True}, status_code=409)
    if result is None:
        return JSONResponse({"error": "未找到该临时记忆"}, status_code=404)
    return JSONResponse({"confirmed": True, "id": entry_id, **result})

@router.delete("/data/memories")
def clear_memories() -> JSONResponse:
    return JSONResponse({"deleted": deps.info_store.clear()})

