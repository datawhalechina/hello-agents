"""
妙想 API 本地 Fixture（原始 JSON 回放）

修前端/解析逻辑时设置 MX_REPLAY_FIXTURES=1，可将已成功请求保存为 JSON，
按 query 哈希命中文件则不再发起网络请求，节省妙想额度。

用法见 backend/scripts/capture_mx_fixture.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from app.config import settings


def fixture_path(channel: str, query: str) -> Path:
    """channel: mx_data | mx_search | mx_xuangu"""
    h = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()[:16]
    root: Path = settings.MX_FIXTURE_DIR
    return root / f"{channel}_{h}.json"


def try_load_raw_fixture(channel: str, query: str) -> Optional[dict[str, Any]]:
    """回放模式且文件存在时返回妙想原始响应 dict，否则 None"""
    if not settings.MX_REPLAY_FIXTURES:
        return None
    path = fixture_path(channel, query)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_raw_fixture(channel: str, query: str, raw: dict[str, Any]) -> Path:
    """将一次成功的原始响应写入磁盘，供后续 MX_REPLAY_FIXTURES 使用"""
    path = fixture_path(channel, query)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
