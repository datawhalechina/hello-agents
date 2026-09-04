"""Server-side validation and character budgets for chat context."""

from __future__ import annotations

import json
import math
from datetime import date
from typing import Any


CHAT_REQUEST_MAX_BYTES = 256 * 1024
CHAT_MESSAGE_MAX_CHARS = 12_000
UPLOADED_PLAN_MESSAGE_MAX_CHARS = 48_000
HISTORY_ACCEPTED_MAX_ITEMS = 20
HISTORY_CONTEXT_MAX_ITEMS = 8
HISTORY_ITEM_MAX_CHARS = 4_000
HISTORY_TOTAL_MAX_CHARS = 12_000
AGENT_INPUT_MAX_CHARS = 65_536

ALLOWED_SOURCES = {"chat", "uploaded_plan"}
ROLE_ALIASES = {"user": "user", "assistant": "assistant", "bot": "assistant"}

#: 历史被裁剪时留下的标记。任何带有这些标记的文本都是**残缺**的，
#: 绝不能当作完整内容落盘（BUG-05）。
HISTORY_ITEM_TRUNCATION_MARKER = "\n[历史消息已截断]"
HISTORY_TOTAL_TRUNCATION_MARKER = "\n[历史上下文预算已用尽]"
TRUNCATION_MARKERS = (
    HISTORY_ITEM_TRUNCATION_MARKER.strip(),
    HISTORY_TOTAL_TRUNCATION_MARKER.strip(),
)


def contains_truncation_marker(text: str) -> bool:
    """判断文本是否是被上下文预算裁剪过的残片。"""
    if not isinstance(text, str):
        return False
    return any(marker in text for marker in TRUNCATION_MARKERS)


class ContextInputError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, field: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field


def _truncate_with_marker(text: str, limit: int, marker: str) -> str:
    if len(text) <= limit:
        return text
    if limit <= len(marker):
        return marker[:limit]
    return text[: limit - len(marker)] + marker


def validate_chat_request_headers(content_type: str | None, content_length: str | None) -> None:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise ContextInputError(
            "UNSUPPORTED_MEDIA_TYPE",
            "聊天接口只接受 application/json。",
            status_code=415,
        )

    if content_length is None or content_length == "":
        return
    try:
        declared_length = int(content_length)
    except ValueError as exc:
        raise ContextInputError("INVALID_CONTENT_LENGTH", "Content-Length 无效。") from exc
    if declared_length < 0:
        raise ContextInputError("INVALID_CONTENT_LENGTH", "Content-Length 无效。")
    if declared_length > CHAT_REQUEST_MAX_BYTES:
        raise ContextInputError(
            "REQUEST_TOO_LARGE",
            "聊天请求不能超过 256 KiB。",
            status_code=413,
        )


