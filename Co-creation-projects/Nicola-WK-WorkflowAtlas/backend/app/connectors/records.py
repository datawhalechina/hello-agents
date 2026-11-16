"""Field adapters for recognized structured chat exports."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from app.schemas import StandardMessage
from .formats import CHAT_KEYS, CONTENT_KEYS, ID_KEYS, SENDER_KEYS, TIME_KEYS

STANDARD_KEYS = {
    "id",
    "source_id",
    "source_type",
    "chat_id",
    "sender",
    "text",
    "timestamp",
    "thread_id",
    "metadata",
}
PLATFORMS = {
    "wechat": "wechat",
    "weixin": "wechat",
    "wx": "wechat",
    "微信": "wechat",
    "qq": "qq",
    "tencentqq": "qq",
    "飞书": "feishu",
    "feishu": "feishu",
    "lark": "feishu",
}


class RecordProblems(ValueError):
    def __init__(self, problems: list[tuple[str, str]]):
        super().__init__("invalid export record")
        self.problems = list(dict.fromkeys(problems))


def record_kind(record: Any, context: dict[str, Any] | None = None) -> str:
    if not isinstance(record, dict):
        return "invalid"
    if context and context.get("export_kind"):
        return "export"
    native_aliases = set(TIME_KEYS + CONTENT_KEYS + CHAT_KEYS + ID_KEYS) - STANDARD_KEYS
    explicit_standard = "source_type" in record or (
        "source_id" in record and not native_aliases.intersection(record)
    )
    canonical = {"id", "text", "timestamp"}.issubset(record)
    if explicit_standard or (canonical and not native_aliases.intersection(record)):
        return "standard"
    if _is_segment_export(record):
        return "export"
    if {"StrContent", "StrTalker", "MsgSvrID", "msgSvrId", "IsSender"}.intersection(record):
        return "export"
    if PLATFORMS.get(str(record.get("platform", (context or {}).get("platform", ""))).lower()) in {
        "wechat",
        "qq",
    }:
        return "export"
    if set(record).issubset(STANDARD_KEYS) and {"id", "text", "timestamp"}.intersection(record):
        return "standard"
    # Preserve the established Feishu normalization branch exactly.
    if {"msg_type", "message_type", "body"}.intersection(record):
        return "feishu"
    if "message_id" in record and not {
        "group_id",
        "groupId",
        "MsgTime",
        "message",
        "platform",
    }.intersection(record):
        return "feishu"
    if "create_time" in record and not {
        "id",
        "msgId",
        "MsgSvrID",
        "StrContent",
        "platformMessageId",
    }.intersection(record):
        return "feishu"
    if "source_id" in record and {"id", "text", "timestamp"}.intersection(record):
        return "standard"
    return "export"


def _scalar(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (str, int)):
        return str(value)
    return None


def _is_segment_export(record: dict[str, Any]) -> bool:
    actor = record.get("self")
    conversation_type = record.get("message_type")
    string_event = (
        isinstance(conversation_type, str)
        and conversation_type in {"group", "private"}
        and "message_id" in record
        and isinstance(record.get("message"), str)
    )
    return (
        isinstance(record.get("message"), list)
        or (isinstance(actor, dict) and actor.get("platform") == "qq")
        or ("raw_message" in record and "message_id" in record)
        or string_event
    )


def _present(record: dict[str, Any], keys) -> list[tuple[str, Any]]:
    return [
        (key, record[key])
        for key in keys
        if key in record and record[key] is not None and record[key] != ""
    ]


def _one(record, keys, field, problems, *, optional=False):
    values = _present(record, keys)
    if not values:
        if not optional:
            problems.append(
                (
                    field,
                    "missing_"
                    + {"timestamp": "timestamp", "content": "content", "id": "id"}.get(
                        field, field
                    ),
                )
            )
        return None, None
    comparable = [json.dumps(value, sort_keys=True, ensure_ascii=False) for _, value in values]
    if len(set(comparable)) > 1:
        problems.append((field, "ambiguous_fields"))
    return values[0]


def _platform(record: dict[str, Any], context: dict[str, Any]) -> str:
    value = record.get("platform", context.get("platform"))
    if isinstance(value, str):
        return PLATFORMS.get(value.lower().strip(), "chat")
    if _is_segment_export(record):
        return "qq"
    if {"StrContent", "StrTalker", "MsgSvrID", "msgSvrId", "IsSender"}.intersection(record):
        return "wechat"
    if {"group_id", "groupId", "qq", "uin"}.intersection(record):
        return "qq"
    native = record.get("id")
    if isinstance(native, str) and native.startswith("om_"):
        return "feishu"
    return "chat"


def _conversation(record: dict[str, Any], context: dict[str, Any], problems) -> str:
    values = _present(record, CHAT_KEYS)
    normalized = []
    for key, value in values:
        if isinstance(value, dict):
            value = value.get("id", value.get("chat_id", value.get("groupId", value.get("name"))))
        text = _scalar(value)
        if text is None:
            problems.append((key, "invalid_type"))
        else:
            normalized.append(text)
    if len(set(normalized)) > 1:
        problems.append(("chat_id", "ambiguous_fields"))
    if normalized:
        return normalized[0]
    if _is_segment_export(record) and "user_id" in record:
        identity = _scalar(record["user_id"])
        if identity is not None:
            return identity
    for value in (context.get("conversation"), context.get("meta")):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("id", "chat_id", "groupId", "group_id", "conversationId", "name"):
                candidate = _scalar(value.get(key))
                if candidate is not None and candidate.strip():
                    return candidate
    return ""


def _sender(record: dict[str, Any], context: dict[str, Any], problems) -> tuple[str, str | None]:
    value = next(
        (record[key] for key in ("sender", "from", "sender_id", "senderId") if key in record), None
    )
    if value is None and _is_segment_export(record):
        value = record.get("user_id")
    sender_id = None
    observed_name = None
    if isinstance(value, dict):
        sender_id = next(
            (
                _scalar(value[key])
                for key in ("id", "platformId", "user_id", "uin", "wxid")
                if key in value
            ),
            None,
        )
        observed_name = next(
            (
                _scalar(value[key])
                for key in (
                    "name",
                    "sender_name",
                    "nickname",
                    "NickName",
                    "displayName",
                    "accountName",
                )
                if key in value
            ),
            None,
        )
        if sender_id is None and observed_name is None:
            problems.append(("sender", "invalid_sender"))
    elif value is not None:
        sender_id = _scalar(value)
        if sender_id is None:
            problems.append(("sender", "invalid_sender"))
        observed_name = sender_id
    for key in (
        "groupNickname",
        "NickName",
        "nickname",
        "accountName",
        "displayName",
        "发送人",
        "发送者",
        "昵称",
    ):
        if key in record and record[key] not in (None, ""):
            text = _scalar(record[key])
            if text is None:
                problems.append((key, "invalid_sender"))
            else:
                observed_name = text
                break
    index = context.get("_member_index")
    members = index.get(sender_id, []) if isinstance(index, dict) else context.get("members")
    if isinstance(members, list) and sender_id is not None and observed_name in {None, sender_id}:
        names = set()
        for member in members:
            if (
                not isinstance(member, dict)
                or _scalar(member.get("platformId", member.get("id"))) != sender_id
            ):
                continue
            name = next(
                (
                    _scalar(member[key])
                    for key in ("groupNickname", "accountName", "name", "nickname")
                    if key in member
                ),
                None,
            )
            if name is not None:
                names.add(name)
        if len(names) == 1:
            observed_name = next(iter(names))
        elif len(names) > 1:
            problems.append(("sender", "ambiguous_fields"))
    return observed_name if observed_name is not None else "unknown", sender_id


def _namespace(
    native: str, platform: str, chat: str, field: str | None, force: bool = False
) -> str:
    if chat and (force or platform in {"wechat", "qq"} or field in {"localId", "msgId"}):
        value = f"{platform}:{chat}:{native}"
        if len(value) > 300:
            value = f"{platform}:conversation:{hashlib.sha256(chat.encode()).hexdigest()}:{hashlib.sha256(native.encode()).hexdigest()}"
        return value
    return native


def _conversation_scope(
    record: dict[str, Any], context: dict[str, Any], platform: str, chat: str
) -> str:
    if platform != "qq":
        return chat
    actor = record.get("self")
    account = _scalar(record.get("self_id"))
    if account is None and isinstance(actor, dict):
        account = _scalar(actor.get("user_id"))
    meta = context.get("meta")
    kind = record.get("detail_type", record.get("message_type"))
    if kind not in {"group", "private"}:
        kind = meta.get("type") if isinstance(meta, dict) else None
    if kind not in {"group", "private"} and {"group_id", "groupId"}.intersection(record):
        kind = "group"
    parts = [
        value
        for value in (kind if kind in {"group", "private"} else None, account, chat)
        if value is not None and value != ""
    ]
    return ":".join(parts)


def _message_kind(value: Any, platform: str, export_kind: str | None) -> str:
    if isinstance(value, str) and not value.isdigit():
        kind = value.lower()
        return {
            "voice": "audio",
            "record": "audio",
            "interactive": "link",
            "card": "link",
            "xml": "link",
            "json": "link",
            "sticker": "image",
            "face": "image",
            "recall": "system",
            "recalled": "system",
        }.get(
            kind,
            (
                kind
                if kind in {"text", "post", "image", "audio", "video", "file", "link", "system"}
                else "other"
            ),
        )
    mapping = {
        0: "text",
        1: "image",
        2: "audio",
        3: "video",
        4: "file",
        5: "image",
        7: "link",
        25: "text",
        80: "system",
        81: "system",
    }
    if export_kind != "chatlab" and platform == "wechat":
        mapping = {
            1: "text",
            3: "image",
            34: "audio",
            43: "video",
            47: "image",
            49: "link",
            10000: "system",
            10002: "system",
        }
    return mapping.get(int(value), "other")


def _member_summaries(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bound display metadata; complete member records live in source context."""
    summaries = []
    for member in members[:10]:
        summary = {}
        for key in ("platformId", "id", "accountName", "groupNickname", "name"):
            if key in member and isinstance(member[key], (str, int)):
                summary[key] = str(member[key])[:1000]
        aliases = member.get("aliases")
        if isinstance(aliases, list):
            summary["aliases"] = [value[:256] for value in aliases[:10] if isinstance(value, str)]
        if summary not in summaries:
            summaries.append(summary)
    return summaries


