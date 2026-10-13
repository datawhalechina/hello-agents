"""Resource-scoped HTTP routes extracted from main."""

import sqlite3
from datetime import datetime
from typing import Any, Callable
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from fithealth_agent.backup_service import MAX_BACKUP_BYTES
from fithealth_agent.maintenance import MAINTENANCE, MaintenanceBusyError
from fithealth_agent import workout_store
from fithealth_agent.runtime import deps
from fithealth_agent.runtime.deps import logger
from fithealth_agent.runtime.upload_io import read_upload_with_limit

backup_router = APIRouter()

router = APIRouter()

@backup_router.get("/data/backup/export")
def export_backup() -> Response:
    try:
        content = deps.backup_service.export_bytes()
    except (ValueError, OSError, sqlite3.Error) as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    filename = f"fithealth-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@backup_router.post("/data/backup/inspect")
async def inspect_backup(file: UploadFile = File(...)) -> JSONResponse:
    content = await read_upload_with_limit(file, MAX_BACKUP_BYTES)
    if content is None:
        return JSONResponse({"error": "备份文件超过 1 GiB"}, status_code=413)
    try:
        files = deps.backup_service.validate(content)
    except (ValueError, OSError, sqlite3.Error) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"valid": True, "files": sorted(files), "has_health_database": "health.db" in files})

@backup_router.post("/data/backup/import")
async def import_backup(
    file: UploadFile = File(...), confirm_restore: bool = Form(False)
) -> JSONResponse:
    if not confirm_restore:
        return JSONResponse({"error": "恢复备份需要明确确认"}, status_code=409)
    content = await read_upload_with_limit(file, MAX_BACKUP_BYTES)
    if content is None:
        return JSONResponse({"error": "备份文件超过 1 GiB"}, status_code=413)
    try:
        result = deps.backup_service.restore(content)
    except MaintenanceBusyError as exc:
        # 排空超时／已有维护在进行中：数据一个字节都没动，让用户重试即可。
        return JSONResponse({"error": str(exc)}, status_code=409)
    except (ValueError, OSError, sqlite3.Error) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    # 备份现在带 pending_workout.json（DATA-11），所以这里必须**按盘重载**
    # 而不是 clear_current()——后者会把刚恢复回来的待确认训练删掉。
    workout_state = workout_store.reload_from_disk()
    callback_results = result.pop("restore_callbacks", [])
    memory_revalidated = (
        callback_results[0] if callback_results else deps.info_store.revalidate()
    )
    return JSONResponse({
        "restored": True,
        **result,
        "workout_state": workout_state,
        "memory_store_revalidated": memory_revalidated,
    })

def _reset_steps() -> tuple[tuple[str, str, Callable[[], int]], ...]:
    def reset_profile_step() -> int:
        deps.profile_store.reset()
        return 1

    def clear_pending_workout_step() -> int:
        existed = workout_store.get_current() is not None
        workout_store.clear_current()
        return 1 if existed else 0

    def clear_plan_drafts_step() -> int:
        # 进程内缓存，但里面存着完整的训练计划正文（BUG-05）。"删除全部数据"
        # 之后它还留在内存里，下一句"保存刚才的计划"就能把已删内容写回来。
        removed = len(deps.plan_draft_cache)
        deps.plan_draft_cache.clear()
        return removed

    return (
        ("records_removed", "训练与每日记录", deps.daily_record_store.clear),
        ("plans_removed", "训练计划", deps.plan_store.clear),
        ("memories_removed", "临时记忆", deps.info_store.clear),
        ("soreness_reports_removed", "肌群酸痛记录", deps.soreness_store.clear),
        ("health_imports_removed", "健康与睡眠导入", deps.health_store.clear),
        ("hr_streams_removed", "心率流文件", deps.hr_stream_store.clear),
        ("profile_reset", "用户档案", reset_profile_step),
        ("pending_workout_removed", "待确认训练", clear_pending_workout_step),
        ("quarantined_removed", "隔离的待确认训练文件", workout_store.clear_quarantined),
        ("plan_drafts_removed", "计划草稿缓存", clear_plan_drafts_step),
    )

