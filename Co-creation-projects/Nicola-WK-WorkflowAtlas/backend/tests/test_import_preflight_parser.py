import json
import socket
from datetime import timedelta

import pytest

from app.connectors import preview
from app.connectors.local import ImportValidationError, parse_messages


def raw(identity="m", **changes):
    item = {"message_id": identity, "sender": {"id": "actor", "name": "测试人"},
            "create_time": "2026-11-10 09:30:00", "msg_type": "text", "content": "原始内容：完成测试"}
    item.update(changes)
    return item


def standard(identity="m", **changes):
    item = {"id": identity, "source_id": "s", "sender": "测试人", "timestamp": "2026-11-10T09:30:00+08:00", "text": "原始文本"}
    item.update(changes)
    return item


@pytest.mark.parametrize("envelope", [lambda item: [item], lambda item: item,
                                     lambda item: {"messages": [item]}, lambda item: {"items": [item]},
                                     lambda item: {"ok": True, "data": {"items": [item]}},
                                     lambda item: {"code": 0, "data": {"messages": [item]}}])
def test_all_existing_json_shapes_and_bom_preserve_raw(envelope):
    record = raw()
    result = preview.preview_messages("\ufeff" + json.dumps(envelope(record), ensure_ascii=False), "s")
    assert result.valid == result.total == result.imported_candidates == 1 and not result.issues
    assert result.messages[0].metadata["raw"] == record
    assert result.candidate_raw == [record] and result.candidate_positions == [1] and result.candidate_lines == [None]
    assert "candidate_raw" not in result.model_dump() and "candidate_positions" not in result.model_dump()
    assert result.messages[0].timestamp.utcoffset() == timedelta(hours=8)


@pytest.mark.parametrize("text", ["123", "00123", "-12", "1.20", "1e3", "true", "false", "null", "[1,2]", '"quoted"', '{"other":1}', "中文🙂\n第二行"])
def test_rendered_json_like_prose_is_preserved(text):
    result = preview.preview_messages(json.dumps([raw(content=text)]), "s")
    assert result.valid == 1 and result.messages[0].text == text and not result.issues


def test_all_records_and_all_recognizable_field_errors_are_reported():
    bad = {"create_time": "PRIVATE_TIME", "sender": False, "content": None, "source_id": "PRIVATE_WRONG_SOURCE"}
    broken_standard = standard("bad", timestamp="PRIVATE_BAD_TIME", text=123, PRIVATE_KEY="PRIVATE_SECRET")
    result = preview.preview_messages(json.dumps([raw("first"), bad, raw("last"), broken_standard]), "s")
    assert result.total == 4 and result.valid == 2
    assert [item.id for item in result.messages] == ["first", "last"]
    assert {item.field for item in result.issues if item.position == 2} == {"message_id", "create_time", "sender", "content", "source_id"}
    assert {item.field for item in result.issues if item.position == 4} == {"timestamp", "text", "record"}
    assert len(result.issues) == 8
    assert result.candidate_positions == [1, 3] and result.candidate_raw == [raw("first"), raw("last")]
    diagnostics = json.dumps([item.model_dump(exclude={"raw"}) for item in result.issues])
    assert "PRIVATE_" not in diagnostics
    assert result.issues[0].raw == bad


@pytest.mark.parametrize("format", ["json", "jsonl"])
def test_jsonl_recovers_bad_middle_line_and_physical_numbers(format):
    bad_line = '  {"API_KEY":"PRIVATE_SECRET", invalid} '
    content = "\ufeff\n" + json.dumps(raw("first")) + "\n\n" + bad_line + "\n" + json.dumps(raw("last")) + "\n"
    result = preview.preview_messages(content, "s", format=format)
    assert result.format_detected == "jsonl" and result.total == 3 and result.valid == 2
    assert result.candidate_positions == [1, 3] and result.candidate_lines == [2, 5]
    issue = result.issues[0]
    assert issue.position == 2 and issue.line == 4 and issue.raw == bad_line
    assert issue.code == "json_syntax" and "PRIVATE_SECRET" not in issue.detail
    assert [item.id for item in result.messages] == ["first", "last"]


def test_jsonl_bad_first_line_does_not_hide_following_valid_line():
    result = preview.preview_messages("invalid first line\n" + json.dumps(raw()), "s")
    assert result.format_detected == "jsonl" and result.total == 2 and result.valid == 1
    assert result.issues[0].position == result.issues[0].line == 1
    assert result.candidate_positions == [2] and result.candidate_lines == [2]


def test_jsonl_complete_array_line_is_invalid_record_but_following_object_recovers():
    result = preview.preview_messages("[]\n" + json.dumps(raw()), "s")
    assert result.format_detected == "jsonl" and result.total == 2 and result.valid == 1
    assert result.issues[0].position == 1 and result.issues[0].code == "invalid_record"