def _segments_text(segments: list[Any], problems) -> tuple[str, str, str | None]:
    parts = []
    kinds = set()
    replies = []
    if not segments:
        problems.append(("message", "missing_content"))
    for segment in segments:
        if (
            not isinstance(segment, dict)
            or not isinstance(segment.get("type"), str)
            or not isinstance(segment.get("data"), dict)
        ):
            problems.append(("message", "invalid_content"))
            continue
        kind, data = segment["type"], segment["data"]
        kinds.add(kind)
        if kind == "text":
            if not isinstance(data.get("text"), str):
                problems.append(("message", "invalid_content"))
            else:
                parts.append(data["text"])
        elif kind == "reply":
            reply = _scalar(data.get("id", data.get("message_id")))
            if reply is None:
                problems.append(("message", "invalid_content"))
            else:
                replies.append(reply)
        else:
            parts.append(f"[{kind} message]")
    if len(set(replies)) > 1:
        problems.append(("message", "ambiguous_fields"))
    if not parts and replies:
        parts.append("[reply message]")
    media_kinds = kinds - {"reply"}
    if media_kinds <= {"text"}:
        message_kind = "text"
    elif "text" in media_kinds:
        message_kind = "post"
    elif len(media_kinds) == 1:
        message_kind = _message_kind(next(iter(media_kinds)), "qq", "onebot")
    else:
        message_kind = "other"
    return "".join(parts), message_kind, replies[0] if replies else None


