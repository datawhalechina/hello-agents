"""ValidatorAgent 包装验证结论的单元测试"""
from src.agents.validator_agent import ValidatorAgent


def _result(status_code):
    return {
        "success": True,
        "status_code": status_code,
        "body": None,
        "elapsed": 0.1,
        "error": None,
    }


def test_validate_one_pass():
    item = {"case": {"expected_status": 200}, "result": _result(200)}
    out = ValidatorAgent().validate_one(item)
    assert out["passed"] is True
    assert out["errors"] == []


def test_validate_one_fail():
    item = {"case": {"expected_status": 200}, "result": _result(404)}
    out = ValidatorAgent().validate_one(item)
    assert out["passed"] is False
    assert len(out["errors"]) == 1
    assert "404" in out["errors"][0]


def test_validate_one_missing_expected_status():
    # 用例没给 expected_status 时，应只做请求成功判断，不应崩溃
    item = {"case": {}, "result": _result(200)}
    out = ValidatorAgent().validate_one(item)
    assert out["passed"] is True


def test_validate_batch():
    items = [
        {"case": {"expected_status": 200}, "result": _result(200)},
        {"case": {"expected_status": 200}, "result": _result(500)},
    ]
    out = ValidatorAgent().validate(items)
    assert len(out) == 2
    assert out[0]["passed"] is True
    assert out[1]["passed"] is False
