"""行程历史记录API路由"""
from fastapi import APIRouter, HTTPException, Request, Query
from ...models.schemas import SaveHistoryRequest
from ...database import save_trip_history, list_trip_history, get_trip_history, delete_trip_history
from .auth import require_auth

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.post("", summary="保存行程到历史记录")
async def save_history(req: SaveHistoryRequest, request: Request):
    """保存生成的行程到历史记录"""
    user = require_auth(request)
    import json
    plan_json = json.dumps(req.plan_data, ensure_ascii=False)
    hid = save_trip_history(
        user_id=user["id"],
        city=req.city,
        start_date=req.start_date,
        end_date=req.end_date,
        travel_days=req.travel_days,
        preferences=",".join(req.preferences) if req.preferences else "",
        traveler_group=req.traveler_group or "",
        plan_data=plan_json,
    )
    return {"success": True, "message": "保存成功", "history_id": hid}


@router.get("", summary="获取历史记录列表")
async def list_history(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """获取当前用户的行程历史记录列表"""
    user = require_auth(request)
    offset = (page - 1) * page_size
    records = list_trip_history(user["id"], limit=page_size, offset=offset)
    return {"success": True, "records": records}


@router.get("/{history_id}", summary="获取历史记录详情")
async def get_history(history_id: int, request: Request):
    """获取单条历史记录的完整行程数据"""
    user = require_auth(request)
    record = get_trip_history(history_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    import json
    plan_data = json.loads(record["plan_data"]) if isinstance(record["plan_data"], str) else record["plan_data"]
    return {"success": True, "record": {
        "id": record["id"],
        "city": record["city"],
        "start_date": record["start_date"],
        "end_date": record["end_date"],
        "travel_days": record["travel_days"],
        "preferences": record["preferences"],
        "traveler_group": record["traveler_group"],
        "created_at": record["created_at"],
        "plan_data": plan_data,
    }}


@router.delete("/{history_id}", summary="删除历史记录")
async def delete_history(history_id: int, request: Request):
    """删除一条历史记录"""
    user = require_auth(request)
    deleted = delete_trip_history(history_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "message": "删除成功"}
