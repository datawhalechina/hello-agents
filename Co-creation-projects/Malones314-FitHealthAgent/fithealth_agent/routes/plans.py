"""Resource-scoped HTTP routes extracted from main."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent.context_budget import contains_truncation_marker
from fithealth_agent.plan_draft_cache import resolve_plan_save_content
from fithealth_agent.runtime import deps

router = APIRouter()

@router.get("/plans/{plan_id}")
def get_plan(plan_id: str) -> JSONResponse:
    item = deps.plan_store.get(plan_id)
    if item is None:
        return JSONResponse({"error": "未找到该训练计划"}, status_code=404)
    return JSONResponse(item)

@router.post("/plans")
def save_plan(payload: dict) -> JSONResponse:
    # 正文来源的裁决抽在 plan_draft_cache.resolve_plan_save_content 里，
    # 这样那段顺序敏感的逻辑能被真正调用着测（BUG-05）。
    content, content_error = resolve_plan_save_content(
        payload, deps.plan_draft_cache, is_truncated=contains_truncation_marker
    )
    if content_error is not None:
        return JSONResponse({"error": content_error}, status_code=400)
    try:
        item = deps.plan_store.add(
            date=str(payload.get("date") or ""),
            subject=str(payload.get("subject") or ""),
            title=str(payload.get("title") or ""),
            content=content,
            source=str(payload.get("source") or ""),
            memo=str(payload.get("memo") or ""),
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"saved": not item.get("duplicate"), **item})

@router.patch("/plans/{plan_id}")
def update_plan(plan_id: str, payload: dict) -> JSONResponse:
    try:
        item = deps.plan_store.update(
            plan_id,
            date=str(payload.get("date") or ""),
            subject=str(payload.get("subject") or ""),
            title=str(payload.get("title") or ""),
            memo=str(payload.get("memo") or ""),
            content=payload.get("content") if "content" in payload else None,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if item is None:
        return JSONResponse({"error": "未找到该训练计划"}, status_code=404)
    return JSONResponse(item)

@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: str) -> JSONResponse:
    if not deps.plan_store.delete(plan_id):
        return JSONResponse({"error": "未找到该训练计划"}, status_code=404)
    return JSONResponse({"deleted": True, "id": plan_id})

@router.post("/plans/delete-batch")
def delete_plans_batch(payload: dict) -> JSONResponse:
    plan_ids = payload.get("ids")
    if not isinstance(plan_ids, list) or not plan_ids:
        return JSONResponse({"error": "请选择需要删除的训练计划"}, status_code=400)
    normalized = list(dict.fromkeys(str(item).strip() for item in plan_ids if str(item).strip()))
    return JSONResponse({"deleted": deps.plan_store.delete_many(normalized)})

