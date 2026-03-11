"""会话/事件日志处理工具（与 CLI/TUI 共用）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def load_events(log_path: Path) -> list[dict]:
    """从 JSONL 读取事件列表。"""
    if not log_path.exists():
        return []
    events: list[dict] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events


def parse_ts(ts: str) -> datetime | None:
    """解析 ISO 时间戳字符串。"""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def summarize_session(events: list[dict]) -> dict:
    """汇总会话统计信息。"""
    stats = {
        "turns": 0,
        "tool_calls": 0,
        "tool_errors": 0,
        "llm_calls": 0,
        "llm_errors": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "prompt_tokens_est": 0,
        "completion_tokens_est": 0,
        "duration_ms": None,
        "start_ts": None,
        "end_ts": None,
    }
    for e in events:
        et = e.get("type")
        if et == "session_start":
            stats["start_ts"] = e.get("ts")
        elif et == "session_end":
            stats["end_ts"] = e.get("ts")
            stats["turns"] = e.get("turns", stats["turns"])
        elif et == "tool":
            stats["tool_calls"] += 1
            if not e.get("ok", True):
                stats["tool_errors"] += 1
        elif et == "llm":
            stats["llm_calls"] += 1
            if not e.get("ok", True):
                stats["llm_errors"] += 1
            stats["prompt_tokens"] += e.get("prompt_tokens") or 0
            stats["completion_tokens"] += e.get("completion_tokens") or 0
            stats["prompt_tokens_est"] += e.get("prompt_tokens_est") or 0
            stats["completion_tokens_est"] += e.get("completion_tokens_est") or 0

    if stats["start_ts"] and stats["end_ts"]:
        start_dt = parse_ts(stats["start_ts"])
        end_dt = parse_ts(stats["end_ts"])
        if start_dt and end_dt:
            stats["duration_ms"] = int((end_dt - start_dt).total_seconds() * 1000)
    return stats


def export_session(session_id: str, events: list[dict], export_dir: Path) -> Path:
    """导出会话事件为 JSON 文件。"""
    export_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_session(events)
    payload = {
        "session_id": session_id,
        "summary": summary,
        "events": events,
    }
    export_path = export_dir / f"session_{session_id}.json"
    with export_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return export_path
