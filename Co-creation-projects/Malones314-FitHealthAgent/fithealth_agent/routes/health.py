"""Resource-scoped HTTP routes extracted from main."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fithealth_agent.maintenance import MAINTENANCE
from fithealth_agent.runtime import deps

storage_router = APIRouter()

audit_router = APIRouter()

daily_router = APIRouter()

router = APIRouter()

@storage_router.get("/health/storage-status")
def health_storage_status() -> JSONResponse:
    # revalidate() 会重新尝试加载：用户修好文件/权限后无需重启即可解除降级。
    memory_status = deps.info_store.storage_status()
    if not memory_status["available"] and deps.info_store.revalidate():
        memory_status = deps.info_store.storage_status()
    health_status = deps.health_store.storage_status()
    if not health_status["available"] and deps.health_store.revalidate():
        health_status = deps.health_store.storage_status()
    payload = {
        "memory_store": memory_status,
        "health_store": health_status,
        "external_model_settings": deps.external_model_settings_store.storage_status(),
        "maintenance": MAINTENANCE.status,
    }
    if not health_status["available"]:
        return JSONResponse(
            {
                "available": False,
                "message": (
                    "健康数据库无法访问，原有健康数据未加载，且已转为**只读**："
                    "查询接口可用，但导入与删除都会被拒绝（不再把新数据写进注定消失的临时目录）。"
                    f"原因：{health_status['degraded_reason']}。"
                    "请检查 data 目录的写入权限或修复 health.db 后重新访问本接口。"
                ),
                **payload,
            }
        )
    if not memory_status["available"]:
        return JSONResponse(
            {
                "available": False,
                "message": (
                    "记忆库文件无法解析，已进入只读降级：现有记忆不会被覆盖，但无法保存新记忆。"
                    f"原因：{memory_status['degraded_reason']}。"
                    "请修复 data/info_store.json 后重新访问本接口。"
                ),
                **payload,
            }
        )
    if not health_status["journal_mode_safe"]:
        # DATA-09：WAL 与 DELETE 都没设上，当前模式没有崩溃恢复能力。
        # 数据现在是好的，所以 available 仍为 True，但必须让用户看见。
        return JSONResponse(
            {
                "available": True,
                "message": (
                    f"健康数据库当前的 journal 模式是 {health_status['journal_mode']}，"
                    "崩溃或断电会留下结构性损坏的数据库。WAL 与 DELETE 都无法启用，"
                    "通常说明 data 目录所在的文件系统不支持（例如某些网络盘）。"
                ),
                **payload,
            }
        )
    return JSONResponse({"available": True, **payload})

@audit_router.get("/health/imports/raw-audit")
def audit_health_raw_files() -> JSONResponse:
    return JSONResponse(deps.health_store.audit_raw_files())

@audit_router.delete("/health/imports/raw-orphans/{name}")
def delete_health_raw_orphan(name: str) -> JSONResponse:
    try:
        removed = deps.health_store.delete_orphan_raw_file(name)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if not removed:
        return JSONResponse({"error": "未找到孤立的健康原始文件"}, status_code=404)
    return JSONResponse({"deleted": True, "name": name})

@audit_router.get("/data/hr-streams/audit")
def audit_hr_streams() -> JSONResponse:
    return JSONResponse(deps.hr_stream_store.audit(deps.daily_record_store.list_records()))

@audit_router.delete("/data/hr-streams/orphans/{name}")
def delete_hr_stream_orphan(name: str) -> JSONResponse:
    try:
        removed = deps.hr_stream_store.delete_orphan(
            name, deps.daily_record_store.list_records()
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if not removed:
        return JSONResponse({"error": "未找到孤立的心率流文件"}, status_code=404)
    return JSONResponse({"deleted": True, "name": name})

@daily_router.get("/health/daily/{day}")
def get_daily_health(day: str) -> JSONResponse:
    try:
        return JSONResponse(deps.health_store.get_daily_health(day))
    except ValueError:
        return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)

@daily_router.get("/health/overview")
def get_daily_overview(day: str | None = None) -> JSONResponse:
    try:
        overview = deps.health_store.get_daily_overview(day)
        return JSONResponse(overview)
    except ValueError:
        return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)

@router.get("/health/range")
def get_health_range(start_date: str, end_date: str) -> JSONResponse:
    try:
        return JSONResponse({"items": deps.health_store.get_health_range(start_date, end_date)})
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

@router.get("/health/trend")
def get_health_trend(metric: str, period: str, end_date: str | None = None) -> JSONResponse:
    try:
        return JSONResponse(deps.health_store.get_metric_trend(metric, period, end_date))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

@router.get("/health/sleep/{day}")
def get_sleep_health(day: str) -> JSONResponse:
    try:
        item = deps.health_store.get_sleep(day)
    except ValueError:
        return JSONResponse({"error": "日期格式必须为 YYYY-MM-DD"}, status_code=400)
    if item is None:
        return JSONResponse({"error": "未找到该日期的睡眠数据"}, status_code=404)
    return JSONResponse(item)

@router.get("/health/imports/{import_id}")
def get_health_import(import_id: str) -> JSONResponse:
    item = deps.health_store.get_import_detail(import_id)
    if item is None:
        return JSONResponse({"error": "未找到该健康数据导入"}, status_code=404)
    return JSONResponse(item)

@router.delete("/health/imports/{import_id}")
def delete_health_import(import_id: str) -> JSONResponse:
    if not deps.health_store.delete_import(import_id):
        return JSONResponse({"error": "未找到该健康数据导入"}, status_code=404)
    return JSONResponse({"deleted": True, "id": import_id})

