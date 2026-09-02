"""
文件上传记录模块
==============
记录每个上传文件与其在向量库中 ID 的对应关系及存储时间，
便于后期按文件路径定位并删除向量库中的相关数据。

记录格式（JSONL，每行一条 JSON）：
{
    "file_path": "D:/docs/readme.txt",
    "file_name": "readme.txt",
    "chroma_ids": ["readme.txtid1", "readme.txtid2", ...],
    "timestamp": "2026-07-27 14:30:00",
    "collection_name": "my_collection"
}
"""

import json
import os

from tool.config_handler import Rag_Config, System_Config
from tool.logger_handler import logger


def _get_record_path() -> str:
    """获取记录文件路径，若目录不存在则自动创建。"""
    record_path = Rag_Config.get("file_record_path", "vector_uploader_service/file_record.jsonl")
    record_dir = os.path.dirname(record_path)
    if record_dir and not os.path.exists(record_dir):
        os.makedirs(record_dir, exist_ok=True)
    return record_path


def record_file(file_path: str, chroma_ids: list[str], collection_name: str) -> None:
    """
    将文件上传信息追加写入记录文件。

    参数:
        file_path:       上传文件的绝对路径
        chroma_ids:      该文件在 Chroma 中对应的所有 chunk ID 列表
        collection_name: Chroma 集合名称
    """
    import datetime

    record = {
        "file_path": os.path.abspath(file_path),
        "file_name": os.path.basename(file_path),
        "chroma_ids": chroma_ids,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "collection_name": collection_name,
    }

    record_storage_path = _get_record_path()
    encoding = System_Config.get("encoding", "utf-8")

    with open(record_storage_path, "a", encoding=encoding) as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"[file_record] 已记录: {os.path.basename(file_path)} → {len(chroma_ids)} 条向量ID")


def get_all_records() -> list[dict]:
    """
    读取全部文件上传记录。

    返回:
        list[dict]: 所有记录的列表，每项为一个字典
    """
    record_storage_path = _get_record_path()
    encoding = System_Config.get("encoding", "utf-8")

    if not os.path.exists(record_storage_path):
        return []

    records = []
    with open(record_storage_path, "r", encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"[file_record] 跳过无效行: {line[:80]}...")
    return records


def get_records_by_file(file_path: str) -> list[dict]:
    """
    根据文件绝对路径查询对应的上传记录。

    参数:
        file_path: 文件的绝对路径

    返回:
        list[dict]: 匹配的记录列表（同一文件可能多次上传）
    """
    target = os.path.abspath(file_path)
    return [r for r in get_all_records() if r.get("file_path") == target]


def get_records_by_name(file_name: str) -> list[dict]:
    """
    根据文件名查询对应的上传记录。

    参数:
        file_name: 文件名

    返回:
        list[dict]: 匹配的记录列表
    """
    return [r for r in get_all_records() if r.get("file_name") == file_name]


def remove_records_by_file(file_path: str) -> int:
    """
    从记录文件中移除指定文件的所有记录。

    参数:
        file_path: 要移除的文件绝对路径

    返回:
        int: 被移除的记录条数
    """
    target = os.path.abspath(file_path)
    all_records = get_all_records()

    kept = [r for r in all_records if r.get("file_path") != target]
    removed_count = len(all_records) - len(kept)

    if removed_count == 0:
        logger.info(f"[file_record] 未找到 {target} 的记录，无需移除")
        return 0

    record_storage_path = _get_record_path()
    encoding = System_Config.get("encoding", "utf-8")

    with open(record_storage_path, "w", encoding=encoding) as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info(f"[file_record] 已移除 {target} 的 {removed_count} 条记录")
    return removed_count


def list_all_files() -> list[str]:
    """
    列出所有已记录的上传文件路径（去重）。

    返回:
        list[str]: 去重后的文件绝对路径列表
    """
    records = get_all_records()
    seen = set()
    result = []
    for r in records:
        fp = r.get("file_path", "")
        if fp and fp not in seen:
            seen.add(fp)
            result.append(fp)
    return result
