"""文件夹扫描工具：收集指定文件夹下所有 PDF 文件"""
from __future__ import annotations

import asyncio
import os

from backend.tools.base import Tool


def _scan_folder_sync(folder_path: str) -> dict:
    """同步遍历文件夹收集 .pdf 文件"""
    pdf_files: list[str] = []
    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            if name.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, name))
    # 排序保证顺序稳定
    pdf_files.sort()
    return {
        "folder": folder_path,
        "pdf_files": pdf_files,
        "count": len(pdf_files),
    }


async def scan_folder(folder_path: str) -> dict:
    """扫描文件夹，返回所有 PDF 文件路径列表。

    失败时返回 {"error": "..."} 不抛异常。
    """
    try:
        return await asyncio.to_thread(_scan_folder_sync, folder_path)
    except Exception as e:
        return {
            "error": f"文件夹扫描失败: {e}",
            "folder": folder_path,
            "pdf_files": [],
            "count": 0,
        }


# ---------- Tool 定义 ----------

_PARAMETERS = {
    "type": "object",
    "properties": {
        "folder_path": {
            "type": "string",
            "description": "待扫描的文件夹绝对路径",
        }
    },
    "required": ["folder_path"],
}

scan_folder_tool = Tool(
    name="scan_folder",
    description=(
        "扫描指定文件夹，递归收集所有 .pdf 文件路径。"
        "返回 {folder, pdf_files, count}。"
    ),
    parameters=_PARAMETERS,
    func=scan_folder,
)
