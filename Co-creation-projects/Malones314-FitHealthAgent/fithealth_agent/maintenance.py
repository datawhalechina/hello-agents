"""maintenance.py

全局维护开关（对应需求清单 DATA-12）。

为什么需要它
------------
恢复备份要同时换掉 4 个 JSON 文件和 `health.db`。文件系统没法原子地替换
多个文件，所以真正的危险不是"换到一半"（`backup_service.restore` 已经有
快照回滚），而是**换的过程中还有别的请求在跑**：

* 一个在飞的 `add_record` 手里拿着恢复前读到的内存列表，恢复完成后它照常
  写回——直接把恢复结果覆盖掉，而且两边都"成功"了，没有任何报错；
* 任何持有 `health.db` 连接的请求，在我们删掉 `-wal` / `-shm` 之后会把旧的
  WAL 内容写回新库；Windows 上覆盖一个被打开的 `health.db` 甚至直接
  `PermissionError`。

所以恢复期间必须：先竖起开关让**新**请求拿到 503，再等**在飞**请求排空，
然后才动文件。

为什么是"排空"而不是"加锁等着"
------------------------------
恢复要同时持有若干 `JsonFileLock` 和 `HealthStore` 的访问锁。如果直接去抢，
一个已经拿着 `daily_records.json` 锁、接下来还要查 `health.db` 的在飞请求，
会与恢复形成经典的循环等待。排空 + 超时把这种情况变成一次**干净的失败**
（返回 409、数据一个字节都没动），而不是一次挂死。
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)

#: 等在飞请求排空的默认上限。个人本地单用户场景下正常请求都是毫秒级，
#: 等超过这个时间基本只能说明有请求卡住了，此时放弃比硬闯安全。
DEFAULT_DRAIN_TIMEOUT_SECONDS = 15.0


class MaintenanceBusyError(RuntimeError):
    """在飞请求没能在超时内排空，维护操作主动放弃（未做任何改动）。"""


class MaintenanceGate:
    def __init__(self) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._inflight = 0
        self._reason: str | None = None
        self._since: str | None = None

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        with self._condition:
            return self._reason is not None

    @property
    def inflight(self) -> int:
        with self._condition:
            return self._inflight

    @property
    def status(self) -> dict[str, Any]:
        with self._condition:
            return {
                "active": self._reason is not None,
                "reason": self._reason,
                "since": self._since,
                "inflight_requests": self._inflight,
            }

    # ------------------------------------------------------------------
    # 请求侧
    # ------------------------------------------------------------------

    @contextmanager
    def track_request(self):
        """把一个在飞请求计入排空计数。"""
        with self._condition:
            self._inflight += 1
        try:
            yield
        finally:
            with self._condition:
                self._inflight -= 1
                self._condition.notify_all()

    # ------------------------------------------------------------------
    # 维护侧
    # ------------------------------------------------------------------

    @contextmanager
    def exclusive(self, reason: str, *, timeout: float = DEFAULT_DRAIN_TIMEOUT_SECONDS):
        """竖起开关、等在飞请求排空，然后把独占权交给调用方。

        竖开关与排空必须是这个顺序：先让新请求 503，在飞计数才可能归零。
        """
        with self._condition:
            if self._reason is not None:
                raise MaintenanceBusyError(f"系统正在执行维护操作：{self._reason}")
            self._reason = reason
            self._since = datetime.now(timezone.utc).isoformat()
        try:
            self._drain(timeout)
            logger.info("进入维护模式：%s", reason)
            yield self
        finally:
            with self._condition:
                self._reason = None
                self._since = None
            logger.info("退出维护模式：%s", reason)

    def _drain(self, timeout: float) -> None:
        with self._condition:
            if not self._condition.wait_for(lambda: self._inflight == 0, timeout=timeout):
                remaining = self._inflight
                raise MaintenanceBusyError(
                    f"仍有 {remaining} 个请求在处理中，{timeout:.0f} 秒内没有结束；"
                    "为避免恢复过程与它们互相踩，本次操作已放弃，数据未做任何改动。请稍后重试。"
                )


#: 进程内唯一的维护开关。
MAINTENANCE = MaintenanceGate()