@router.post("/data/reset")
def reset_all_data(payload: dict) -> JSONResponse:
    """清空全部本地数据。

    DATA-14：原实现把六个 store 顺序清空，`except` 只在最外层——第 3 步抛错
    时前 2 步已经**永久**删掉了，而响应里连"删掉了多少"都没有。这不是理论
    风险：`info_store.clear()` 在记忆库只读降级时抛 `MemoryStoreDegradedError`，
    `health_store.clear()` 在数据库只读降级时抛 `HealthStoreDegradedError`，
    两者都是 `RuntimeError`，绕过 `except (OSError, sqlite3.Error)` 直接被全局
    处理器转成 503，用户看到的是一句"只读降级"，完全不知道记录已经没了。

    现在分三层：
    1. **先落恢复点**，写不出来就一个字节都不删（`/data/reset` 是全仓库唯一
       不可逆的批量删除，没有退路的删除不该执行）；
    2. 持维护开关：新请求 503、在飞请求排空，快照与删除之间没有别人插进来
       写数据（否则刚写入的记录会被快照漏掉又被删掉）；
    3. 每项独立 try/except，一项失败不影响其余项，逐项成败原样返回。
    """
    if payload.get("confirmation") != "删除全部数据":
        return JSONResponse({"error": "确认短语不正确"}, status_code=400)

    try:
        with MAINTENANCE.exclusive("清空全部数据"):
            try:
                recovery_point = deps.backup_service.write_recovery_point()
            except (OSError, ValueError, sqlite3.Error):
                logger.exception("清空全部数据前的恢复点写入失败，已放弃删除")
                return JSONResponse(
                    {
                        "error": (
                            "无法在删除前生成恢复点，本次操作已放弃，数据未做任何改动。"
                            "请检查 data 目录的写入权限与剩余磁盘空间后重试。"
                        )
                    },
                    status_code=500,
                )
            results = _run_reset_steps()
    except MaintenanceBusyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)

    failures = [item for item in results if item["error"]]
    body: dict[str, Any] = {
        "deleted": not failures,
        "partial": bool(failures),
        "recovery_point": recovery_point,
        "steps": results,
        # 逐项计数同时平铺成顶层字段，保持与旧响应兼容。
        **{item["key"]: item["removed"] for item in results},
    }
    if failures:
        body["error"] = "部分数据未能删除：" + "、".join(item["label"] for item in failures)
        body["recovery_hint"] = (
            f"其余数据已删除。如需完整还原，请下载恢复点 {recovery_point['name']} "
            "并通过「导入备份」恢复；确认无误后可在「重置前恢复点」中删除它。"
        )
        # 半删状态是 200 里的 partial 而不是 500：客户端必须能读到究竟删了
        # 哪些，5xx 会让前端只显示一句"操作失败"，正是原实现的毛病。
        return JSONResponse(body, status_code=200)
    return JSONResponse(body)

@router.post("/data/reset/retry")
def retry_reset_steps(payload: dict) -> JSONResponse:
    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        return JSONResponse({"error": "请提供需要重试的清理项目"}, status_code=400)
    wanted = {str(key) for key in keys}
    steps = {key: (label, action) for key, label, action in _reset_steps()}
    results = []
    for key in wanted:
        if key not in steps:
            continue
        label, action = steps[key]
        try:
            removed = int(action() or 0)
            results.append({"key": key, "label": label, "removed": removed, "error": None})
        except Exception as exc:  # noqa: BLE001
            results.append({"key": key, "label": label, "removed": 0, "error": str(exc)})
    failures = [item for item in results if item["error"]]
    return JSONResponse({"retried": results, "partial": bool(failures), "error": "部分项目重试仍失败" if failures else None})

def _run_reset_steps() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key, label, action in _reset_steps():
        try:
            removed = int(action() or 0)
        except Exception as exc:  # noqa: BLE001
            # 刻意 catch 宽：这里有 8 个互相独立的破坏性操作，"一个失败就把
            # 后面全部跳过"正是 DATA-14 描述的缺陷。只读降级异常
            # （MemoryStoreDegradedError / HealthStoreDegradedError）是
            # RuntimeError，窄 except 抓不到它们。
            logger.exception("清空 %s 失败", label)
            results.append({"key": key, "label": label, "removed": 0, "error": str(exc)})
        else:
            results.append({"key": key, "label": label, "removed": removed, "error": None})
    return results

@router.get("/data/recovery-points")
def list_recovery_points() -> JSONResponse:
    return JSONResponse({"points": deps.backup_service.list_recovery_points()})

@router.get("/data/recovery-points/{name}")
def download_recovery_point(name: str) -> Response:
    try:
        content = deps.backup_service.read_recovery_point(name)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except (FileNotFoundError, OSError):
        return JSONResponse({"error": "未找到该恢复点"}, status_code=404)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )

@router.delete("/data/recovery-points/{name}")
def delete_recovery_point(name: str) -> JSONResponse:
    try:
        removed = deps.backup_service.delete_recovery_point(name)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except OSError as exc:
        return JSONResponse({"error": f"删除恢复点失败：{exc}"}, status_code=500)
    if not removed:
        return JSONResponse({"error": "未找到该恢复点"}, status_code=404)
    return JSONResponse({"deleted": True, "name": name})