def _normalize_history(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContextInputError("INVALID_HISTORY", "history 必须是数组。", field="history")
    if len(value) > HISTORY_ACCEPTED_MAX_ITEMS:
        raise ContextInputError(
            "HISTORY_TOO_LARGE",
            f"历史消息不能超过 {HISTORY_ACCEPTED_MAX_ITEMS} 条。",
            status_code=413,
            field="history",
        )

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        field = f"history[{index}]"
        if not isinstance(item, dict):
            raise ContextInputError("INVALID_HISTORY_ITEM", "历史消息必须是对象。", field=field)
        role = item.get("role")
        if role not in ROLE_ALIASES:
            raise ContextInputError(
                "INVALID_HISTORY_ROLE",
                "历史消息角色只允许 user、assistant 或 bot。",
                field=f"{field}.role",
            )
        text = item.get("text")
        if not isinstance(text, str):
            raise ContextInputError(
                "INVALID_HISTORY_TEXT",
                "历史消息 text 必须是字符串。",
                field=f"{field}.text",
            )
        text = text.strip()
        if not text:
            continue
        if len(text) > HISTORY_ITEM_MAX_CHARS:
            text = _truncate_with_marker(text, HISTORY_ITEM_MAX_CHARS, HISTORY_ITEM_TRUNCATION_MARKER)
        normalized.append({"role": ROLE_ALIASES[role], "text": text})

    selected: list[dict[str, str]] = []
    total_chars = 0
    for item in reversed(normalized[-HISTORY_CONTEXT_MAX_ITEMS:]):
        remaining = HISTORY_TOTAL_MAX_CHARS - total_chars
        if remaining <= 0:
            break
        text = item["text"]
        if len(text) > remaining:
            text = _truncate_with_marker(text, remaining, HISTORY_TOTAL_TRUNCATION_MARKER)
        selected.append({"role": item["role"], "text": text})
        total_chars += len(text)
    selected.reverse()
    return selected


def _normalize_plan_context(value: Any, source: str) -> dict[str, str]:
    if value is None or source != "uploaded_plan":
        return {}
    if not isinstance(value, dict):
        raise ContextInputError(
            "INVALID_PLAN_CONTEXT",
            "plan_context 必须是对象。",
            field="plan_context",
        )

    subject = value.get("subject", "")
    suggested_date = value.get("suggested_date", "")
    if not isinstance(subject, str) or len(subject.strip()) > 40:
        raise ContextInputError(
            "INVALID_PLAN_SUBJECT",
            "训练科目必须是最多 40 个字符的字符串。",
            field="plan_context.subject",
        )
    if not isinstance(suggested_date, str) or len(suggested_date.strip()) > 10:
        raise ContextInputError(
            "INVALID_PLAN_DATE",
            "建议日期必须是最多 10 个字符的字符串。",
            field="plan_context.suggested_date",
        )
    suggested_date = suggested_date.strip()
    if suggested_date:
        try:
            date.fromisoformat(suggested_date)
        except ValueError as exc:
            raise ContextInputError(
                "INVALID_PLAN_DATE",
                "建议日期格式必须为 YYYY-MM-DD。",
                field="plan_context.suggested_date",
            ) from exc
    return {
        "subject": subject.strip(),
        "suggested_date": suggested_date,
    }


def validate_chat_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContextInputError("INVALID_JSON_OBJECT", "请求正文必须是 JSON 对象。")

    source = payload.get("source", "chat")
    if not isinstance(source, str) or source not in ALLOWED_SOURCES:
        raise ContextInputError(
            "INVALID_SOURCE",
            "source 只允许 chat 或 uploaded_plan。",
            field="source",
        )

    message = payload.get("message")
    if not isinstance(message, str):
        raise ContextInputError("INVALID_MESSAGE", "message 必须是字符串。", field="message")
    message = message.strip()
    if not message:
        raise ContextInputError("EMPTY_MESSAGE", "请输入内容。", field="message")

    message_limit = (
        UPLOADED_PLAN_MESSAGE_MAX_CHARS if source == "uploaded_plan" else CHAT_MESSAGE_MAX_CHARS
    )
    if len(message) > message_limit:
        raise ContextInputError(
            "MESSAGE_TOO_LARGE",
            f"消息不能超过 {message_limit} 个字符。",
            status_code=413,
            field="message",
        )

    from .muscle_recovery import normalise_garmin_hours
    garmin_hours = normalise_garmin_hours(payload.get("garmin_recovery_hours", 0))
    if garmin_hours is None:
        raise ContextInputError(
            "INVALID_GARMIN_RECOVERY_HOURS",
            "Garmin 恢复时间必须是 0–96.0 之间的数字。",
            field="garmin_recovery_hours",
        )

    prompt_regions_raw = payload.get("soreness_prompt_regions", [])
    if not isinstance(prompt_regions_raw, list):
        raise ContextInputError(
            "INVALID_SORENESS_PROMPT_REGIONS",
            "soreness_prompt_regions 必须是数组。",
            field="soreness_prompt_regions",
        )
    from .muscle_recovery import REGION_ALIASES
    allowed_regions = set(REGION_ALIASES)
    prompt_regions = list(dict.fromkeys(
        str(region).strip() for region in prompt_regions_raw
        if str(region).strip() in allowed_regions
    ))

    pending_memory_ids_raw = payload.get("pending_memory_entry_ids", [])
    if not isinstance(pending_memory_ids_raw, list):
        raise ContextInputError(
            "INVALID_PENDING_MEMORY_IDS",
            "pending_memory_entry_ids 必须是数组。",
            field="pending_memory_entry_ids",
        )
    pending_memory_entry_ids = list(dict.fromkeys(
        str(entry_id).strip()[:80]
        for entry_id in pending_memory_ids_raw[:8]
        if isinstance(entry_id, str) and entry_id.strip()
    ))

    return {
        "message": message,
        "history": _normalize_history(payload.get("history", [])),
        "source": source,
        "plan_context": _normalize_plan_context(payload.get("plan_context"), source),
        "garmin_recovery_hours": garmin_hours,
        "soreness_prompt_regions": prompt_regions,
        "pending_memory_entry_ids": pending_memory_entry_ids,
    }


def decode_chat_payload(body: bytes) -> dict[str, Any]:
    if len(body) > CHAT_REQUEST_MAX_BYTES:
        raise ContextInputError(
            "REQUEST_TOO_LARGE",
            "聊天请求不能超过 256 KiB。",
            status_code=413,
        )
    if not body:
        raise ContextInputError("EMPTY_REQUEST", "请求正文不能为空。")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextInputError("INVALID_JSON", "请求正文不是有效的 UTF-8 JSON。") from exc
    return validate_chat_payload(payload)
