"""
uploads/ 定时清理模块测试
========================
覆盖 tool/uploads_cleanup.py：过期删除、知识库保护、严格边界语义、子目录跳过、
目录不存在、Windows 文件占用兜底，以及后台任务的启动/停止接线。

不联网、不起真实服务器，全部用 tmp_path + os.utime 构造文件。
"""

import asyncio
import os
import time

import pytest

import tool.uploads_cleanup as uc


def _write(path, content="x", mtime_ts=None):
    """写文件并可选设置 mtime。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mtime_ts is not None:
        os.utime(path, (mtime_ts, mtime_ts))
    return path


def test_cleanup_deletes_expired_keeps_fresh(tmp_path):
    """过期（5 天前）文件被删，新鲜文件保留，upload_dir 目录本身保留。"""
    now = time.time()
    _write(tmp_path / "old.txt", mtime_ts=now - 5 * 86400)
    _write(tmp_path / "fresh.txt", mtime_ts=now)

    removed = uc.cleanup_uploads(str(tmp_path), retention_days=3)

    assert removed == 1
    assert not (tmp_path / "old.txt").exists()
    assert (tmp_path / "fresh.txt").exists()
    assert tmp_path.is_dir()  # 目录本身不被删


def test_cleanup_protects_kb_files(tmp_path, monkeypatch):
    """有 file_record 记录的知识库文件即使超期也不删，未受保护文件照常删。"""
    now = time.time()
    _write(tmp_path / "kb.txt", mtime_ts=now - 10 * 86400)
    _write(tmp_path / "chat.txt", mtime_ts=now - 10 * 86400)

    monkeypatch.setattr(
        uc, "get_all_records",
        lambda: [{"file_path": str(tmp_path / "kb.txt")}],
    )

    removed = uc.cleanup_uploads(str(tmp_path), retention_days=3)

    assert removed == 1
    assert (tmp_path / "kb.txt").exists()    # 知识库文件受保护
    assert not (tmp_path / "chat.txt").exists()  # 聊天附件被清理


def test_cleanup_strict_retention_boundary(tmp_path):
    """严格「超过」语义（collect_expired_files 层，cutoff 可控、确定性）。"""
    cutoff_ts = time.time() - 3 * 86400
    _write(tmp_path / "boundary.txt", mtime_ts=cutoff_ts)   # mtime == cutoff → 保留
    _write(tmp_path / "older.txt", mtime_ts=cutoff_ts - 1)  # mtime < cutoff → 删除

    expired = uc.collect_expired_files(str(tmp_path), cutoff_ts, protected_paths=set())

    assert expired == [str(tmp_path / "older.txt")]


def test_cleanup_near_boundary_margin(tmp_path):
    """cleanup_uploads 层：接近但未满 3 天（留 30s 余量防时钟漂移）的文件保留，超过的被删。"""
    now = time.time()
    _write(tmp_path / "under.txt", mtime_ts=now - (3 * 86400 - 30))  # 未满 3 天
    _write(tmp_path / "over.txt", mtime_ts=now - (3 * 86400 + 30))   # 超过 3 天

    removed = uc.cleanup_uploads(str(tmp_path), retention_days=3)

    assert removed == 1
    assert (tmp_path / "under.txt").exists()   # 未超过 3 天 → 保留
    assert not (tmp_path / "over.txt").exists()  # 超过 3 天 → 删除


def test_cleanup_skips_subdirs(tmp_path):
    """子目录及其内部文件不被清理（uploads/ 为扁平目录）。"""
    now = time.time()
    _write(tmp_path / "nested" / "a.txt", mtime_ts=now - 10 * 86400)
    _write(tmp_path / "top_old.txt", mtime_ts=now - 10 * 86400)

    removed = uc.cleanup_uploads(str(tmp_path), retention_days=3)

    assert removed == 1
    assert (tmp_path / "nested" / "a.txt").exists()  # 子目录内文件不动
    assert not (tmp_path / "top_old.txt").exists()   # 顶层过期文件照常删


def test_cleanup_missing_dir_returns_zero(tmp_path):
    """目录不存在时返回 0，不报错。"""
    assert uc.cleanup_uploads(str(tmp_path / "nope"), retention_days=3) == 0


def test_cleanup_survives_remove_error(tmp_path, monkeypatch):
    """Windows 文件占用（PermissionError）时跳过该文件，其余照常删除。"""
    now = time.time()
    _write(tmp_path / "locked.txt", mtime_ts=now - 10 * 86400)
    _write(tmp_path / "normal.txt", mtime_ts=now - 10 * 86400)

    real_remove = os.remove

    def flaky_remove(path):
        if os.path.basename(path) == "locked.txt":
            raise PermissionError("文件被占用")
        real_remove(path)

    monkeypatch.setattr(uc.os, "remove", flaky_remove)

    removed = uc.cleanup_uploads(str(tmp_path), retention_days=3)

    assert removed == 1
    assert (tmp_path / "locked.txt").exists()   # 占用文件被跳过
    assert not (tmp_path / "normal.txt").exists()


def test_collect_expired_filters_by_cutoff(tmp_path):
    """collect_expired_files 只收集 mtime 早于 cutoff 的非保护普通文件。"""
    now = time.time()
    _write(tmp_path / "a.txt", mtime_ts=now - 10 * 86400)
    _write(tmp_path / "b.txt", mtime_ts=now)
    protected = {uc._normalize(str(tmp_path / "a.txt"))}

    expired = uc.collect_expired_files(
        str(tmp_path), cutoff_ts=now - 3 * 86400, protected_paths=protected
    )

    assert expired == []  # a.txt 受保护，b.txt 未过期


def test_start_stop_uploads_cleanup(tmp_path, monkeypatch):
    """start 启动即清理一次并返回任务；stop 取消任务。"""
    calls: list[str] = []
    monkeypatch.setattr(
        uc, "cleanup_uploads",
        lambda *a, **k: calls.append("run") or 0,
    )

    async def main():
        task = uc.start_uploads_cleanup()
        assert task is not None and not task.done()
        # 等待第一轮清理执行
        for _ in range(100):
            if calls:
                break
            await asyncio.sleep(0.01)
        assert calls, "启动后应立即清理一次"
        uc.stop_uploads_cleanup()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return task

    task = asyncio.run(main())
    assert task.cancelled()


def test_start_returns_none_when_disabled(monkeypatch):
    """uploads_cleanup_enabled=false 时 start 返回 None、不启动任务。"""
    monkeypatch.setattr(uc, "FileManage_Config", {"uploads_cleanup_enabled": False})
    assert uc.start_uploads_cleanup() is None
