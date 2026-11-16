"""Normalize untrusted JSON exports without following links or opening files."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any
from collections import Counter

from pydantic import ValidationError

from app.schemas import StandardMessage

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_MESSAGES = 10000


class ImportValidationError(ValueError):
    """The import is malformed; no partial normalized result is returned."""


class ImportFieldError(ValueError):
    """Application-authored field diagnostics, safe to show without raw input."""


def _timestamp(value: Any, naive_timezone: str | None = None) -> datetime:
    if isinstance(value, bool) or value is None:
        raise ValueError("missing or invalid timestamp")
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        number = float(value)
        # Official create_time is milliseconds; CLI exports may use seconds.
        if abs(number) >= 100_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO 8601 or epoch time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ImportFieldError(
            "create_time/timestamp 时间格式无效，请使用日期时间或秒/毫秒时间戳"
        ) from error
    if parsed.tzinfo is None:
        if naive_timezone is None:
            raise ImportFieldError(
                "create_time/timestamp 时间未包含时区，请在导入时选择原始时间的时区"
            )
        zone = timezone.utc if naive_timezone == "UTC" else timezone(timedelta(hours=8))
        parsed = parsed.replace(tzinfo=zone)
    return parsed


def _post_text(value: Any) -> str:
    """Render only textual post elements, never interpret arbitrary JSON as prose."""
    if isinstance(value, list):
        return "\n".join(filter(None, (_post_text(part) for part in value)))
    if not isinstance(value, dict):
        return ""
    if value.get("tag") in {"text", "a", "at"}:
        return str(value.get("text") or value.get("user_name") or "")
    if "content" in value:
        title = value.get("title", "")
        rows = value["content"]
        lines = []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    lines.append("".join(_post_text(item) for item in row))
                else:
                    lines.append(_post_text(row))
        return "\n".join(filter(None, [str(title), *lines]))
    for language in ("zh_cn", "en_us", "ja_jp"):
        if language in value:
            return _post_text(value[language])
    return ""


def _content_text(record: dict[str, Any]) -> str:
    msg_type = record.get("msg_type", record.get("message_type", "text"))
    if record.get("deleted") is True:
        return "[recalled message]"
    body = record.get("body") or {}
    content = body.get("content") if isinstance(body, dict) else None
    if content is None:
        content = record.get("content", record.get("text"))
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
            # A rendered CLI message such as "123", "null", a quoted string
            # or an array is still literal prose. Only unpack a recognizable
            # text envelope (or validate an official body object).
            if msg_type == "text":
                if not isinstance(decoded, dict) or (
                    "text" not in decoded
                    and not (isinstance(body, dict) and body.get("content") is not None)
                ):
                    decoded = content
            elif not isinstance(decoded, (dict, list)):
                decoded = content
        except json.JSONDecodeError:
            # The CLI returns already-rendered human readable strings.
            decoded = content
    else:
        decoded = content
    if msg_type == "text":
        if isinstance(decoded, dict):
            decoded = decoded.get("text")
        if not isinstance(decoded, str) or not decoded.strip():
            raise ImportFieldError(
                "text 消息缺少有效正文，请检查 content 或 body.content.text 字段"
            )
        return decoded
    if msg_type == "post":
        if isinstance(decoded, str):
            return decoded or "[post]"
        return _post_text(decoded) or "[post without text]"
    # Attachment metadata remains available, but is not mistaken for observed prose.
    return f"[{msg_type} message]"


def normalize_record(
    record: dict[str, Any],
    source_id: str,
    naive_timezone: str | None = None,
    *,
    context: dict[str, Any] | None = None,
    occurrences: Counter | None = None,
) -> StandardMessage:
    """Normalize one standard record or raw OpenAPI/CLI history item."""
    if not isinstance(record, dict):
        raise ValueError("each message must be an object")
    if record.get("source_id", source_id) != source_id:
        raise ValueError("message source_id does not match import source_id")
    from .records import normalize_export_record, record_kind

    kind = record_kind(record, context)
    if kind == "standard":
        return StandardMessage.model_validate({**record, "source_id": source_id})
    if kind == "export":
        return normalize_export_record(record, source_id, naive_timezone, context, occurrences)
    message_id = record.get("message_id")
    if not isinstance(message_id, str) or not message_id.strip():
        raise ValueError("Feishu message_id is required")
    sender = record.get("sender", "unknown")
    if isinstance(sender, dict):
        sender = sender.get("name") or sender.get("sender_name") or sender.get("id") or "unknown"
    if not isinstance(sender, str):
        raise ValueError("sender must be a string or sender object")
    return StandardMessage(
        id=message_id,
        source_id=source_id,
        source_type="feishu",
        chat_id=str(record.get("chat_id", "")),
        sender=sender,
        text=_content_text(record),
        timestamp=_timestamp(record.get("create_time", record.get("timestamp")), naive_timezone),
        thread_id=record.get("thread_id"),
        metadata={"raw": record},
    )


def _records(payload: Any) -> list[Any]:
    from .formats import unwrap_records

    return [record for record, _ in unwrap_records(payload)]


def parse_messages(
    content: str, source_id: str, format: str = "json", naive_timezone: str | None = None
) -> list[StandardMessage]:
    """All-or-nothing import; neither executes content nor makes network requests."""
    from .preview import preview_messages

    preview = preview_messages(content, source_id, format, naive_timezone)
    if preview.issues:
        issue = preview.issues[0]
        location = (
            f" at line {issue.line}" if issue.line is not None else f" at position {issue.position}"
        )
        raise ImportValidationError(f"invalid message{location}: {issue.field} {issue.detail}")
    return preview.messages
