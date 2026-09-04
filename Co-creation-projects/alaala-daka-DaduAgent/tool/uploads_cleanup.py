"""
uploads/ 目录定时清理模块
========================
清理 uploads/ 下超期未修改的聊天附件 / Agent 临时文件，保护知识库（RAG）源文件。

设计要点：
- 与 api/files.py 共用同一锚定：UPLOAD_DIR = <项目根>/uploads（即 file_manage 沙箱根）。
- 「知识库文件」判定：凡在 file_record.jsonl 中有记录（RAG 上传时会写入）的文件一律保留。
- 删除条件：mtime 距今严格超过 retention_days（默认 3 天）。
- 零新依赖：由 server.py 的 lifespan 用 asyncio.create_task 驱动周期循环。
"""

import asyncio
import os
import time

from tool.config_handler import FileManage_Config
from tool.logger_handler import logger
from tool.path_tool import get_project_root
from vector_uploader_service.file_record import get_all_records

# 上传目录固定锚定到项目根，与 api/files.py 的 UPLOAD_DIR 保持一致（file_manage 沙箱根）
UPLOAD_DIR = os.path.join(get_project_root(), "uploads")


def _normalize(path: str) -> str:
    """统一路径表示，消除 Windows 大小写 / 分隔符差异。"""
    return os.path.normcase(os.path.abspath(path))


def collect_expired_files(upload_dir: str, cutoff_ts: float, protected_paths: set[str]) -> list[str]:
    """返回 upload_dir 下「普通文件 且 非保护 且 mtime < cutoff_ts」的绝对路径列表。

    - 跳过子目录（uploads/ 为扁平目录，仅文件可清理，目录本身是沙箱根需保留）。
    - protected_paths 需已用 _normalize 归一化。
    """
    if not os.path.isdir(upload_dir):
        return []
    expired: list[str] = []
    for name in os.listdir(upload_dir):
        full = os.path.join(upload_dir, name)
        if not os.path.isfile(full):
            continue
        if _normalize(full) in protected_paths:
            continue
        try:
            if os.path.getmtime(full) < cutoff_ts:
                expired.append(full)
        except OSError:
            logger.warning(f"[uploads_cleanup] 无法读取 mtime，跳过: {name}")
    return expired


def cleanup_uploads(upload_dir: str | None = None, retention_days: int | None = None) -> int:
    """清理 uploads/ 下超期未修改的临时文件，返回删除数量。

    - 知识库（RAG）文件受保护：有 file_record 记录的路径不删。
    - 逐个 try/except OSError（Windows 文件占用等），不影响其余文件。
    - upload_dir 不存在时直接返回 0（上传目录会由上传接口按需创建）。
    """
    upload_dir = upload_dir or UPLOAD_DIR
    if retention_days is None:
        retention_days = FileManage_Config.get("uploads_cleanup_retention_days", 3)
    if not os.path.isdir(upload_dir):
        return 0

    cutoff_ts = time.time() - float(retention_days) * 86400
    protected = {_normalize(r["file_path"]) for r in get_all_records() if r.get("file_path")}

    removed = 0
    for full in collect_expired_files(upload_dir, cutoff_ts, protected):
        name = os.path.basename(full)
        try:
            os.remove(full)
            removed += 1
            logger.info(f"[uploads_cleanup] 已清理过期文件: {name}")
        except OSError as e:
            logger.warning(f"[uploads_cleanup] 文件被占用，跳过: {name} ({e})")
    if removed:
        logger.info(f"[uploads_cleanup] 本次清理 {removed} 个文件")
    return removed


_cleanup_task: asyncio.Task | None = None


async def _cleanup_loop() -> None:
    """周期任务：启动即清理一次（清掉上次关闭至今积压的过期文件），之后每 interval 秒一次。"""
    interval_days = FileManage_Config.get("uploads_cleanup_interval_days", 3)
    # 兜底下限 60s，避免误配 0/负数导致忙循环
    interval_sec = max(int(interval_days) * 86400, 60)
    while True:
        try:
            # 同步文件 I/O 放到线程池，避免阻塞事件循环
            await asyncio.to_thread(cleanup_uploads)
        except Exception:
            logger.exception("[uploads_cleanup] 清理任务异常，继续下一轮")
        await asyncio.sleep(interval_sec)


def start_uploads_cleanup() -> asyncio.Task | None:
    """启动 uploads/ 定时清理后台任务（幂等）。禁用时返回 None。"""
    global _cleanup_task
    if not FileManage_Config.get("uploads_cleanup_enabled", True):
        logger.info("[uploads_cleanup] 已禁用（uploads_cleanup_enabled=false）")
        return None
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info("[uploads_cleanup] uploads/ 定时清理任务已启动")
    return _cleanup_task


def stop_uploads_cleanup() -> None:
    """取消 uploads/ 定时清理后台任务。"""
    global _cleanup_task
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        _cleanup_task = None
        logger.info("[uploads_cleanup] uploads/ 定时清理任务已停止")