def normalize_export_record(
    record: dict[str, Any],
    source_id: str,
    naive_timezone: str | None,
    context: dict[str, Any] | None = None,
    occurrences: Counter | None = None,
) -> StandardMessage:
    from .local import _timestamp

    context = dict(context or {})
    problems = []
    if record.get("source_id", source_id) != source_id:
        problems.append(("source_id", "source_mismatch"))
    platform = _platform(record, context)
    segmented = _is_segment_export(record)
    chat = _conversation(record, context, problems)
    scope = _conversation_scope(record, context, platform, chat)
    sender, sender_id = _sender(record, context, problems)
    stamps = _present(record, TIME_KEYS)
    stamp = None
    if not stamps:
        problems.append(("timestamp", "missing_timestamp"))
    times = []
    for key, value in stamps:
        try:
            normalized_value = value.replace("/", "-") if isinstance(value, str) else value
            current = _timestamp(normalized_value, naive_timezone)
            times.append(current)
            if stamp is None:
                stamp = current
        except (ValueError, TypeError, OverflowError, OSError):
            problems.append((key, "invalid_timestamp"))
    if len({value.timestamp() for value in times}) > 1:
        problems.append(("timestamp", "ambiguous_fields"))
    content_field, text = _one(record, CONTENT_KEYS, "content", problems, optional=True)
    if content_field is None and segmented and "raw_message" in record:
        content_field, text = "raw_message", record["raw_message"]
    type_field = next(
        (key for key in ("msg_type", "message_type", "type", "Type", "MsgType") if key in record),
        None,
    )
    message_type = record[type_field] if type_field else "text"
    if segmented:
        message_type = "segments" if isinstance(record.get("message"), list) else "text"
    if isinstance(message_type, bool) or not isinstance(message_type, (str, int)):
        problems.append((type_field or "type", "invalid_type"))
    segment_kind, segment_reply = None, None
    if segmented and isinstance(text, list):
        text, segment_kind, segment_reply = _segments_text(text, problems)
    text_types = (
        {0, "0", "text", "TEXT"}
        if context.get("export_kind") == "chatlab"
        else {0, 1, "0", "1", "text", "TEXT"}
    )
    if text is None or text == "":
        if message_type not in text_types:
            text = f"[{message_type} message]"
        else:
            problems.append((content_field or "content", "missing_content"))
    elif not isinstance(text, str):
        problems.append((content_field or "content", "invalid_content"))
    # A server ID and a local row ID are distinct documented identities.
    server_keys = tuple(key for key in ID_KEYS if key != "localId")
    if segmented and "message_id" in record:
        # OneBot v12 event.id identifies the event, independently of message_id.
        server_keys = tuple(key for key in server_keys if key != "id")
    id_field, native = _one(record, server_keys, "id", problems, optional=True)
    if native is None and "localId" in record:
        id_field, native = "localId", record["localId"]
    if native is not None:
        native_text = _scalar(native)
        if (
            native_text is None
            or not native_text.strip()
            or (len(native_text) > 300 and not (chat and platform in {"wechat", "qq"}))
        ):
            problems.append((id_field or "id", "invalid_id"))
        native = native_text
    recognized = bool(context.get("export_kind")) or bool(
        stamps and content_field and (set(SENDER_KEYS + CHAT_KEYS + ID_KEYS).intersection(record))
    )
    if native is None and not recognized:
        problems.append(("id", "missing_id"))
    if problems:
        raise RecordProblems(problems)
    identity_kind = "native"
    identity: dict[str, Any] = {}
    if native is None:
        canonical = json.dumps(
            {"source_id": source_id, "platform": platform, "conversation": chat, "record": record},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        occurrences = occurrences if occurrences is not None else Counter()
        occurrences[digest] += 1
        native = f"localimport:{digest}:{occurrences[digest]}"
        identity_kind = "derived"
        identity = {
            "kind": "derived",
            "hash": "sha256",
            "digest": digest,
            "occurrence": occurrences[digest],
            "basis": ["source_id", "platform", "conversation", "raw_record"],
        }
        message_id = native
    else:
        message_id = _namespace(
            native, platform, scope, id_field, bool(context.get("namespace_native_id"))
        )
    reply_field = next(
        (
            key
            for key in (
                "replyToMessageId",
                "replyTo",
                "reply_to",
                "reply_to_message_id",
                "parent_id",
                "replyId",
            )
            if key in record
        ),
        None,
    )
    reply = record[reply_field] if reply_field else None
    if reply is None and segment_reply is not None:
        reply = segment_reply
    if isinstance(reply, dict):
        reply = next(
            (
                reply[key]
                for key in ("platformMessageId", "message_id", "id", "msgId")
                if key in reply
            ),
            None,
        )
    reply_id = _scalar(reply)
    thread_id = (
        _namespace(reply_id, platform, scope, id_field, bool(context.get("namespace_native_id")))
        if reply_id is not None
        else None
    )
    metadata: dict[str, Any] = {
        "raw": record,
        "import": {
            "platform": platform,
            "format": context.get("format", "json"),
            "conversation_id": chat,
            "conversation_scope": scope,
            "message_type": message_type,
            "message_kind": segment_kind
            or _message_kind(message_type, platform, context.get("export_kind")),
            "identity_kind": identity_kind,
            "native_id": native if identity_kind == "native" else None,
            "id_field": id_field,
            "source_fields": {"timestamp": [key for key, _ in stamps], "content": content_field},
            "sender_id": sender_id,
        },
    }
    if identity:
        metadata["identity"] = identity
    if context.get("_source_context_hash"):
        metadata["import"]["source_context_hash"] = context["_source_context_hash"]
    if context.get("source_html"):
        metadata["import"]["source_html"] = context["source_html"]
    member_index = context.get("_member_index", {})
    if sender_id in member_index:
        metadata["import"]["sender_members"] = _member_summaries(member_index[sender_id])
    if reply_id is not None:
        metadata["import"]["reply_to_native_id"] = reply_id
        metadata["import"]["reply_to_message_id"] = thread_id
    return StandardMessage(
        id=message_id,
        source_id=source_id,
        source_type=platform,
        chat_id=chat,
        sender=sender,
        text=text,
        timestamp=stamp,
        thread_id=thread_id,
        metadata=metadata,
    )
