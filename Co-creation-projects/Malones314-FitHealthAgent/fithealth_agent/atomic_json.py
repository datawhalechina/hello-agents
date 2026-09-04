"""atomic_json.py

JSON 落盘的**唯一**持久化写入点（对应需求清单 DATA-06 与 DATA-07）。

为什么不能直接 `write_text` + `replace`
--------------------------------------
`Path.write_text` 只把内容交给 OS 页缓存，`os.replace` 只保证**目录项替换**
是原子的——它对"内容是否已经落盘"不作任何承诺。Windows 上突然断电，
`daily_records.json` 可以变成 0 字节或者半截文件：目录项已经指向新文件，
而新文件的数据块还没写出去。所以每个写路径都必须 `flush` + `os.fsync`
之后才 `replace`。

为什么临时文件名要带 pid + uuid4
--------------------------------
固定的 `<name>.tmp` 会让两个并发写入同时 `open("w")` 同一个临时文件，
交错写入后 replace 出去的是**两份 JSON 拼在一起的垃圾**。DATA-07 里
`user_profile.json.tmp` 的原始实现正是这样。名字带上 pid + uuid4 之后，
每个写入者都有自己的临时文件，最坏情况只是"后写的赢"，而不是产出垃圾。

约定
----
`fithealth_agent/` 下所有 JSON 写路径都应该走这里。串行化（谁先谁后、
read-modify-write 是否原子）仍然是调用方的责任——用 `JsonFileLock` 解决，
本模块只负责"写出去的那一份要么是旧的、要么是完整的新的"。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


def temp_write_path(path: Path) -> Path:
    """给 `path` 生成一个进程内唯一的临时文件路径。"""
    return path.with_name(f"{path.name}.{os.getpid()}.{uuid4().hex}.tmp")


def atomic_write_json(path: Path, data: Any, *, indent: int | None = 2) -> None:
    """把 `data` 序列化后持久化到 `path`：先 fsync 临时文件，再原子替换。"""
    temp_path = temp_write_path(path)
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=indent)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    finally:
        # 替换成功后临时文件已经不在了；失败时这里负责不留垃圾。
        temp_path.unlink(missing_ok=True)
    _fsync_directory(path.parent)


def _fsync_directory(directory: Path) -> None:
    """让 `replace` 这次目录项变更本身也落盘。

    刻意做成 best-effort：Windows 上根本无法 fsync 目录（`os.open` 打不开
    目录句柄），而这一步失败也不该让一次**已经 fsync 过内容**的写入报错——
    最坏情况是崩溃后看到替换前的旧文件，那仍然是一份完整数据。
    """
    if os.name == "nt":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError as exc:
        logger.debug("目录 %s fsync 失败（已忽略）：%s", directory, exc)
    finally:
        os.close(descriptor)
