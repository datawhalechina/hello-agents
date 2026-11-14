"""示例请求加载（批量评测与前端示例共用）。

``data/samples.json`` 是唯一的示例数据源，结构为对象数组，字段与
:class:`~src.models.StoryRequest` 对齐，另可带 ``id`` 与 ``note``。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .logging_utils import get_logger

logger = get_logger("samples")

DEFAULT_SAMPLES_PATH = Path(__file__).resolve().parent.parent / "data" / "samples.json"


def load_samples(path: Path | str | None = None) -> list[dict[str, Any]]:
    """读取示例请求列表。

    Args:
        path: JSON 文件路径，缺省使用 ``data/samples.json``。

    Returns:
        示例字典列表；文件缺失或格式非法时返回空列表（不抛异常）。
    """
    target = Path(path) if path else DEFAULT_SAMPLES_PATH
    if not target.exists():
        logger.warning("示例数据不存在：%s", target)
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("读取示例数据失败 %s: %s", target, exc)
        return []
    if not isinstance(payload, list):
        logger.warning("示例数据顶层必须是数组：%s", target)
        return []
    return [item for item in payload if isinstance(item, dict)]
