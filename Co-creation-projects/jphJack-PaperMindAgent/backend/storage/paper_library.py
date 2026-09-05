"""论文库持久化管理：data/papers_library.json

职责：
- 以 PDF 文件内容 SHA-256 作为 paper_id，跨路径/跨会话唯一标识论文
- 跟踪每篇论文的预处理状态（解析/抽取/索引三步）
- 提供增删查改与缓存状态查询
- 删除论文时联动清理缓存文件与 Chroma chunks
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# 合法的预处理状态
_STATUSES = ("pending", "done", "failed")


def compute_paper_id(file_path: str) -> str:
    """计算 PDF 文件内容的 SHA-256 作为 paper_id

    Args:
        file_path: PDF 文件路径

    Returns:
        64 字符的十六进制 SHA-256 哈希
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class PaperLibrary:
    """论文库持久化管理器

    数据存储在 data/papers_library.json，线程安全（文件锁）。
    """

    def __init__(self, library_path: Optional[Path] = None) -> None:
        self._library_path = library_path or (settings.CACHE_DIR / "papers_library.json")
        self._library_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._papers: dict[str, dict] = self._load()

    # ------------------------------------------------------------------ #
    # 持久化读写
    # ------------------------------------------------------------------ #

    def _load(self) -> dict[str, dict]:
        """从磁盘加载论文库"""
        if not self._library_path.exists():
            return {}
        try:
            with open(self._library_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("papers"), list):
                # 兼容 {"papers": [...]} 格式
                return {p["paper_id"]: p for p in data["papers"] if "paper_id" in p}
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("加载论文库失败: %s", exc)
        return {}

    def _save(self) -> None:
        """保存论文库到磁盘"""
        data = {"papers": list(self._papers.values())}
        with open(self._library_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # ------------------------------------------------------------------ #
    # 增删查改
    # ------------------------------------------------------------------ #

    def register(
        self,
        paper_id: str,
        filename: str,
        source: str,
        original_path: str,
    ) -> dict:
        """注册论文到库中。若已存在则返回现有记录（不覆盖状态）。

        Args:
            paper_id: 内容哈希
            filename: 文件名
            source: "upload" 或 "folder"
            original_path: 存储路径（上传文件为 data/uploads/{paper_id}.pdf）

        Returns:
            论文元数据 dict
        """
        with self._lock:
            if paper_id in self._papers:
                return self._papers[paper_id]
            entry = {
                "paper_id": paper_id,
                "filename": filename,
                "source": source,
                "original_path": original_path,
                "upload_time": datetime.now().isoformat(),
                "title": "",
                "parse_status": "pending",
                "extract_status": "pending",
                "index_status": "pending",
                "parsed_at": None,
                "extracted_at": None,
                "indexed_at": None,
            }
            self._papers[paper_id] = entry
            self._save()
            logger.info("注册论文: paper_id=%s, filename=%s", paper_id[:12], filename)
            return entry

    def get(self, paper_id: str) -> Optional[dict]:
        """获取单篇论文元数据，不存在返回 None"""
        with self._lock:
            return self._papers.get(paper_id)

    def list_all(self) -> list[dict]:
        """列出全部论文元数据"""
        with self._lock:
            return list(self._papers.values())

    def update_status(
        self,
        paper_id: str,
        title: Optional[str] = None,
        parse_status: Optional[str] = None,
        extract_status: Optional[str] = None,
        index_status: Optional[str] = None,
    ) -> Optional[dict]:
        """更新论文预处理状态

        Args:
            paper_id: 论文 ID
            title: 解析得到的标题（可选）
            parse_status: 解析状态
            extract_status: 抽取状态
            index_status: 索引状态

        Returns:
            更新后的元数据 dict，或 None（论文不存在）
        """
        with self._lock:
            entry = self._papers.get(paper_id)
            if entry is None:
                return None
            now = datetime.now().isoformat()
            if title is not None and title:
                entry["title"] = title
            if parse_status is not None:
                if parse_status not in _STATUSES:
                    raise ValueError(f"非法状态: {parse_status}")
                entry["parse_status"] = parse_status
                if parse_status == "done":
                    entry["parsed_at"] = now
            if extract_status is not None:
                if extract_status not in _STATUSES:
                    raise ValueError(f"非法状态: {extract_status}")
                entry["extract_status"] = extract_status
                if extract_status == "done":
                    entry["extracted_at"] = now
            if index_status is not None:
                if index_status not in _STATUSES:
                    raise ValueError(f"非法状态: {index_status}")
                entry["index_status"] = index_status
                if index_status == "done":
                    entry["indexed_at"] = now
            self._save()
            return entry

    def delete(self, paper_id: str) -> bool:
        """删除论文：移除库记录 + 删除缓存文件 + 删除 Chroma chunks

        Args:
            paper_id: 论文 ID

        Returns:
            是否删除成功
        """
        with self._lock:
            entry = self._papers.pop(paper_id, None)
            if entry is None:
                return False

        # 删除缓存文件（解析结果）
        parsed_cache = settings.CACHE_DIR / "parsed" / f"{paper_id}.json"
        if parsed_cache.exists():
            try:
                parsed_cache.unlink()
            except OSError as exc:
                logger.warning("删除解析缓存失败: %s", exc)

        # 删除缓存文件（抽取结果）
        extract_cache = settings.CACHE_DIR / "papers" / f"{paper_id}.json"
        if extract_cache.exists():
            try:
                extract_cache.unlink()
            except OSError as exc:
                logger.warning("删除抽取缓存失败: %s", exc)

        # 删除 Chroma chunks
        original_path = entry.get("original_path", "")
        if original_path:
            try:
                from backend.tools.build_vector_index import delete_paper_chunks

                delete_paper_chunks(original_path)
            except Exception as exc:
                logger.warning("删除 Chroma chunks 失败: %s", exc)

        # 删除上传的原文件（仅 upload 来源）
        if entry.get("source") == "upload":
            upload_file = Path(entry.get("original_path", ""))
            if upload_file.exists():
                try:
                    upload_file.unlink()
                except OSError as exc:
                    logger.warning("删除上传文件失败: %s", exc)

        with self._lock:
            self._save()
        logger.info("删除论文: paper_id=%s", paper_id[:12])
        return True

    def is_preprocessed(self, paper_id: str) -> bool:
        """检查论文是否已完成全部三步预处理"""
        entry = self.get(paper_id)
        if entry is None:
            return False
        return (
            entry.get("parse_status") == "done"
            and entry.get("extract_status") == "done"
            and entry.get("index_status") == "done"
        )


# 模块级单例
_library: Optional[PaperLibrary] = None


def get_paper_library() -> PaperLibrary:
    """获取 PaperLibrary 单例"""
    global _library
    if _library is None:
        _library = PaperLibrary()
    return _library
