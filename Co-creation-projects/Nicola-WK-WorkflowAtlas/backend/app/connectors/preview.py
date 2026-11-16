"""Read-only import preflight: all record diagnostics, no inferred repairs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from ..schemas import ImportIssue, ImportPreview, StandardMessage
from .local import (
    MAX_IMPORT_BYTES,
    MAX_MESSAGES,
    ImportValidationError,
    _content_text,
    _timestamp,
    normalize_record,
)
from .formats import SUPPORTED_FORMATS, read_export, prepare_contexts
from .records import RecordProblems, normalize_export_record, record_kind

_FIELDS = {
    "id",
    "message_id",
    "source_id",
    "source_type",
    "sender",
    "timestamp",
    "create_time",
    "text",
    "content",
    "body",
    "chat_id",
    "thread_id",
    "metadata",
    "msg_type",
    "message_type",
}
_DIAGNOSTICS = {
    "missing_id": "缺少消息 ID，请填写原始消息的 id 或 message_id。",
    "invalid_id": "消息 ID 必须为非空文本，且不能超过300字符。",
    "missing_timestamp": "缺少消息时间，请填写原始 timestamp 或 create_time。",
    "invalid_timestamp": "消息时间无效、超出支持范围或缺少时区，请使用有效日期时间并明确选择时区，或使用秒/毫秒时间戳。",
    "timezone_required": "标准消息时间必须明确包含时区，不能自动补填。",
    "missing_content": "缺少有效消息正文，请检查 text、content 或 body.content.text。",
    "invalid_content": "消息正文类型或内容无效，请保留有效的原始文本。",
    "source_mismatch": "记录的 source_id 与本次选择的来源不一致。",
    "invalid_sender": "发送人必须为文本或包含姓名、标识的发送人对象。",
    "invalid_type": "字段类型不正确，请按导入格式提供原始值。",
    "invalid_value": "字段值不符合消息格式要求。",
    "too_long": "字段内容超过支持的长度限制。",
    "unknown_fields": "标准消息包含不支持的字段，请按导入格式整理。",
    "invalid_record": "每条消息必须是符合格式的 JSON 对象。",
    "json_syntax": "JSON 内容无法解析，请检查引号、逗号和括号是否完整。",
    "unknown_envelope": "无法识别消息容器，请使用消息数组、单条消息或包含 messages/items 的导出对象。",
    "unsuccessful_export": "导出对象表示请求未成功，不能作为消息记录导入。",
    "empty": "文件中没有可预检的消息记录。",
    "ambiguous_fields": "多个原始字段给出了互相冲突的值，请核对导出的列或字段。",
    "unknown_format": "未识别出带真实时间和发送人/会话信息的聊天导出结构，请检查格式或导出选项。",
    "csv_syntax": "CSV/TSV 的引号或列结构不完整，请重新导出原始文件。",
    "invalid_html": "HTML 消息结构损坏或嵌套超过支持范围，请使用静态消息导出。",
}


def _validation_diagnostics(error: ValidationError) -> list[tuple[str, str]]:
    diagnostics = []
    for item in error.errors(include_url=False, include_context=False, include_input=False):
        location = item.get("loc", ())
        field = location[0] if location and location[0] in _FIELDS else "record"
        kind = item.get("type")
        if kind == "extra_forbidden":
            field, code = "record", "unknown_fields"
        elif field in {"id", "message_id"}:
            code = "missing_id" if kind == "missing" else "invalid_id"
        elif field in {"timestamp", "create_time"}:
            code = (
                "missing_timestamp"
                if kind == "missing"
                else "timezone_required" if kind == "value_error" else "invalid_timestamp"
            )
        elif field == "text":
            code = (
                "missing_content"
                if kind in {"missing", "string_too_short"}
                else "too_long" if kind == "string_too_long" else "invalid_content"
            )
        elif field == "sender":
            code = "invalid_sender"
        else:
            code = (
                "too_long"
                if kind == "string_too_long"
                else (
                    "invalid_type"
                    if kind in {"string_type", "dict_type", "list_type"}
                    else "invalid_value"
                )
            )
        diagnostics.append((field, code))
    return diagnostics


def _diagnose(
    record: Any, source_id: str, naive_timezone: str | None, context: dict[str, Any] | None = None
) -> list[tuple[str, str]]:
    if not isinstance(record, dict):
        return [("record", "invalid_record")]
    problems = []
    if record.get("source_id", source_id) != source_id:
        problems.append(("source_id", "source_mismatch"))
    kind = record_kind(record, context)
    if kind == "export":
        try:
            normalize_export_record(record, source_id, naive_timezone, context)
        except RecordProblems as error:
            return error.problems
        except ValidationError as error:
            return _validation_diagnostics(error)
        return []
    if kind == "standard":
        if isinstance(record.get("id"), str) and not record["id"].strip():
            problems.append(("id", "invalid_id"))
        try:
            StandardMessage.model_validate({**record, "source_id": source_id})
        except ValidationError as error:
            problems.extend(_validation_diagnostics(error))
        return list(dict.fromkeys(problems))
    identity = record.get("message_id")
    if "message_id" not in record:
        problems.append(("message_id", "missing_id"))
    elif not isinstance(identity, str) or not identity.strip() or len(identity) > 300:
        problems.append(("message_id", "invalid_id"))
    field = "create_time" if "create_time" in record else "timestamp"
    if field not in record:
        problems.append((field, "missing_timestamp"))
    else:
        try:
            _timestamp(record[field], naive_timezone)
        except (ValueError, TypeError, OverflowError, OSError, RecursionError):
            problems.append((field, "invalid_timestamp"))
    if "create_time" in record and "timestamp" in record:
        try:
            if _timestamp(record["create_time"], naive_timezone) != _timestamp(
                record["timestamp"], naive_timezone
            ):
                problems.append(("timestamp", "ambiguous_fields"))
        except (ValueError, TypeError, OverflowError, OSError, RecursionError):
            pass
    sender = record.get("sender", "unknown")
    if isinstance(sender, dict):
        sender = sender.get("name") or sender.get("sender_name") or sender.get("id") or "unknown"
    if not isinstance(sender, str):
        problems.append(("sender", "invalid_sender"))
    type_field = "msg_type" if "msg_type" in record else "message_type"
    if type_field in record and (
        not isinstance(record[type_field], str) or not record[type_field].strip()
    ):
        problems.append((type_field, "invalid_type"))
    try:
        _content_text(record)
    except (ValueError, TypeError, OverflowError, OSError, RecursionError):
        problems.append(
            (
                "content",
                (
                    "missing_content"
                    if not any(key in record for key in {"text", "content", "body"})
                    else "invalid_content"
                ),
            )
        )
    # Extra standardized fields are intentionally handled only by the existing
    # normalizer: a raw Feishu export retains its arbitrary fields in metadata.
    return list(dict.fromkeys(problems))


def preview_messages(
    content: str, source_id: str, format: str = "json", naive_timezone: str | None = "UTC+08:00"
) -> ImportPreview:
    """Return all candidates and safe issues; resource/config errors are fatal.

    JSONL position counts nonempty records, while line is its physical line.
    Whole-document failures have position=0,total=1; empty documents total=0.
    One invalid record may contribute multiple issues without increasing total.
    """
    if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 300:
        raise ImportValidationError("来源标识必须为1至300字符的非空文本。")
    if not isinstance(content, str):
        raise ImportValidationError("导入内容必须是文本。")
    try:
        size = len(content.encode("utf-8"))
        source_id.encode("utf-8")
    except UnicodeEncodeError:
        raise ImportValidationError("导入文本包含无效的 Unicode 字符。") from None
    if size > MAX_IMPORT_BYTES:
        raise ImportValidationError("导入文件超过10 MiB限制。")
    if format not in SUPPORTED_FORMATS:
        raise ImportValidationError("导入格式只能为 auto、json、jsonl、csv、txt 或 html。")
    if naive_timezone not in {None, "UTC", "UTC+08:00"}:
        raise ImportValidationError("不支持的导入时区，请选择 UTC 或 UTC+08:00。")
    clean = content.lstrip("\ufeff")
    result = ImportPreview(
        source_id=source_id,
        format_detected="json" if format == "auto" else format,
        total=0,
        valid=0,
    )

    def issue(position, line, field, code, raw):
        result.issues.append(
            ImportIssue(
                position=position,
                line=line,
                field=field,
                code=code,
                detail=_DIAGNOSTICS[code],
                raw=raw,
            )
        )

    document = read_export(clean, format)
    prepare_contexts(document)
    result.format_detected = document.format
    if document.error:
        result.total = 0 if document.error == "empty" else 1
        issue(0, None, "document", document.error, document.raw)
        return result
    if len(document.entries) > MAX_MESSAGES:
        raise ImportValidationError("导入记录超过10000条限制。")
    result.total = len(document.entries)
    if not document.entries:
        issue(0, None, "document", "empty", document.raw)
        return result
    if result.format_detected != format and format != "auto":
        result.warnings.append("已自动识别实际文件格式为 " + result.format_detected.upper() + "。")
    occurrences = Counter()
    derived_count = 0
    for entry in document.entries:
        position, line, record = entry.position, entry.line, entry.raw
        if entry.error:
            issue(position, line, "record", entry.error, record)
            continue
        try:
            problems = _diagnose(record, source_id, naive_timezone, entry.context)
        except (ValueError, TypeError, OverflowError, OSError, RecursionError):
            problems = [("record", "invalid_record")]
        if not problems:
            try:
                message = normalize_record(
                    record,
                    source_id,
                    naive_timezone,
                    context=entry.context,
                    occurrences=occurrences,
                )
                message.text.encode("utf-8")
            except UnicodeEncodeError:
                problems = [("text", "invalid_content")]
            except RecordProblems as error:
                problems = error.problems
            except ValidationError as error:
                problems = _validation_diagnostics(error)
            except (ValueError, TypeError, OverflowError, OSError, RecursionError):
                problems = [("record", "invalid_record")]
        for field, code in problems:
            issue(position, line, field, code, record)
        if not problems:
            result.messages.append(message)
            result.candidate_positions.append(position)
            result.candidate_lines.append(line)
            result.candidate_raw.append(record)
            imported = message.metadata.get("import")
            if isinstance(imported, dict) and imported.get("identity_kind") == "derived":
                derived_count += 1
    if derived_count:
        result.warnings.append(
            f"{derived_count}条记录没有原生消息ID，已按来源、会话、原始记录及重复出现次序生成确定性localimport标识；原始字段与派生依据已保留。"
        )
    result.issues.sort(key=lambda item: item.position)
    result.valid = len(result.messages)
    result.imported_candidates = result.valid
    return result
