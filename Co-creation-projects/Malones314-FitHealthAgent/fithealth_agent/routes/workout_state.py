"""Resource-scoped HTTP routes extracted from main."""

import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent import workout_store
from fithealth_agent.domain.plan_validation import infer_training_subject
from fithealth_agent.runtime import deps

router = APIRouter()

pending_router = APIRouter()

@router.get("/workout_state")
def get_workout_state() -> JSONResponse:
    """返回当前内存中的 Pending Workout，供前端实时刷新训练卡片列表。"""
    return JSONResponse(workout_store.get_state_snapshot())

@router.get("/workout_state/quarantined")
def list_quarantined_workouts(include_dismissed: bool = False) -> JSONResponse:
    """列出被隔离的待确认训练文件及其可恢复内容（DATA-05）。

    隔离原本是单向的：文件搬走之后既没有列表也没有重放接口，合法数据
    就等于永久丢失。这里让每份隔离文件的分段数、心率点数与运动类型可见。

    默认不返回已标记「不再提醒」的——启动提示靠这个接口，不能让用户每次
    进系统都被同一份文件拦一次。数据管理面板传 include_dismissed=true 看全部。
    """
    return JSONResponse({"files": workout_store.list_quarantined(include_dismissed)})

@router.get("/workout_state/quarantined/{name}/preview")
def preview_quarantined_workout(name: str) -> JSONResponse:
    safe_name = Path(name).name
    item = next((entry for entry in workout_store.list_quarantined(True) if entry.get("name") == safe_name), None)
    if item is None:
        return JSONResponse({"error": "未找到该隔离训练文件"}, status_code=404)
    return JSONResponse({"preview": item})

@router.post("/workout_state/quarantined/dismiss")
def dismiss_quarantined_workout(payload: dict) -> JSONResponse:
    """标记「不再提醒」，文件保留在磁盘上，可在数据管理里再处理。"""
    try:
        result = workout_store.dismiss_quarantined(str(payload.get("name") or ""))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except OSError as exc:
        return JSONResponse({"error": f"标记失败：{exc}"}, status_code=500)
    return JSONResponse(result)

@router.post("/workout_state/quarantined/delete")
def delete_quarantined_workout(payload: dict) -> JSONResponse:
    """永久删除一份隔离文件。"""
    try:
        result = workout_store.delete_quarantined(str(payload.get("name") or ""))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except OSError as exc:
        return JSONResponse({"error": f"删除失败：{exc}"}, status_code=500)
    return JSONResponse(result)

@router.post("/workout_state/quarantined/restore")
def restore_quarantined_workout(payload: dict) -> JSONResponse:
    """把一份隔离文件重放成当前待确认训练，交回用户走正常确认流程。"""
    if workout_store.get_current() is not None and not bool(payload.get("overwrite_pending")):
        return JSONResponse(
            {"error": "已有待确认训练，请确认覆盖后再载入", "code": "PENDING_WORKOUT_EXISTS"},
            status_code=409,
        )
        if not deps.external_model_settings_store.get()["external_models_enabled"] and not validation_result["is_plan"]:
            return JSONResponse({
                "status": "manual_confirmation_required",
                "valid": False,
                "content": content,
                "reason": validation_result["reason"],
                "subject": infer_training_subject(content) or "综合训练",
            }, status_code=200)
    try:
        result = workout_store.replay_quarantined(str(payload.get("name") or ""))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except (OSError, TypeError, KeyError, OverflowError, json.JSONDecodeError) as exc:
        return JSONResponse(
            {"error": f"隔离文件无法重放：{exc}"}, status_code=400
        )
    return JSONResponse({**result, "state": workout_store.get_state_snapshot()})

@router.post("/workout_state/update")
def update_workout_state(payload: dict) -> JSONResponse:
    """Handle direct edits from the structured workout editor."""
    action = payload.get("action")
    if action == "update_set":
        try:
            index = int(payload.get("index", 0))
            category = payload.get("category")
            weight = payload.get("weight_kg")
            repetitions = payload.get("repetitions")
            result = workout_store.update_set(
                index=index,
                category=str(category) if category is not None else None,
                weight_kg=float(weight) if weight is not None else None,
                repetitions=int(repetitions) if repetitions is not None else None,
            )
        except (TypeError, ValueError):
            return JSONResponse({"error": "训练组参数格式无效"}, status_code=400)
    elif action == "merge_sets":
        try:
            indices = [int(item) for item in payload.get("indices", [])]
        except (TypeError, ValueError):
            return JSONResponse({"error": "合并序号格式无效"}, status_code=400)
        # BUG-11：把编辑区草稿一并交给合并。不带 updates 时（Agent 路径、老页面）
        # 传 None，行为与从前一致。
        updates = payload.get("updates")
        note = payload.get("note")
        result = workout_store.merge_sets(
            indices,
            updates if isinstance(updates, list) else None,
            str(note) if note is not None else None,
        )
    elif action == "rename_sets":
        try:
            indices = [int(item) for item in payload.get("indices", [])]
        except (TypeError, ValueError):
            return JSONResponse({"error": "重命名序号格式无效"}, status_code=400)
        result = workout_store.rename_sets(indices, str(payload.get("category") or ""))
    elif action == "delete_set":
        try:
            result = workout_store.delete_set(int(payload.get("index", 0)))
        except (TypeError, ValueError):
            return JSONResponse({"error": "训练组序号格式无效"}, status_code=400)
    elif action == "undo_last_edit":
        result = workout_store.undo_last_edit()
    elif action == "restore_parsed_source":
        result = workout_store.restore_parsed_source()
    elif action == "confirm_with_updates":
        updates = payload.get("updates", [])
        note = str(payload.get("note") or "")
        result = workout_store.update_sets_and_confirm(
            updates,
            note,
            workout_id=payload.get("workout_id"),
            version=payload.get("version"),
            confirmation_token=payload.get("confirmation_token"),
            overwrite_duplicate=bool(payload.get("overwrite_duplicate")),
        )
    elif action == "clear":
        workout_store.clear_current()
        result = {"cleared": True}
    else:
        return JSONResponse({"error": f"未知 action: {action}"}, status_code=400)

    if "error" in result:
        status_code = 400
        if result.get("code") == "INVALID_CONFIRMATION_TOKEN":
            status_code = 403
        elif result.get("code") in {
            "NO_PENDING_WORKOUT",
            "WORKOUT_ID_MISMATCH",
            "STALE_WORKOUT_VERSION",
        }:
            status_code = 409
        return JSONResponse(result, status_code=status_code)
    return JSONResponse(result)

@pending_router.delete("/data/pending-workout")
def delete_pending_workout() -> JSONResponse:
    existed = workout_store.get_current() is not None
    workout_store.clear_current()
    return JSONResponse({"deleted": existed})

