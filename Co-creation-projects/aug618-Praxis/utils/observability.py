"""轻量可观测性：JSONL 事件日志"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import tiktoken

from utils.env import env_str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_log_path() -> Path:
    log_dir = env_str("CODE_AGENT_LOG_DIR")
    if log_dir:
        return Path(log_dir).expanduser().resolve() / "events.jsonl"
    # 兜底：当前工作目录下的 .helloagents/logs
    return Path.cwd() / ".helloagents" / "logs" / "events.jsonl"


def log_event(event_type: str, data: Dict[str, Any]) -> None:
    """写入结构化事件到 JSONL。失败时静默。"""
    try:
        path = _resolve_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        session_id = env_str("CODE_AGENT_SESSION_ID")
        base = {"ts": _now_iso(), "type": event_type}
        if session_id:
            base["session_id"] = session_id
        payload = {**base, **data}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # 避免日志失败影响主流程
        return


def _count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    """粗略估算 prompt tokens（适用于多模态 content）。"""
    try:
        return _count_tokens(json.dumps(messages, ensure_ascii=False))
    except Exception:
        return 0


def estimate_completion_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    return _count_tokens(text)


def measure_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)