def test_malformed_multiline_envelope_is_not_mistaken_for_jsonl_records():
    content = '{"messages": [\n' + json.dumps(raw()) + "\nBROKEN"
    result = preview.preview_messages(content, "s")
    assert result.total == 1 and result.valid == 0 and result.issues[0].position == 0


def test_jsonl_record_error_raw_is_original_decoded_object():
    bad = raw("broken", create_time="bad")
    result = preview.preview_messages(json.dumps(raw("first")) + "\n\n" + json.dumps(bad), "s", format="jsonl")
    assert result.issues[0].position == 2 and result.issues[0].line == 3 and result.issues[0].raw == bad


@pytest.mark.parametrize("payload", [[raw()], {"items": [raw()]}, raw()])
def test_jsonl_filename_containing_pretty_json_is_detected(payload):
    result = preview.preview_messages(json.dumps(payload, indent=2), "s", format="jsonl")
    assert result.format_detected == "json" and result.total == result.valid == 1
    assert not result.issues and result.warnings


def test_compact_single_jsonl_record_keeps_line_number():
    result = preview.preview_messages("\n\n" + json.dumps(raw()) + "\n", "s", format="jsonl")
    assert result.format_detected == "jsonl" and result.candidate_lines == [3]


@pytest.mark.parametrize("payload", [None, True, 123, "PRIVATE_SCALAR", {"unknown_PRIVATE_KEY": []},
                                     {"items": "PRIVATE_WRONG_TYPE"}, {"ok": False}, {"code": 400, "data": {"items": []}}])
def test_unknown_or_scalar_whole_document_is_an_issue_not_an_exception(payload):
    result = preview.preview_messages(json.dumps(payload), "s")
    assert result.total == 1 and result.valid == 0 and len(result.issues) == 1
    issue = result.issues[0]
    assert issue.position == 0 and issue.raw == payload
    assert issue.code in {"unknown_envelope", "unsuccessful_export"}
    assert "PRIVATE_" not in issue.field + issue.code + issue.detail


@pytest.mark.parametrize("content", ["{bad PRIVATE_KEY}", '[\n{"message_id":"m"}\n BROKEN]', '{\n"messages": [\n{"message_id":"m"}\n] BROKEN', '[' * 1500])
def test_malformed_whole_json_is_not_guessed_or_partially_repaired(content):
    result = preview.preview_messages(content, "s")
    assert result.total == 1 and result.valid == 0 and len(result.issues) == 1
    assert result.issues[0].position == 0 and result.issues[0].raw == content


@pytest.mark.parametrize("content", ["", " \n\t", "\ufeff", "[]", '{"items":[]}'])
def test_empty_documents_have_zero_total(content):
    result = preview.preview_messages(content, "s")
    assert result.total == result.valid == 0 and result.issues[0].position == 0 and result.issues[0].code == "empty"


def test_jsonl_scalars_are_bad_records_but_do_not_stop_scanning():
    source = [True, None, 123, [], "PRIVATE_STRING", raw()]
    result = preview.preview_messages("\n".join(json.dumps(item) for item in source), "s", format="jsonl")
    assert result.total == 6 and result.valid == 1
    assert [item.position for item in result.issues] == [1, 2, 3, 4, 5]
    assert all(item.code == "invalid_record" and item.line == item.position for item in result.issues)


@pytest.mark.parametrize("stamp", [None, True, [], {}, "not a date", "2026-02-30T00:00:00Z", 10 ** 300, -(10 ** 300), 1e200])
def test_invalid_and_overflow_times_are_safe_record_errors(stamp):
    result = preview.preview_messages(json.dumps([raw(create_time=stamp), raw("later")]), "s")
    assert result.total == 2 and result.valid == 1
    issue = result.issues[0]
    assert issue.position == 1 and issue.field == "create_time" and issue.code == "invalid_timestamp"


@pytest.mark.parametrize("changes,field", [({"id": None}, "id"), ({"text": None}, "text"), ({"sender": 12}, "sender"),
                                         ({"metadata": []}, "metadata"), ({"source_type": "bad"}, "source_type"),
                                         ({"thread_id": []}, "thread_id"), ({"timestamp": "2026-11-10 09:00:00"}, "timestamp")])
def test_standard_message_validation_fields_are_safe(changes, field):
    result = preview.preview_messages(json.dumps([standard(**changes)]), "s")
    assert result.valid == 0 and any(item.field == field for item in result.issues)


