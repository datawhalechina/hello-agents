"""Decode recognized chat-export containers without executing scripts or links."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import hashlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

SUPPORTED_FORMATS = {"auto", "json", "jsonl", "csv", "txt", "html"}
MAX_RECORDS = 10000
TIME_KEYS = (
    "timestamp",
    "time",
    "create_time",
    "CreateTime",
    "MsgTime",
    "datetime",
    "dateTime",
    "sendTime",
    "时间",
    "发送时间",
    "日期时间",
    "消息时间",
)
CONTENT_KEYS = ("text", "content", "StrContent", "message", "正文", "消息内容", "内容")
ID_KEYS = (
    "id",
    "message_id",
    "platformMessageId",
    "msgId",
    "messageId",
    "msgSvrId",
    "MsgSvrID",
    "localId",
    "消息ID",
    "消息编号",
)
SENDER_KEYS = (
    "sender",
    "from",
    "sender_id",
    "senderId",
    "NickName",
    "nickname",
    "accountName",
    "发送人",
    "发送者",
    "昵称",
)
CHAT_KEYS = (
    "chat_id",
    "chat",
    "StrTalker",
    "talker",
    "group_id",
    "groupId",
    "conversation_id",
    "conversationId",
    "会话",
    "群号",
    "群聊",
)
RECORD_KEYS = set(TIME_KEYS + CONTENT_KEYS + ID_KEYS + SENDER_KEYS + CHAT_KEYS)


@dataclass
class Entry:
    position: int
    line: int | None
    raw: Any
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ExportDocument:
    format: str
    entries: list[Entry] = field(default_factory=list)
    error: str | None = None
    raw: Any = None
    warnings: list[str] = field(default_factory=list)


def _append(document: ExportDocument, entry: Entry) -> None:
    if len(document.entries) >= MAX_RECORDS:
        from .local import ImportValidationError

        raise ImportValidationError("导入记录超过10000条限制。")
    document.entries.append(entry)


def load_json(content: str) -> Any:
    def nonfinite(_):
        raise ValueError("Non-finite JSON number")

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Out-of-range JSON number")
        return result

    result = json.loads(content, parse_constant=nonfinite, parse_float=number)
    pending = [result]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            item.encode("utf-8")
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return result


CONTEXT_KEYS = ("chatlab", "meta", "members", "conversation", "preamble", "platform")


def prepare_contexts(document: ExportDocument) -> dict[str, dict[str, Any]]:
    """Keep full root metadata once; message metadata carries its hash reference."""
    contexts = {}
    prepared = {}
    for entry in document.entries:
        context = entry.context
        key = tuple((name, id(context[name])) for name in CONTEXT_KEYS if name in context)
        if not key:
            continue
        if key not in prepared:
            payload = {name: context[name] for name in CONTEXT_KEYS if name in context}
            digest = hashlib.sha256(
                json.dumps(
                    payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode()
            ).hexdigest()
            member_index = {}
            for member in (
                payload.get("members", []) if isinstance(payload.get("members", []), list) else []
            ):
                if isinstance(member, dict):
                    identity = member.get("platformId", member.get("id"))
                    if isinstance(identity, (str, int)) and not isinstance(identity, bool):
                        member_index.setdefault(str(identity), []).append(member)
            prepared[key] = (digest, member_index)
            contexts[digest] = payload
        context["_source_context_hash"], context["_member_index"] = prepared[key]
    return contexts


def source_contexts(content: str, format: str = "auto") -> dict[str, dict[str, Any]]:
    """Return full file-level context for atomic source-context persistence by Main."""
    return prepare_contexts(read_export(content, format))


def _context(payload: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    result = dict(prior)
    for key in ("chatlab", "meta", "members", "conversation", "platform"):
        if key in payload:
            result[key] = payload[key]
    if "chatlab" in payload:
        result["export_kind"] = "chatlab"
    meta = result.get("meta")
    if isinstance(meta, dict) and "platform" in meta:
        result["platform"] = meta["platform"]
    if "chat" in payload and isinstance(payload["chat"], (dict, str)):
        result["conversation"] = payload["chat"]
    if "session" in payload and isinstance(payload["session"], (dict, str)):
        result["conversation"] = payload["session"]
    conversation = result.get("conversation")
    if isinstance(conversation, dict):
        if "platform" in conversation and "platform" not in payload:
            result["platform"] = conversation["platform"]
        if "members" in conversation:
            result["members"] = conversation["members"]
    if (
        any(
            key in payload
            for key in ("messages", "items", "records", "chat_history", "chatHistory")
        )
        and "conversation" in result
    ):
        result.setdefault("export_kind", "conversation")
        result["namespace_native_id"] = True
    return result


def unwrap_records(
    payload: Any, context: dict[str, Any] | None = None
) -> list[tuple[Any, dict[str, Any]]]:
    context = dict(context or {})
    if isinstance(payload, list):
        result = []
        for record in payload:
            if isinstance(record, dict) and "chatlab" in record and "messages" in record:
                result.extend(unwrap_records(record, context))
            else:
                result.append((record, context))
        return result
    if not isinstance(payload, dict):
        raise ValueError("unknown_envelope")
    if payload.get("ok") is False or ("code" in payload and payload["code"] != 0):
        raise ValueError("unsuccessful_export")
    context = _context(payload, context)
    for key in ("chats", "conversations", "sessions"):
        if key not in payload:
            continue
        conversations = payload[key]
        if not isinstance(conversations, list):
            raise ValueError("unknown_envelope")
        result = []
        message_containers = {"messages", "items", "records", "chat_history", "chatHistory"}
        for conversation in conversations:
            if not isinstance(conversation, dict) or not message_containers.intersection(
                conversation
            ):
                raise ValueError("unknown_envelope")
            inherited = dict(context)
            inherited["conversation"] = {
                name: value
                for name, value in conversation.items()
                if name not in message_containers
            }
            inherited["export_kind"] = "conversation"
            inherited["namespace_native_id"] = True
            result.extend(unwrap_records(conversation, inherited))
        return result
    if "data" in payload:
        return unwrap_records(payload["data"], context)
    for key in ("messages", "items", "records", "chat_history", "chatHistory"):
        if key in payload:
            if not isinstance(payload[key], list):
                raise ValueError("unknown_envelope")
            return [(record, context) for record in payload[key]]
    if RECORD_KEYS.intersection(payload):
        return [(payload, context)]
    raise ValueError("unknown_envelope")


def _looks_like_jsonl(content: str) -> bool:
    lines = [line for line in content.splitlines() if line.strip()]
    if len(lines) < 2 or lines[0].rstrip().endswith(("{", "[")):
        return False
    if lines[0].lstrip().startswith("["):
        try:
            load_json(lines[0])
        except (ValueError, RecursionError):
            return False
    for line in lines:
        try:
            if isinstance(load_json(line), dict):
                return True
        except (ValueError, RecursionError):
            continue
    return False


def _json_document(content: str, requested: str) -> ExportDocument:
    try:
        payload = load_json(content)
    except (ValueError, RecursionError):
        payload = None
    else:
        try:
            records = unwrap_records(payload)
        except ValueError as error:
            return ExportDocument("json", error=str(error), raw=payload)
        compact = (
            requested == "jsonl"
            and isinstance(payload, dict)
            and len(records) == 1
            and records[0][0] is payload
            and len([line for line in content.splitlines() if line.strip()]) == 1
        )
        line = (
            next(
                (number for number, value in enumerate(content.splitlines(), 1) if value.strip()),
                None,
            )
            if compact
            else None
        )
        return ExportDocument(
            "jsonl" if compact else "json",
            [
                Entry(index, line, record, {**context, "format": "jsonl" if compact else "json"})
                for index, (record, context) in enumerate(records, 1)
            ],
            raw=payload,
        )
    if requested != "jsonl" and not _looks_like_jsonl(content):
        return ExportDocument("json", error="json_syntax", raw=content)
    result = ExportDocument("jsonl", raw=content)
    context: dict[str, Any] = {"format": "jsonl"}
    members: list[dict[str, Any]] = []
    lines = [(number, line) for number, line in enumerate(content.splitlines(), 1) if line.strip()]
    for number, line in lines:
        if context.get("export_kind") == "chatlab" and line.lstrip().startswith("#"):
            continue
        try:
            record = load_json(line)
        except (ValueError, RecursionError):
            _append(
                result, Entry(len(result.entries) + 1, number, line, dict(context), "json_syntax")
            )
            continue
        if isinstance(record, dict) and record.get("_type") == "header":
            if (
                result.entries
                or "chatlab" not in record
                or not isinstance(record.get("meta"), dict)
            ):
                _append(
                    result,
                    Entry(len(result.entries) + 1, number, record, dict(context), "invalid_record"),
                )
                continue
            context = {**_context(record, context), "format": "jsonl", "members": members}
            continue
        if (
            isinstance(record, dict)
            and record.get("_type") == "member"
            and context.get("export_kind") == "chatlab"
        ):
            members.append(record)
            continue
        if (
            isinstance(record, dict)
            and record.get("_type") in {"member", "message"}
            and context.get("export_kind") != "chatlab"
        ):
            _append(
                result,
                Entry(len(result.entries) + 1, number, record, dict(context), "invalid_record"),
            )
            continue
        _append(result, Entry(len(result.entries) + 1, number, record, dict(context)))
    return result


def _csv_document(content: str) -> ExportDocument:
    result = ExportDocument("csv", raw=content)
    try:
        dialect = csv.Sniffer().sniff(content[:8192], delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in content.partition("\n")[0] else csv.excel
    reader = csv.DictReader(io.StringIO(content, newline=""), dialect=dialect, strict=True)
    try:
        header = reader.fieldnames
        if (
            not header
            or len(set(header)) != len(header)
            or not set(header).intersection(TIME_KEYS)
            or not set(header).intersection(CONTENT_KEYS)
        ):
            return ExportDocument("csv", error="unknown_format", raw=content)
        while True:
            start_line = reader.line_num + 1
            try:
                record = next(reader)
            except StopIteration:
                break
            error = "invalid_record" if None in record else None
            _append(
                result,
                Entry(
                    len(result.entries) + 1,
                    start_line,
                    record,
                    {"format": "csv", "export_kind": "table"},
                    error,
                ),
            )
    except csv.Error:
        _append(
            result,
            Entry(
                len(result.entries) + 1, reader.line_num, content, {"format": "csv"}, "csv_syntax"
            ),
        )
    return result


_DATE = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
_TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?"
_STAMP = rf"{_DATE}[ T]{_TIME}(?:Z|[+-]\d{{2}}:\d{{2}})?"
_TXT_DATE_FIRST = re.compile(
    rf"^\[?(?P<time>{_STAMP})\]?\s+(?P<sender>.+?)(?:[：:]\s*(?P<body>.*))?$"
)
_TXT_SENDER_FIRST = re.compile(rf"^(?P<sender>.+?)\s+(?P<time>{_STAMP})\s*$")
_TXT_QQ_ID = re.compile(r"^(?P<name>.*?)\s*[（(](?P<id>\d{5,20})[）)]$")


def _txt_document(content: str) -> ExportDocument:
    result = ExportDocument("txt", raw=content)
    current: dict[str, Any] | None = None
    start_line: int | None = None
    original: list[str] = []
    body_lines: list[str] = []
    preamble: list[str] = []

    def finish():
        if current is not None:
            current["content"] = "\n".join(body_lines).rstrip("\n")
            current["_raw_text"] = "\n".join(original)
            platform = current.pop("_platform", "chat")
            _append(
                result,
                Entry(
                    len(result.entries) + 1,
                    start_line,
                    dict(current),
                    {"format": "txt", "export_kind": "transcript", "platform": platform},
                ),
            )

    for number, line in enumerate(content.splitlines(), 1):
        match = _TXT_DATE_FIRST.match(line) or _TXT_SENDER_FIRST.match(line)
        if match:
            finish()
            groups = match.groupdict()
            sender = groups["sender"].strip()
            qq = _TXT_QQ_ID.match(sender)
            current = {
                "time": groups["time"],
                "sender": {"name": qq["name"], "id": qq["id"]} if qq else sender,
                "_platform": "qq" if qq else "chat",
            }
            start_line = number
            original = [line]
            body_lines = [groups["body"]] if groups.get("body") is not None else []
        elif current is not None:
            original.append(line)
            body_lines.append(line)
        elif line.strip():
            preamble.append(line)
    finish()
    if not result.entries:
        result.error = "unknown_format"
    elif preamble:
        # Common QQ exporter headings contain no messages. Preserve them as context.
        for entry in result.entries:
            entry.context["preamble"] = "\n".join(preamble)
    return result


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[Any] = field(default_factory=list)
    raw: str = ""
    line: int = 1
    offset: int = 0
    end_offset: int = 0

    def text(self, include_scripts: bool = False) -> str:
        if self.tag in {"script", "style"} and not include_scripts:
            return ""
        return "".join(
            item.text(include_scripts) if isinstance(item, _Element) else item
            for item in self.children
        )


class _ExportHTML(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.root = _Element("root", {})
        self.stack = [self.root]
        self.source = source
        self.line_offsets = [0]
        self.line_offsets.extend(match.end() for match in re.finditer("\n", source))

    def _offset(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if len(self.stack) > 200:
            raise ValueError("HTML nesting exceeds supported depth")
        item = _Element(tag, dict(attrs), line=self.getpos()[0], offset=self._offset())
        self.stack[-1].children.append(item)
        if tag == "br":
            item.children.append("\n")
        if tag not in {"br", "img", "hr", "meta", "link", "input", "source", "wbr"}:
            self.stack.append(item)
        else:
            item.end_offset = item.offset + len(self.get_starttag_text())

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                end = self.source.find(">", self._offset())
                self.stack[index].end_offset = end + 1
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _elements(root: _Element):
    for child in root.children:
        if isinstance(child, _Element):
            yield child
            yield from _elements(child)


def _html_document(content: str) -> ExportDocument:
    parser = _ExportHTML(content)
    try:
        parser.feed(content)
    except (ValueError, RecursionError):
        return ExportDocument("html", error="invalid_html", raw=content)
    result = ExportDocument("html", raw=content)
    elements = list(_elements(parser.root))
    for item in elements:
        if item.tag == "script" and item.attrs.get("type", "").lower() == "application/json":
            try:
                records = unwrap_records(load_json(item.text(include_scripts=True)))
            except (ValueError, RecursionError):
                _append(
                    result,
                    Entry(
                        len(result.entries) + 1,
                        item.line,
                        item.text(include_scripts=True),
                        {"format": "html"},
                        "json_syntax",
                    ),
                )
                continue
            for record, context in records:
                _append(
                    result,
                    Entry(
                        len(result.entries) + 1,
                        item.line,
                        record,
                        {
                            **context,
                            "format": "html",
                            "export_kind": context.get("export_kind", "embedded-json"),
                        },
                    ),
                )
    if result.entries:
        return result
    for table in (item for item in elements if item.tag == "table"):
        rows = [item for item in _elements(table) if item.tag == "tr"]
        if not rows:
            continue
        header = [
            item.text().strip()
            for item in rows[0].children
            if isinstance(item, _Element) and item.tag in {"th", "td"}
        ]
        if (
            not set(header).intersection(TIME_KEYS)
            or not set(header).intersection(CONTENT_KEYS)
            or len(header) != len(set(header))
        ):
            continue
        for row in rows[1:]:
            cells = [
                item.text()
                for item in row.children
                if isinstance(item, _Element) and item.tag in {"th", "td"}
            ]
            raw = dict(zip(header, cells))
            _append(
                result,
                Entry(
                    len(result.entries) + 1,
                    row.line,
                    raw,
                    {
                        "format": "html",
                        "export_kind": "table",
                        "source_html": content[row.offset : row.end_offset],
                    },
                    "invalid_record" if len(cells) != len(header) else None,
                ),
            )
    if result.entries:
        return result
    classes = {"message", "msg", "chat-message", "message-item", "chat-item"}
    for item in elements:
        if not (
            classes.intersection(item.attrs.get("class", "").split())
            or "data-message-id" in item.attrs
        ):
            continue
        record = {}
        for destination, aliases in {
            "id": ("data-message-id", "data-id"),
            "time": ("data-time", "data-timestamp"),
            "sender": ("data-sender", "data-name"),
            "content": ("data-content",),
        }.items():
            for alias in aliases:
                if alias in item.attrs:
                    record[destination] = item.attrs[alias]
                    break
        for child in _elements(item):
            child_classes = set(child.attrs.get("class", "").split())
            for destination, choices in {
                "time": {"time", "timestamp", "datetime"},
                "sender": {"sender", "sender-name", "nickname"},
                "content": {"content", "text", "msg-content", "message-content"},
            }.items():
                if destination not in record and child_classes.intersection(choices):
                    record[destination] = child.text()
        if not record:
            continue
        if item.attrs.get("data-chat-id") is not None:
            record["chat"] = item.attrs["data-chat-id"]
        _append(
            result,
            Entry(
                len(result.entries) + 1,
                item.line,
                record,
                {
                    "format": "html",
                    "export_kind": "static-html",
                    "source_html": content[item.offset : item.end_offset],
                },
            ),
        )
    if not result.entries:
        result.error = "unknown_format"
    return result


def read_export(content: str, requested: str) -> ExportDocument:
    clean = content.lstrip("\ufeff")
    if not clean.strip():
        return ExportDocument(
            "json" if requested == "auto" else requested, error="empty", raw=content
        )
    if requested in {"json", "jsonl"}:
        return _json_document(clean, requested)
    if requested == "csv":
        return _csv_document(clean)
    if requested == "txt":
        return _txt_document(clean)
    if requested == "html":
        return _html_document(clean)
    start = clean.lstrip()
    if start.startswith(("{", "[")) or _looks_like_jsonl(clean):
        return _json_document(clean, "auto")
    if re.match(r"(?is)<(?:!doctype\s+html|html|head|body|table|div|script)\b", start):
        return _html_document(clean)
    first = start.partition("\n")[0]
    if any(delimiter in first for delimiter in (",", "\t", ";")):
        table = _csv_document(clean)
        if table.error != "unknown_format":
            return table
    return _txt_document(clean)
