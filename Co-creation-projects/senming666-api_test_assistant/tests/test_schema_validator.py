"""SchemaValidator 工具层的单元测试"""
from src.tools.schema_validator import SchemaValidator


def _validator():
    return SchemaValidator()


def _result(success=True, status_code=200, body=None, error=None):
    return {
        "success": success,
        "status_code": status_code,
        "body": body,
        "elapsed": 0.1,
        "error": error,
    }


# --- 状态码校验 ---

def test_status_code_match():
    ok, msg = _validator().validate_status_code(200, 200)
    assert ok is True and msg is None


def test_status_code_mismatch():
    ok, msg = _validator().validate_status_code(200, 400)
    assert ok is False and "400" in msg


# --- 响应体结构校验 ---

def test_body_no_schema_skips():
    ok, msg = _validator().validate_body({"a": 1}, None)
    assert ok is True


def test_body_matches_schema():
    schema = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
    ok, msg = _validator().validate_body({"id": 1}, schema)
    assert ok is True


def test_body_mismatches_schema():
    schema = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
    ok, msg = _validator().validate_body({"name": "x"}, schema)
    assert ok is False and "id" in msg


# --- 综合校验 ---

def test_validate_request_failed():
    check = _validator().validate(_result(success=False, error="请求超时"), expected_status=200)
    assert check["success"] is False
    assert any("请求超时" in e for e in check["errors"])


def test_validate_all_pass():
    check = _validator().validate(_result(status_code=200, body={"id": 1}), expected_status=200)
    assert check["success"] is True and check["errors"] == []


def test_validate_status_and_schema_both_fail():
    schema = {"type": "object", "required": ["id"]}
    check = _validator().validate(
        _result(status_code=500, body={}), expected_status=200, expected_schema=schema
    )
    assert check["success"] is False and len(check["errors"]) == 2
