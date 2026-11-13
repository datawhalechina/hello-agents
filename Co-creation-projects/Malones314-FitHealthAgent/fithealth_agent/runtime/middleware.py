"""全局 HTTP 中间件与降级异常处理器（main.py 拆分：阶段 2）。

本模块只定义处理函数和显式的 ``register(app)`` 接线入口；导入模块本身不修改
FastAPI 应用，避免隐藏的 import 副作用。维护白名单集中在这里，路径字符串属于
排空协议的一部分，修改时必须同步跑维护与备份事务专项测试。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fithealth_agent.health_store import HealthStoreDegradedError
from fithealth_agent.info_store import MemoryStoreDegradedError
from fithealth_agent.maintenance import MAINTENANCE


logger = logging.getLogger("fithealth")


#: 维护期间仍然放行的路径。诊断接口必须能访问，否则用户被 503 挡住之后
#: 连“系统现在在干什么”都看不到；页面本身也要能打开。
MAINTENANCE_ALLOWED_PATHS = frozenset({"/", "/health/storage-status"})
#: 发起维护的请求自己不计入在飞计数，否则排空会等它自己，直接死等。
MAINTENANCE_UNTRACKED_PATHS = frozenset({"/data/backup/import", "/data/reset"})


async def maintenance_guard(request: Request, call_next):
    """DATA-12：恢复备份期间拒绝其他请求，并统计在飞请求供排空使用。

    只有先让**新**请求拿到 503，在飞计数才有可能归零；两件事都在这里做，
    才不会漏掉任何一条路由。
    """
    path = request.url.path
    if MAINTENANCE.active and path not in MAINTENANCE_ALLOWED_PATHS:
        return JSONResponse(
            {
                "error": f"系统正在执行维护操作（{MAINTENANCE.status['reason']}），请稍后重试。",
                "maintenance": MAINTENANCE.status,
            },
            status_code=503,
        )
    if path in MAINTENANCE_UNTRACKED_PATHS:
        return await call_next(request)
    with MAINTENANCE.track_request():
        return await call_next(request)


async def health_store_degraded_handler(
    request: Request, exc: HealthStoreDegradedError
) -> JSONResponse:
    """健康数据库只读降级时统一回 503。

    DATA-09：原实现在数据目录不可用时切到系统临时目录后仍然允许写入，
    用户看到“导入成功”，而 Windows 清理 %TEMP% 时那些数据直接蒸发。
    """
    logger.error("健康数据库写入被拒绝：%s", exc)
    return JSONResponse(
        {
            "error": str(exc),
            "health_store_degraded": True,
            "database_path": str(exc.database_path) if exc.database_path else None,
            "recovery_hint": (
                "健康数据库当前不可写，已停止一切写入以避免把新数据写进注定消失的临时目录。"
                "请检查 data 目录的写入权限或修复 health.db，"
                "然后调用 /health/storage-status 重新校验（无需重启）。"
            ),
        },
        status_code=503,
    )


async def memory_store_degraded_handler(
    request: Request, exc: MemoryStoreDegradedError
) -> JSONResponse:
    """记忆库只读降级时统一回 503，而不是把写入失败伪装成 500。

    DATA-08：读失败绝不能变成“读到空库”，写入必须显式失败，否则一次意外
    就会把整个记忆库覆盖掉。这里同时把隔离副本路径告诉用户，便于人工恢复。
    """
    logger.error("记忆库写入被拒绝：%s", exc)
    return JSONResponse(
        {
            "error": str(exc),
            "memory_store_degraded": True,
            "quarantine_path": str(exc.quarantine_path) if exc.quarantine_path else None,
            "recovery_hint": (
                "记忆库文件当前无法解析，已停止一切写入以保护原有记忆。"
                "请修复 data/info_store.json（可参考同目录下的 .corrupt-* 隔离副本），"
                "然后重启服务或调用 /health/storage-status 重新校验。"
            ),
        },
        status_code=503,
    )


def register(app: FastAPI) -> None:
    """把全局中间件和异常处理器显式注册到应用。"""
    app.middleware("http")(maintenance_guard)
    app.add_exception_handler(HealthStoreDegradedError, health_store_degraded_handler)
    app.add_exception_handler(MemoryStoreDegradedError, memory_store_degraded_handler)
