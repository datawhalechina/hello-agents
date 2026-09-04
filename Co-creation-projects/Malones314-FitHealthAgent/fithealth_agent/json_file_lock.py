from __future__ import annotations

import os
import time
from pathlib import Path


#: Windows 分支等锁的上限（秒）。ARCH-08：`msvcrt.locking(fd, LK_LOCK, 1)` 的
#: 语义是"每秒重试 10 次、约 10 秒后放弃"，而导出备份要一次按住 7 把 JSON 锁，
#: 持锁时长随数据量线性增长——越过 10 秒之后，恰好落在那个窗口里的一次保存
#: 计划／写酸痛记录就会直接失败。所以上限自己定，并且给足余量。
LOCK_TIMEOUT_SECONDS = 60.0
#: 重试间隔从 10ms 起、指数退避到 100ms 封顶：竞争轻时几乎不引入额外延迟，
#: 竞争重时也不会把 CPU 烧在空转上。
_RETRY_INITIAL_SECONDS = 0.01
_RETRY_MAX_SECONDS = 0.1


class JsonFileLock:
    def __init__(self, data_path: Path, *, timeout: float | None = None) -> None:
        self.path = data_path.with_suffix(data_path.suffix + ".lock")
        self.handle = None
        #: 只影响 Windows 分支；POSIX 的 `flock(LOCK_EX)` 仍然是无限等待。
        self.timeout = LOCK_TIMEOUT_SECONDS if timeout is None else timeout

    def __enter__(self) -> "JsonFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # ``a+b`` forces every write to EOF, even after seek(0). Only seed an
        # empty lock file so repeated acquisitions do not grow it forever.
        self.path.touch(exist_ok=True)
        self.handle = self.path.open("r+b")
        try:
            self.handle.seek(0, os.SEEK_END)
            if self.handle.tell() == 0:
                self.handle.write(b"\0")
                self.handle.flush()
            self.handle.seek(0)
            if os.name == "nt":
                self._acquire_windows(self.handle.fileno())
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
            return self
        except BaseException:
            # __exit__ is not called when __enter__ raises.
            try:
                self.handle.close()
            finally:
                self.handle = None
            raise

    def _acquire_windows(self, descriptor: int) -> None:
        """Windows 上自己写重试循环，超时给出中文说明（ARCH-08 修法 3）。

        原实现是裸 `LK_LOCK`：等待上限被 CRT 写死成约 10 秒，超时抛出来的是
        `OSError: Permission denied`——调用方与最终用户都看不出是哪个文件、
        被谁占着、该等还是该报错。这里换成 `LK_NBLCK` + 显式退避重试，超时
        抛 `TimeoutError`（它是 `OSError` 的子类，所以既有的 `except OSError`
        处理链一个字都不用改），消息里带上文件名与已等待时长。
        """
        import msvcrt

        deadline = time.monotonic() + self.timeout
        interval = _RETRY_INITIAL_SECONDS
        while True:
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                return
            except OSError as exc:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"数据文件 {self.path.stem} 被其他操作占用超过 "
                        f"{self.timeout:g} 秒（可能正在导出或恢复备份），"
                        "请稍后重试"
                    ) from exc
                time.sleep(min(interval, remaining))
                interval = min(interval * 2, _RETRY_MAX_SECONDS)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.handle is None:
            return
        handle = self.handle
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self.handle = None