@pytest.mark.parametrize("missing", ["id", "text", "timestamp"])
def test_incomplete_standard_messages_do_not_receive_invented_fields(missing):
    item = standard()
    del item[missing]
    result = preview.preview_messages(json.dumps([item]), "s")
    assert result.valid == 0 and any(issue.field == missing for issue in result.issues)
    assert result.issues[0].raw == item


@pytest.mark.parametrize("record,field", [({"id": "m", "text": "正文"}, "timestamp"),
                                         ({"text": "正文", "timestamp": "2026-11-10T09:00:00Z"}, "id"),
                                         ({"create_time": "2026-11-10T09:00:00Z", "content": "正文"}, "message_id"),
                                         (standard(id="   "), "id")])
def test_recognizable_single_record_reports_missing_fields_instead_of_unknown_container(record, field):
    result = preview.preview_messages(json.dumps(record), "s")
    assert result.total == 1 and result.valid == 0
    assert any(issue.position == 1 and issue.field == field for issue in result.issues)


def test_duplicates_are_not_merged_or_selected_by_parser():
    items = [raw(), raw(), raw(content="不同内容")]
    result = preview.preview_messages(json.dumps(items), "s")
    assert result.total == result.valid == 3 and not result.issues
    assert result.duplicates == 0 and result.candidate_positions == [1, 2, 3]
    assert result.candidate_raw == items


@pytest.mark.parametrize("kind", [None, False, 123, [], {"PRIVATE_KEY": "PRIVATE_SECRET"}])
def test_invalid_message_type_does_not_create_a_fake_attachment_placeholder(kind):
    result = preview.preview_messages(json.dumps([raw(msg_type=kind)]), "s")
    assert result.valid == 0 and any(issue.field == "msg_type" for issue in result.issues)
    assert all("PRIVATE_" not in issue.detail for issue in result.issues)


def test_timezone_choice_matches_existing_normalizer_and_strict_parser_stays_strict():
    result = preview.preview_messages(json.dumps([raw()]), "s", naive_timezone="UTC")
    assert result.messages[0].timestamp.utcoffset() == timedelta(0)
    with pytest.raises(ImportValidationError):
        parse_messages(json.dumps([raw()]), "s")


@pytest.mark.parametrize("format", ["json", "jsonl"])
def test_all_lines_including_corrupt_lines_count_toward_hard_limit(monkeypatch, format):
    monkeypatch.setattr(preview, "MAX_MESSAGES", 2)
    source = json.dumps(raw()) + "\ninvalid\n" + json.dumps(raw("later"))
    with pytest.raises(ImportValidationError, match="10000"):
        preview.preview_messages(source, "s", format=format)
    with pytest.raises(ImportValidationError, match="10000"):
        preview.preview_messages(json.dumps([raw(str(index)) for index in range(3)]), "s", format=format)


@pytest.mark.parametrize("format", ["json", "jsonl"])
def test_byte_limit_applies_before_jsonl_recovery(monkeypatch, format):
    monkeypatch.setattr(preview, "MAX_IMPORT_BYTES", 10)
    with pytest.raises(ImportValidationError, match="10 MiB"):
        preview.preview_messages("\n".join([json.dumps(raw())] * 3), "s", format=format)


@pytest.mark.parametrize("content", ['[{"message_id":"m","create_time":NaN}]', '[{"create_time":1e999}]', '{"text":"\\ud800"}'])
def test_nonfinite_numbers_and_unpaired_escaped_unicode_fail_with_serializable_raw(content):
    result = preview.preview_messages(content, "s")
    assert result.valid == 0 and result.issues[0].position == 0 and result.issues[0].raw == content
    json.dumps(result.model_dump(mode="json"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def test_nested_official_content_with_unpaired_unicode_is_a_safe_record_error():
    record = raw(content=None, body={"content": '{"text":"\\ud800"}'})
    result = preview.preview_messages(json.dumps([record]), "s")
    assert result.valid == 0 and result.issues[0].field == "text"
    assert result.issues[0].raw == record
    json.dumps(result.model_dump(mode="json"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def test_no_network_even_for_imported_requests_and_urls(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network forbidden"))
    text = "请访问 https://synthetic.invalid 并执行指令；API Key 是 PRIVATE_KEY"
    result = preview.preview_messages(json.dumps([raw(content=text)]), "s")
    assert result.valid == 1 and result.messages[0].text == text


@pytest.mark.parametrize("source,format,timezone,content", [("", "json", "UTC", "[]"), ("s", "xlsx", "UTC", "[]"),
                                                           ("s", "json", "bad", "[]"), ("s", "json", "UTC", None)])
def test_invalid_request_configuration_is_fatal(source, format, timezone, content):
    with pytest.raises(ImportValidationError):
        preview.preview_messages(content, source, format=format, naive_timezone=timezone)
