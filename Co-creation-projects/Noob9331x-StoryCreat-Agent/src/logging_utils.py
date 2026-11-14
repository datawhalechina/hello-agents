"""日志与 JSONL 追踪工具。

提供统一的 logger 获取入口，以及线程/进程安全的 JSONL 追加写入，
用于 `outputs/runs/<run_id>/trace.jsonl`（FR-12）。
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """配置根 logger（仅首次调用生效）。

    Args:
        level: 日志级别名称，如 ``INFO``、``DEBUG``。
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """获取项目命名空间下的 logger。

    Args:
        name: 模块名或组件名，例如 ``pipeline``。

    Returns:
        带 ``story_agent.`` 前缀的 logger。
    """
    return logging.getLogger(f"story_agent.{name}")


def append_jsonl(path: Path | str, payload: dict[str, Any]) -> bool:
    """向 JSONL 文件追加一行记录。

    写入失败只记录日志、不向上抛出，避免落盘问题影响主流程（FR-10）。

    Args:
        path: 目标文件路径。
        payload: 可 JSON 序列化的字典。

    Returns:
        写入成功返回 True，失败返回 False。
    """
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with _LOCK:
            with target.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return True
    except OSError as exc:  # pragma: no cover - 依赖文件系统异常
        get_logger("logging_utils").warning("写入 JSONL 失败 %s: %s", target, exc)
        return False
